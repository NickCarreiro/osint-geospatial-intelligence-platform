"""Radio Browser API adapter for fetching radio station data."""
import logging
from datetime import datetime
from typing import List, Optional

import httpx

from app.adapters.base import AdapterError, BaseAdapter
from app.models import DataSource, EntityType, GeoJSONFeature

logger = logging.getLogger(__name__)


class RadioAdapter(BaseAdapter):
    """Adapter for the Radio Browser API."""

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

    def _get_station_coordinates(self, station: dict) -> tuple[Optional[float], Optional[float]]:
        """Extract station coordinates from Radio Browser payloads."""
        lat = station.get("geo_lat")
        lon = station.get("geo_long")
        if lat is None or lon is None:
            return None, None

        try:
            return float(lat), float(lon)
        except (TypeError, ValueError):
            return None, None

    def _build_feature(self, station: dict, lat: float, lon: float) -> GeoJSONFeature:
        """Convert a Radio Browser station into a GeoJSON feature."""
        tags = station.get("tags", [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

        metadata = {
            "name": station.get("name", "Unknown Station"),
            "country": station.get("countrycode"),
            "country_name": station.get("country"),
            "state": station.get("state"),
            "language": station.get("language"),
            "codec": station.get("codec"),
            "bitrate": station.get("bitrate"),
            "clickcount": station.get("clickcount"),
            "votes": station.get("votes"),
            "tags": tags,
            "homepage": station.get("homepage"),
            "favicon": station.get("favicon"),
            "url_resolved": station.get("url_resolved"),
            "lastcheckok": station.get("lastcheckok"),
        }

        return GeoJSONFeature.create_point(
            lon=lon,
            lat=lat,
            source=self.source,
            entity_type=EntityType.RADIO_STATION,
            identifier=station.get("stationuuid", ""),
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )

    async def fetch_data(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch radio stations, optionally centered around a bbox."""
        try:
            params = {
                "limit": 1000,
                "hidebroken": True,
                "order": "clickcount",
                "reverse": True,
                "geoip": False,
            }

            if None not in (lamin, lomin, lamax, lomax):
                params["lat"] = (lamin + lamax) / 2
                params["lon"] = (lomin + lomax) / 2
                params["distance"] = "5000"

            logger.info(f"Fetching radio stations from {self.api_url}")
            client = await self._get_client()
            response = await client.get(self.api_url, params=params)
            response.raise_for_status()

            stations = response.json()
            features = []
            for station in stations:
                lat, lon = self._get_station_coordinates(station)
                if lat is None or lon is None:
                    continue
                features.append(self._build_feature(station, lat, lon))

            logger.info(f"Fetched {len(features)} radio stations")
            return features
        except Exception as e:
            logger.error(f"Error fetching radio stations: {e}")
            raise AdapterError(f"Radio Browser fetch failed: {e}") from e

    async def fetch_by_country(self, country_code: str) -> List[GeoJSONFeature]:
        """Fetch radio stations for a specific country."""
        try:
            client = await self._get_client()
            response = await client.get(
                self.api_url,
                params={
                    "limit": 500,
                    "countrycode": country_code.upper(),
                    "hidebroken": True,
                },
            )
            response.raise_for_status()

            features = []
            for station in response.json():
                lat, lon = self._get_station_coordinates(station)
                if lat is None or lon is None:
                    continue
                features.append(self._build_feature(station, lat, lon))
            return features
        except Exception as e:
            logger.error(f"Error fetching radio stations for country {country_code}: {e}")
            raise AdapterError(f"Radio Browser country fetch failed: {e}") from e

    async def fetch_by_language(self, language: str) -> List[GeoJSONFeature]:
        """Fetch radio stations by language."""
        try:
            client = await self._get_client()
            response = await client.get(
                self.api_url,
                params={
                    "limit": 500,
                    "language": language,
                    "hidebroken": True,
                },
            )
            response.raise_for_status()

            features = []
            for station in response.json():
                lat, lon = self._get_station_coordinates(station)
                if lat is None or lon is None:
                    continue
                features.append(self._build_feature(station, lat, lon))
            return features
        except Exception as e:
            logger.error(f"Error fetching radio stations by language {language}: {e}")
            raise AdapterError(f"Radio Browser language fetch failed: {e}") from e

    async def fetch(self, country_code: Optional[str] = None, language: Optional[str] = None, **kwargs) -> List[GeoJSONFeature]:
        """Fetch radio stations - default implementation calls fetch_data."""
        if country_code:
            return await self.fetch_by_country(country_code)
        if language:
            return await self.fetch_by_language(language)
        return await self.fetch_data(**kwargs)

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
