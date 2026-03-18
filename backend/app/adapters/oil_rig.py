"""Oil rig locations adapter for fetching offshore drilling platform data."""
import logging
from typing import List, Optional
from datetime import datetime

import httpx

from app.models import DataSource, EntityType, GeoJSONFeature
from app.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class OilRigAdapter(BaseAdapter):
    """Adapter for offshore oil rig locations."""

    def __init__(self, api_url: str = "https://api.oilrigs.org/v1"):
        super().__init__(DataSource.OIL_RIG_API)
        self.api_url = api_url
        self.cache_key_prefix = "oil_rigs"
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
        """Fetch oil rigs within bounding box."""
        try:
            # Build query parameters
            params = {
                "limit": 500,
                "status": "active",  # Only active rigs
            }

            # Add bounding box filter if provided
            if lamin is not None and lomin is not None and lamax is not None and lomax is not None:
                params["min_lat"] = lamin
                params["min_lon"] = lomin
                params["max_lat"] = lamax
                params["max_lon"] = lomax

            logger.info(f"Fetching oil rigs from {self.api_url}")
            response = await self.client.get(self.api_url, params=params)
            response.raise_for_status()

            rigs = response.json()

            # Convert to GeoJSON features
            features = []
            for rig in rigs:
                # Extract coordinates
                lat = rig.get("latitude")
                lon = rig.get("longitude")

                if lat is None or lon is None:
                    continue

                metadata = {
                    "name": rig.get("name", "Unknown Rig"),
                    "operator": rig.get("operator"),
                    "operator_code": rig.get("operator_code"),
                    "country": rig.get("country"),
                    "country_code": rig.get("country_code"),
                    "region": rig.get("region"),
                    "status": rig.get("status"),
                    "production": rig.get("production"),
                    "water_depth": rig.get("water_depth"),
                    "type": rig.get("type"),
                    "commissioned": rig.get("commissioned"),
                    "latitude": lat,
                    "longitude": lon,
                    "id": rig.get("id"),
                }

                feature = GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=self.source,
                    entity_type=EntityType.OIL_RIG,
                    identifier=rig.get("id", ""),
                    timestamp=datetime.utcnow(),
                    metadata=metadata,
                )
                features.append(feature)

            logger.info(f"Fetched {len(features)} oil rigs")
            return features

        except Exception as e:
            logger.error(f"Error fetching oil rigs: {e}")
            return []

    async def fetch_by_region(self, region: str) -> List[GeoJSONFeature]:
        """Fetch oil rigs for a specific region."""
        try:
            params = {
                "limit": 200,
                "status": "active",
                "region": region,
            }

            response = await self.client.get(self.api_url, params=params)
            response.raise_for_status()

            rigs = response.json()
            features = []

            for rig in rigs:
                lat = rig.get("latitude")
                lon = rig.get("longitude")

                if lat is None or lon is None:
                    continue

                metadata = {
                    "name": rig.get("name", "Unknown Rig"),
                    "operator": rig.get("operator"),
                    "country": rig.get("country"),
                    "region": rig.get("region"),
                    "status": rig.get("status"),
                    "production": rig.get("production"),
                    "water_depth": rig.get("water_depth"),
                    "type": rig.get("type"),
                }

                feature = GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=self.source,
                    entity_type=EntityType.OIL_RIG,
                    identifier=rig.get("id", ""),
                    timestamp=datetime.utcnow(),
                    metadata=metadata,
                )
                features.append(feature)

            return features

        except Exception as e:
            logger.error(f"Error fetching oil rigs for region {region}: {e}")
            return []

    async def fetch_by_country(self, country_code: str) -> List[GeoJSONFeature]:
        """Fetch oil rigs for a specific country."""
        try:
            params = {
                "limit": 200,
                "status": "active",
                "country_code": country_code.upper(),
            }

            response = await self.client.get(self.api_url, params=params)
            response.raise_for_status()

            rigs = response.json()
            features = []

            for rig in rigs:
                lat = rig.get("latitude")
                lon = rig.get("longitude")

                if lat is None or lon is None:
                    continue

                metadata = {
                    "name": rig.get("name", "Unknown Rig"),
                    "operator": rig.get("operator"),
                    "country": rig.get("country"),
                    "region": rig.get("region"),
                    "status": rig.get("status"),
                    "production": rig.get("production"),
                    "water_depth": rig.get("water_depth"),
                    "type": rig.get("type"),
                }

                feature = GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=self.source,
                    entity_type=EntityType.OIL_RIG,
                    identifier=rig.get("id", ""),
                    timestamp=datetime.utcnow(),
                    metadata=metadata,
                )
                features.append(feature)

            return features

        except Exception as e:
            logger.error(f"Error fetching oil rigs for country {country_code}: {e}")
            return []

    async def fetch(self, **kwargs) -> List[GeoJSONFeature]:
        """Fetch oil rigs - default implementation calls fetch_data."""
        return await self.fetch_data(**kwargs)

    async def close(self):
        """Close the HTTP client."""
        if hasattr(self, '_client') and self._client and not self._client.is_closed:
            await self._client.aclose()
