"""CelesTrak TLE adapter for satellite tracking with orbital propagation."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import re

import httpx
from skyfield.api import load, EarthSatellite, wgs84

from app.adapters.base import BaseAdapter, AdapterError
from app.models import GeoJSONFeature, DataSource, EntityType, BoundingBox
from app.config import settings

logger = logging.getLogger(__name__)


class CelesTrakAdapter(BaseAdapter):
    """Adapter for CelesTrak TLE data with orbital propagation."""

    def __init__(self):
        """Initialize the CelesTrak adapter."""
        super().__init__(DataSource.CELESTRAK)
        self._client: Optional[httpx.AsyncClient] = None
        self._satellites: Dict[str, EarthSatellite] = {}
        self._satellite_metadata: Dict[str, Dict[str, Any]] = {}
        self._last_catalog_refresh: Optional[datetime] = None
        self._timescale = load.timescale()
        self._spacetrack_session: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            # Use configured timeout with separate connect and read timeouts
            # TLE catalogs can be large, so we need a longer read timeout
            timeout = httpx.Timeout(
                connect=10.0,  # Connection timeout
                read=60.0,     # Read timeout for large TLE downloads
                write=10.0,    # Write timeout
                pool=10.0      # Pool timeout
            )
            self._client = httpx.AsyncClient(timeout=timeout)
        return self._client

    async def _spacetrack_login(self) -> bool:
        """Login to Space-Track and get session cookie."""
        if not settings.spacetrack_username or not settings.spacetrack_password:
            logger.debug("Space-Track: No credentials configured")
            return False

        client = await self._get_client()

        try:
            logger.info("Space-Track: Logging in")
            # Space-Track uses form data with identity and password
            response = await client.post(
                settings.spacetrack_login_url,
                data={
                    "identity": settings.spacetrack_username,
                    "password": settings.spacetrack_password,
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin": settings.spacetrack_base_url,
                    "Referer": settings.spacetrack_base_url,
                },
            )
            response.raise_for_status()

            # Extract session cookie from response
            # Space-Track uses "chocolatechip" as the session cookie name
            cookies = response.cookies
            logger.debug(f"Space-Track: Response cookies: {list(cookies.keys())}")
            
            # Try to find the session cookie (Space-Track uses "chocolatechip")
            session_cookie = None
            for cookie_name in ["chocolatechip", "spacetrack", "sessionid", "session", "auth"]:
                if cookie_name in cookies:
                    session_cookie = cookies[cookie_name]
                    logger.info(f"Space-Track: Found session cookie '{cookie_name}'")
                    break
            
            if session_cookie:
                self._spacetrack_session = session_cookie
                logger.info("Space-Track: Login successful")
                return True
            else:
                logger.warning(f"Space-Track: No session cookie in response. Available cookies: {list(cookies.keys())}")
                return False

        except Exception as e:
            logger.warning(f"Space-Track: Login failed: {e}")
            return False

    async def _refresh_catalog_from_spacetrack(self) -> bool:
        """Refresh TLE catalog from Space-Track."""
        if not self._spacetrack_session:
            if not await self._spacetrack_login():
                return False

        client = await self._get_client()

        # Try both TLE URLs
        tle_urls = [settings.spacetrack_tle_url, settings.spacetrack_tle_url_alt]
        
        for tle_url in tle_urls:
            try:
                logger.info(f"Space-Track: Fetching TLE catalog from {tle_url}")
                # Use the session cookie with the correct name
                response = await client.get(
                    tle_url,
                    cookies={"chocolatechip": self._spacetrack_session},
                )
                response.raise_for_status()

                tle_text = response.text
                self._parse_tle_catalog(tle_text)

                self._last_catalog_refresh = datetime.utcnow()
                logger.info(f"Space-Track: Loaded {len(self._satellites)} satellites")
                return True

            except httpx.HTTPStatusError as e:
                logger.warning(f"Space-Track: API error for {tle_url}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Space-Track: Catalog refresh error for {tle_url}: {e}")
                continue

        logger.warning("Space-Track: All TLE URLs failed")
        return False

    async def _refresh_catalog_from_celestrak(self) -> bool:
        """Refresh TLE catalog from CelesTrak."""
        client = await self._get_client()

        try:
            logger.info("CelesTrak: Fetching TLE catalog")
            response = await client.get(settings.satellite_tle_url)
            response.raise_for_status()

            tle_text = response.text
            self._parse_tle_catalog(tle_text)

            self._last_catalog_refresh = datetime.utcnow()
            logger.info(f"CelesTrak: Loaded {len(self._satellites)} satellites")
            return True

        except httpx.HTTPStatusError as e:
            logger.warning(f"CelesTrak: API error: {e}")
            return False
        except Exception as e:
            logger.warning(f"CelesTrak: Catalog refresh error: {e}")
            return False

    async def _refresh_catalog(self):
        """Refresh the TLE catalog from available sources."""
        now = datetime.utcnow()

        # Check if we need to refresh
        if self._last_catalog_refresh:
            age = (now - self._last_catalog_refresh).total_seconds()
            if age < settings.satellite_catalog_refresh_s:
                logger.debug(f"Satellite: Catalog fresh ({age:.0f}s old)")
                return

        # Try Space-Track first if credentials are available
        if settings.spacetrack_username and settings.spacetrack_password:
            if await self._refresh_catalog_from_spacetrack():
                return
            logger.info("Space-Track failed, trying CelesTrak...")

        # Fall back to CelesTrak
        if await self._refresh_catalog_from_celestrak():
            return

        # If both failed, raise an error
        raise AdapterError("Failed to refresh TLE catalog from both Space-Track and CelesTrak")

    def _parse_tle_catalog(self, tle_text: str):
        """Parse TLE catalog into satellite objects."""
        lines = tle_text.strip().split("\n")
        satellites = {}
        metadata = {}

        i = 0
        while i < len(lines):
            line1 = lines[i].strip()

            # Skip empty lines and comments
            if not line1 or line1.startswith("#"):
                i += 1
                continue

            # Check if this is a TLE line 1
            if line1.startswith("1 "):
                # Get line 2
                if i + 1 < len(lines):
                    line2 = lines[i + 1].strip()
                    if line2.startswith("2 "):
                        # Get name from previous line if available
                        name = ""
                        if i > 0:
                            prev_line = lines[i - 1].strip()
                            if not prev_line.startswith("1 ") and not prev_line.startswith("2 "):
                                name = prev_line

                        # Parse satellite ID from line 1
                        # Format: 1 <NORAD_ID> ...
                        match = re.match(r"1\s+(\d+)", line1)
                        if match:
                            norad_id = match.group(1)

                            # Create EarthSatellite object
                            try:
                                sat = EarthSatellite(line1, line2, name, self._timescale)
                                satellites[norad_id] = sat

                                # Store metadata
                                metadata[norad_id] = {
                                    "name": name,
                                    "norad_id": norad_id,
                                }

                            except Exception as e:
                                logger.warning(f"CelesTrak: Failed to parse TLE for {norad_id}: {e}")

                        i += 2
                        continue

            i += 1

        self._satellites = satellites
        self._satellite_metadata = metadata

    def _get_satellite_position(
        self,
        satellite: EarthSatellite,
        time: datetime,
    ) -> Optional[tuple[float, float, float]]:
        """Get satellite position at a given time."""
        try:
            # Convert datetime to skyfield time
            t = self._timescale.utc(
                time.year,
                time.month,
                time.day,
                time.hour,
                time.minute,
                time.second,
            )

            # Get geocentric position
            geocentric = satellite.at(t)

            # Get subpoint on Earth's surface
            subpoint = wgs84.subpoint(geocentric)

            lat = subpoint.latitude.degrees
            lon = subpoint.longitude.degrees
            altitude = subpoint.elevation.m / 1000.0  # Convert to km

            return lon, lat, altitude

        except Exception as e:
            logger.warning(f"CelesTrak: Failed to get position: {e}")
            return None

    async def fetch(
        self,
        bbox: Optional[BoundingBox] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch satellite data with orbital propagation."""
        try:
            # Refresh catalog if needed
            await self._refresh_catalog()

            # Get current time
            now = datetime.utcnow()

            features = []
            max_satellites = settings.satellite_max_entities

            # Process satellites
            for norad_id, satellite in list(self._satellites.items()):
                if len(features) >= max_satellites:
                    logger.warning(
                        f"CelesTrak: Reached max satellites ({max_satellites})"
                    )
                    break

                # Get position
                position = self._get_satellite_position(satellite, now)
                if position is None:
                    continue

                lon, lat, altitude = position

                # Apply bbox filter if provided
                if bbox and not bbox.contains(lon, lat):
                    continue

                # Get metadata
                meta = self._satellite_metadata.get(norad_id, {})
                name = meta.get("name", f"Satellite {norad_id}")

                # Calculate orbital elements for metadata
                try:
                    t = self._timescale.utc(
                        now.year,
                        now.month,
                        now.day,
                        now.hour,
                        now.minute,
                        now.second,
                    )
                    geocentric = satellite.at(t)

                    # Get orbital parameters
                    position_km = geocentric.position.km
                    velocity_kms = geocentric.velocity.km_per_s

                    # Calculate inclination (simplified)
                    # In practice, you'd extract this from the TLE
                    inclination = 0.0

                except Exception as e:
                    logger.warning(f"CelesTrak: Failed to get orbital params: {e}")
                    position_km = [0, 0, 0]
                    velocity_kms = [0, 0, 0]
                    inclination = 0.0

                # Create metadata
                metadata = {
                    "norad_id": norad_id,
                    "name": name,
                    "altitude": altitude,
                    "inclination": inclination,
                }

                feature = GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=DataSource.CELESTRAK,
                    entity_type=EntityType.SATELLITE,
                    identifier=norad_id,
                    timestamp=now,
                    metadata=metadata,
                )

                features.append(feature)

            logger.info(f"CelesTrak: Fetched {len(features)} satellites")
            return features

        except Exception as e:
            raise AdapterError(f"CelesTrak fetch error: {e}")

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()