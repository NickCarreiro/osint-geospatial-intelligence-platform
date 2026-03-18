"""Maritime boundaries adapter for international and national waters."""
import logging
from typing import List, Optional
from datetime import datetime

import httpx

from app.models import DataSource, EntityType, GeoJSONFeature
from app.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class MaritimeAdapter(BaseAdapter):
    """Adapter for maritime boundaries (EEZ, territorial waters)."""

    def __init__(self, api_url: str = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/10m-geojson.json"):
        super().__init__(DataSource.MARITIME_API)
        self.api_url = api_url
        self.cache_key_prefix = "maritime_boundaries"
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
        """Fetch maritime boundaries within bounding box."""
        try:
            logger.info(f"Fetching maritime boundaries from {self.api_url}")
            response = await self.client.get(self.api_url)
            response.raise_for_status()

            data = response.json()

            # Handle different GeoJSON structures
            features = []
            if data.get("type") == "FeatureCollection":
                geojson_features = data.get("features", [])
            elif data.get("type") == "Feature":
                geojson_features = [data]
            else:
                logger.warning(f"Unexpected GeoJSON structure: {data.get('type')}")
                return []

            for feature in geojson_features:
                geometry = feature.get("geometry")
                properties = feature.get("properties", {})

                # Extract coordinates
                if geometry:
                    # Handle Polygon
                    if geometry.get("type") == "Polygon":
                        coordinates = geometry.get("coordinates", [])
                        if coordinates and len(coordinates) > 0:
                            # Flatten the polygon coordinates
                            flat_coords = []
                            for ring in coordinates:
                                flat_coords.extend(ring)
                            geometry["coordinates"] = flat_coords

                    # Handle MultiPolygon
                    elif geometry.get("type") == "MultiPolygon":
                        flat_coords = []
                        for polygon in geometry.get("coordinates", []):
                            for ring in polygon:
                                flat_coords.extend(ring)
                        geometry["coordinates"] = flat_coords

                    # Extract maritime information
                    name = properties.get("name", properties.get("NAME", "Unknown"))
                    water_type = properties.get("water_type", properties.get("WATER_TYPE", "unknown"))
                    country = properties.get("country", properties.get("COUNTRY", "Unknown"))
                    country_code = properties.get("country_code", properties.get("ISO_A2", ""))
                    featurecla = properties.get("featurecla", properties.get("FEATURECLA", ""))

                    # Determine if it's international or national waters
                    is_international = water_type.lower() in ["international", "international waters", "high seas"]
                    is_national = water_type.lower() in ["national", "territorial waters", "internal waters"]

                    metadata = {
                        "name": name,
                        "water_type": water_type,
                        "country": country,
                        "country_code": country_code,
                        "featurecla": featurecla,
                        "is_international": is_international,
                        "is_national": is_national,
                        "type": "maritime_boundary",
                    }

                    feature = GeoJSONFeature(
                        type="Feature",
                        geometry=geometry,
                        properties={
                            "source": self.source.value,
                            "entity_type": EntityType.MARITIME_BOUNDARY.value,
                            "timestamp": datetime.utcnow().isoformat(),
                            "identifier": str(feature.get("id", "")),
                            "popup_title": f"{name} ({water_type})",
                            "metadata_keys": "name,water_type,country,country_code,featurecla,is_international,is_national,type",
                            **{f"meta_{k}": v for k, v in metadata.items()},
                        },
                    )
                    features.append(feature)

            logger.info(f"Fetched {len(features)} maritime boundaries")
            return features

        except Exception as e:
            logger.error(f"Error fetching maritime boundaries: {e}")
            return []

    async def fetch_international_waters(self) -> List[GeoJSONFeature]:
        """Fetch only international waters."""
        try:
            all_features = await self.fetch_data()
            filtered = [
                f for f in all_features
                if f.properties.get("meta_is_international", False)
            ]
            return filtered

        except Exception as e:
            logger.error(f"Error fetching international waters: {e}")
            return []

    async def fetch_national_waters(self) -> List[GeoJSONFeature]:
        """Fetch only national waters."""
        try:
            all_features = await self.fetch_data()
            filtered = [
                f for f in all_features
                if f.properties.get("meta_is_national", False)
            ]
            return filtered

        except Exception as e:
            logger.error(f"Error fetching national waters: {e}")
            return []

    async def fetch_by_country(self, country_code: str) -> List[GeoJSONFeature]:
        """Fetch maritime boundaries for a specific country."""
        try:
            all_features = await self.fetch_data()
            filtered = [
                f for f in all_features
                if f.properties.get("meta_country_code", "").upper() == country_code.upper()
            ]
            return filtered

        except Exception as e:
            logger.error(f"Error fetching maritime boundaries for country {country_code}: {e}")
            return []

    async def fetch(self, **kwargs) -> List[GeoJSONFeature]:
        """Fetch maritime boundaries - default implementation calls fetch_data."""
        return await self.fetch_data(**kwargs)

    async def close(self):
        """Close the HTTP client."""
        if hasattr(self, '_client') and self._client and not self._client.is_closed:
            await self._client.aclose()
