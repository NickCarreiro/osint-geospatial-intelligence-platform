"""Radio Browser API adapter for fetching radio station data."""
import logging
from typing import List, Optional
from datetime import datetime

import httpx

from app.models import DataSource, EntityType, GeoJSONFeature
from app.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class RadioAdapter(BaseAdapter):
    """Adapter for Radio Browser API - global radio stations."""

    def __init__(self, api_url: str = "https://de1.api.radio-browser.info/json/stations/search"):
        super().__init__(DataSource.RADIO_API)
        self.api_url = api_url
        self.cache_key_prefix = "radio_stations"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def fetch_data(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch radio stations within bounding box."""
        try:
            # Build query parameters
            params = {
                "limit": 1000,  # Limit to 1000 stations for performance
                "hidebroken": True,
                "order": "clickcount",
                "reverse": True,
                "geoip": False,
            }

            # Add bounding box filter if provided
            if lamin is not None and lomin is not None and lamax is not None and lomax is not None:
                params["lat"] = (lamin + lamax) / 2
                params["lon"] = (lomin + lomax) / 2
                params["distance"] = "5000"  # Search within 5000km radius

            logger.info(f"Fetching radio stations from {self.api_url}")
            response = await self.client.get(self.api_url, params=params)
            response.raise_for_status()

            stations = response.json()

            # Convert to GeoJSON features
            features = []
            for station in stations:
                # Extract coordinates (use last known location if available)
                lat = station.get("lastcheckok", {}).get("lat")
                lon = station.get("lastcheckok", {}).get("lon")

                if lat is None or lon is None:
                    continue

                # Extract tags as list
                tags = station.get("tags", [])
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]

                metadata = {
                    "name": station.get("name", "Unknown Station"),
                    "frequency": station.get("frequency"),
                    "country": station.get("countrycode"),
                    "country_name": station.get("country"),
                    "state": station.get("state"),
                    "city": station.get("city"),
                    "tags": tags,
                    "codec": station.get("codec"),
                    "bitrate": station.get("bitrate"),
                    "clickcount": station.get("clickcount"),
                    "clicktimestamp": station.get("clicktimestamp"),
                    "lastcheckok": station.get("lastcheckok"),
                    "lastcheckok_timestamp": station.get("lastcheckok_timestamp"),
                    "homepage": station.get("homepage"),
                    "favicon": station.get("favicon"),
                    "url_resolved": station.get("url_resolved"),
                }

                feature = GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=self.source,
                    entity_type=EntityType.RADIO_STATION,
                    identifier=station.get("stationuuid", ""),
                    timestamp=datetime.utcnow(),
                    metadata=metadata,
                )
                features.append(feature)

            logger.info(f"Fetched {len(features)} radio stations")
            return features

        except Exception as e:
            logger.error(f"Error fetching radio stations: {e}")
            return []

    async def fetch_by_country(self, country_code: str) -> List[GeoJSONFeature]:
        """Fetch radio stations for a specific country."""
        try:
            params = {
                "limit": 500,
                "countrycode": country_code.upper(),
                "hidebroken": True,
            }

            client = await self._get_client()
            response = await client.get(self.api_url, params=params)
            response.raise_for_status()

            stations = response.json()
            features = []

            for station in stations:
                lat = station.get("lastcheckok", {}).get("lat")
                lon = station.get("lastcheckok", {}).get("lon")

                if lat is None or lon is None:
                    continue

                tags = station.get("tags", [])
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]

                metadata = {
                    "name": station.get("name", "Unknown Station"),
                    "frequency": station.get("frequency"),
                    "country": station.get("countrycode"),
                    "country_name": station.get("country"),
                    "state": station.get("state"),
                    "city": station.get("city"),
                    "tags": tags,
                    "codec": station.get("codec"),
                    "bitrate": station.get("bitrate"),
                    "homepage": station.get("homepage"),
                    "favicon": station.get("favicon"),
                    "url_resolved": station.get("url_resolved"),
                }

                feature = GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=self.source,
                    entity_type=EntityType.RADIO_STATION,
                    identifier=station.get("stationuuid", ""),
                    timestamp=datetime.utcnow(),
                    metadata=metadata,
                )
                features.append(feature)

            return features

        except Exception as e:
            logger.error(f"Error fetching radio stations for country {country_code}: {e}")
            return []

    async def fetch_by_language(self, language: str) -> List[GeoJSONFeature]:
        """Fetch radio stations by language."""
        try:
            params = {
                "limit": 500,
                "language": language,
                "hidebroken": True,
            }

            client = await self._get_client()
            response = await client.get(self.api_url, params=params)
            response.raise_for_status()

            stations = response.json()
            features = []

            for station in stations:
                lat = station.get("lastcheckok", {}).get("lat")
                lon = station.get("lastcheckok", {}).get("lon")

                if lat is None or lon is None:
                    continue

                tags = station.get("tags", [])
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]

                metadata = {
                    "name": station.get("name", "Unknown Station"),
                    "frequency": station.get("frequency"),
                    "country": station.get("countrycode"),
                    "country_name": station.get("country"),
                    "state": station.get("state"),
                    "city": station.get("city"),
                    "tags": tags,
                    "codec": station.get("codec"),
                    "bitrate": station.get("bitrate"),
                    "homepage": station.get("homepage"),
                    "favicon": station.get("favicon"),
                    "url_resolved": station.get("url_resolved"),
                }

                feature = GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=self.source,
                    entity_type=EntityType.RADIO_STATION,
                    identifier=station.get("stationuuid", ""),
                    timestamp=datetime.utcnow(),
                    metadata=metadata,
                )
                features.append(feature)

            return features

        except Exception as e:
            logger.error(f"Error fetching radio stations by language {language}: {e}")
            return []

    async def fetch(self, **kwargs) -> List[GeoJSONFeature]:
        """Fetch radio stations - default implementation calls fetch_data."""
        return await self.fetch_data(**kwargs)

    async def close(self):
        """Close the HTTP client."""
        if hasattr(self, '_client') and self._client and not self._client.is_closed:
            await self._client.aclose()
