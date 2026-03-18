"""OpenSky Network adapter for aircraft data."""
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx

from app.adapters.base import BaseAdapter, AdapterError, RateLimitError
from app.models import GeoJSONFeature, DataSource, EntityType, BoundingBox
from app.config import settings

logger = logging.getLogger(__name__)


class OpenSkyAdapter(BaseAdapter):
    """Adapter for OpenSky Network API with OAuth authentication."""

    def __init__(self):
        """Initialize the OpenSky adapter."""
        super().__init__(DataSource.OPENSKY)
        self._client: Optional[httpx.AsyncClient] = None
        self._token_cache: Optional[str] = None
        self._token_cache_exp_ts: int = 0
        self._cache_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def _bearer_token(self) -> Optional[str]:
        """Get OAuth bearer token from OpenSky."""
        if not settings.opensky_client_id or not settings.opensky_client_secret:
            return None

        now = int(time.time())
        
        # Check if we have a cached token that's still valid
        async with self._cache_lock:
            if self._token_cache and now < self._token_cache_exp_ts:
                return self._token_cache

        # Request new token
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.opensky_client_id,
            "client_secret": settings.opensky_client_secret,
        }

        client = await self._get_client()
        try:
            response = await client.post(
                settings.opensky_token_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code >= 400:
                logger.error(f"OpenSky token request failed (HTTP {response.status_code}): {response.text}")
                return None

            payload = response.json()
            token = payload.get("access_token")
            expires_in = int(payload.get("expires_in") or 1800)
            
            if token:
                # Cache the token and refresh before actual expiry
                async with self._cache_lock:
                    self._token_cache = token
                    self._token_cache_exp_ts = int(time.time()) + max(60, expires_in - 60)
                logger.info(f"OpenSky: Obtained OAuth token, expires in {expires_in}s")
                return token
            else:
                logger.error("OpenSky token response did not include access_token")
                return None

        except Exception as e:
            logger.error(f"OpenSky token request error: {e}")
            return None

    async def fetch(
        self,
        bbox: Optional[BoundingBox] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch aircraft data from OpenSky."""
        # Get OAuth bearer token
        token = await self._bearer_token()
        
        # If no token, try without authentication (public API)
        headers: Dict[str, str] = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            logger.warning("OpenSky: No OAuth token available, using public API")

        client = await self._get_client()

        # Use provided bbox or default
        lamin = bbox.lamin if bbox else settings.opensky_lamin
        lomin = bbox.lomin if bbox else settings.opensky_lomin
        lamax = bbox.lamax if bbox else settings.opensky_lamax
        lomax = bbox.lomax if bbox else settings.opensky_lomax

        try:
            response = await client.get(
                settings.opensky_states_url,
                params={
                    "lamin": lamin,
                    "lomin": lomin,
                    "lamax": lamax,
                    "lomax": lomax,
                    "extended": "true",
                },
                headers=headers,
            )

            if response.status_code == 429:
                raise RateLimitError("OpenSky API rate limit exceeded")

            response.raise_for_status()
            data = response.json()

            return self._parse_states(data)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("OpenSky API rate limit exceeded")
            if e.response.status_code == 401:
                # Token might be expired, clear cache
                async with self._cache_lock:
                    self._token_cache = None
                    self._token_cache_exp_ts = 0
                logger.warning("OpenSky: Token expired, will refresh on next request")
                raise AdapterError(f"OpenSky authentication failed: {e}")
            raise AdapterError(f"OpenSky API error: {e}")
        except Exception as e:
            raise AdapterError(f"OpenSky fetch error: {e}")

    def _parse_states(self, data: Dict[str, Any]) -> List[GeoJSONFeature]:
        """Parse OpenSky state vectors into GeoJSON features."""
        features = []
        states = data.get("states", [])

        if not states:
            return features

        # OpenSky states format:
        # [icao24, callsign, origin_country, time_position, last_contact,
        #  longitude, latitude, baro_altitude, on_ground, velocity,
        #  true_track, vertical_rate, sensors, geo_altitude, squawk,
        #  spi, position_source, category]
        for state in states:
            try:
                icao24 = state[0]
                callsign = state[1] or ""
                origin_country = state[2] or ""
                lon = state[5]
                lat = state[6]
                altitude = state[7]
                on_ground = state[8]
                velocity = state[9]
                heading = state[10]
                vertical_rate = state[11]
                geo_altitude = state[13] if len(state) > 13 else None
                squawk = state[14] if len(state) > 14 else None
                spi = state[15] if len(state) > 15 else None
                position_source = state[16] if len(state) > 16 else None
                category = state[17] if len(state) > 17 else None

                # Skip if no position
                if lon is None or lat is None:
                    continue

                # Calculate timestamp
                time_position = state[3]
                if time_position:
                    timestamp = datetime.fromtimestamp(time_position, tz=None)
                else:
                    timestamp = datetime.utcnow()

                # Create metadata
                metadata = {
                    "icao24": icao24,
                    "callsign": callsign,
                    "origin_country": origin_country,
                    "altitude": altitude,
                    "on_ground": on_ground,
                    "velocity": velocity,
                    "heading": heading,
                    "vertical_rate": vertical_rate,
                    "geo_altitude": geo_altitude,
                    "squawk": squawk,
                    "spi": spi,
                    "position_source": position_source,
                    "category": category,
                }

                feature = GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=DataSource.OPENSKY,
                    entity_type=EntityType.AIRCRAFT,
                    identifier=icao24,
                    timestamp=timestamp,
                    metadata=metadata,
                )

                features.append(feature)

            except Exception as e:
                logger.warning(f"OpenSky: Failed to parse state: {e}")
                continue

        logger.info(f"OpenSky: Parsed {len(features)} aircraft")
        return features

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()