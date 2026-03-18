"""FIRMS (NASA Fire Information for Resource Management System) adapter for thermal/fire data."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx

from app.adapters.base import BaseAdapter, AdapterError, RateLimitError
from app.models import GeoJSONFeature, DataSource, EntityType, BoundingBox
from app.config import settings

logger = logging.getLogger(__name__)


class FIRMSAdapter(BaseAdapter):
    """Adapter for NASA FIRMS API."""

    BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area"

    def __init__(self):
        """Initialize the FIRMS adapter."""
        super().__init__(DataSource.FIRMS)
        self._client: Optional[httpx.AsyncClient] = None
        self._rate_limit_tracker: Dict[str, List[float]] = {}

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _check_rate_limit(self):
        """Check if we're within rate limits."""
        now = asyncio.get_event_loop().time()
        window = settings.firms_rate_window
        limit = settings.firms_rate_limit

        # Clean old requests
        self._rate_limit_tracker = {
            k: [t for t in v if now - t < window]
            for k, v in self._rate_limit_tracker.items()
        }

        # Check current request count
        total_requests = sum(len(v) for v in self._rate_limit_tracker.values())
        if total_requests >= limit:
            raise RateLimitError(
                f"FIRMS rate limit exceeded: {total_requests}/{limit} requests"
            )

    def _track_request(self, endpoint: str):
        """Track a request for rate limiting."""
        now = asyncio.get_event_loop().time()
        if endpoint not in self._rate_limit_tracker:
            self._rate_limit_tracker[endpoint] = []
        self._rate_limit_tracker[endpoint].append(now)

    async def fetch(
        self,
        bbox: Optional[BoundingBox] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch thermal/fire data from FIRMS."""
        if not settings.firms_api_key:
            logger.warning("FIRMS: No API key configured")
            return []

        client = await self._get_client()

        # Use provided bbox or default to global
        lamin = bbox.lamin if bbox else -90.0
        lomin = bbox.lomin if bbox else -180.0
        lamax = bbox.lamax if bbox else 90.0
        lomax = bbox.lomax if bbox else 180.0

        # FIRMS uses different bbox format: west,south,east,north
        bbox_str = f"{lomin},{lamin},{lomax},{lamax}"

        # Get data from the last 24 hours
        # FIRMS API uses day_range as a number of days (1-5)
        days_to_fetch = 1  # Last 24 hours

        # FIRMS data source
        source = "MODIS_NRT"  # MODIS Near Real-Time data source

        try:
            # Check rate limit
            self._check_rate_limit()

            # FIRMS API uses path-based URL format:
            # /api/area/csv/{MAP_KEY}/{SOURCE}/{AREA}/{DAY_RANGE}
            # where AREA can be "world" or coordinates in "west,south,east,north" format
            url = f"{self.BASE_URL}/csv/{settings.firms_api_key}/{source}/{bbox_str}/{days_to_fetch}"

            response = await client.get(url)

            # Track request
            self._track_request("area")

            if response.status_code == 429:
                raise RateLimitError("FIRMS API rate limit exceeded")

            response.raise_for_status()

            # Log the response for debugging
            logger.info(f"FIRMS: Response status {response.status_code}, content length {len(response.text)}")
            if response.text:
                logger.info(f"FIRMS: Full response: {repr(response.text[:200])}")
            
            # FIRMS returns CSV, need to parse
            return self._parse_csv(response.text)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("FIRMS API rate limit exceeded")
            raise AdapterError(f"FIRMS API error: {e}")
        except Exception as e:
            raise AdapterError(f"FIRMS fetch error: {e}")

    def _parse_csv(self, csv_text: str) -> List[GeoJSONFeature]:
        """Parse FIRMS CSV response into GeoJSON features."""
        features = []
        lines = csv_text.strip().split("\n")

        if len(lines) < 2:
            return features

        # Check for error responses
        first_line = lines[0].strip().lower()
        if "invalid" in first_line or "error" in first_line:
            logger.warning(f"FIRMS: API returned error: {lines[0]}")
            return features

        # Parse header
        headers = [h.strip() for h in lines[0].split(",")]

        # Parse data rows
        for line in lines[1:]:
            try:
                values = [v.strip() for v in line.split(",")]
                row = dict(zip(headers, values))

                # Extract required fields
                lat_str = row.get("latitude", "")
                lon_str = row.get("longitude", "")
                
                # Skip if coordinates are missing or invalid
                if not lat_str or not lon_str:
                    continue
                
                lat = float(lat_str)
                lon = float(lon_str)
                
                # Skip invalid coordinates (0,0 is likely a default/error value)
                if lat == 0.0 and lon == 0.0:
                    continue
                
                acq_date = row.get("acq_date", "")
                acq_time = row.get("acq_time", "")
                confidence = row.get("confidence", "")
                frp = row.get("frp", "")
                satellite = row.get("satellite", "")
                instrument = row.get("instrument", "")

                # Parse timestamp
                try:
                    timestamp = datetime.strptime(
                        f"{acq_date} {acq_time}",
                        "%Y-%m-%d %H:%M:%S"
                    )
                except:
                    timestamp = datetime.utcnow()

                # Create metadata
                metadata = {
                    "confidence": confidence,
                    "fire_radiative_power": frp,
                    "satellite": satellite,
                    "instrument": instrument,
                    "brightness": row.get("brightness", ""),
                    "bright_t31": row.get("bright_t31", ""),
                    "daynight": row.get("daynight", ""),
                }

                feature = GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=DataSource.FIRMS,
                    entity_type=EntityType.THERMAL_EVENT,
                    identifier=f"{satellite}_{lat}_{lon}_{timestamp.strftime('%Y%m%d%H%M%S')}",
                    timestamp=timestamp,
                    metadata=metadata,
                )

                features.append(feature)

            except Exception as e:
                logger.warning(f"FIRMS: Failed to parse row: {e}")
                continue

        logger.info(f"FIRMS: Fetched {len(features)} thermal events")
        return features

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()