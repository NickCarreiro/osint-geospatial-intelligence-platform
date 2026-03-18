"""Flight Information Regions (FIR) adapter for airspace boundaries."""
import logging
from typing import List, Optional
from datetime import datetime

import httpx

from app.models import DataSource, EntityType, GeoJSONFeature
from app.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class FIRAdapter(BaseAdapter):
    """Adapter for Flight Information Regions (FIRs) - airspace boundaries."""

    def __init__(self, api_url: str = "https://raw.githubusercontent.com/ICAO/ICAO-Aeronautical-Information-Data/master/FIRs.geojson"):
        super().__init__(DataSource.FIR_API)
        self.api_url = api_url
        self.cache_key_prefix = "firs"
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
        """Fetch FIRs within bounding box."""
        try:
            logger.info(f"Fetching FIR data from {self.api_url}")
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

                    # Extract country from properties
                    country = properties.get("country", properties.get("Country", "Unknown"))
                    icao_code = properties.get("icao", properties.get("ICAO", ""))
                    name = properties.get("name", properties.get("Name", "Unknown FIR"))

                    metadata = {
                        "name": name,
                        "icao_code": icao_code,
                        "country": country,
                        "country_code": properties.get("country_code", ""),
                        "type": properties.get("type", "FIR"),
                        "source": properties.get("source", "ICAO"),
                    }

                    feature = GeoJSONFeature(
                        type="Feature",
                        geometry=geometry,
                        properties={
                            "source": self.source.value,
                            "entity_type": EntityType.FIR.value,
                            "timestamp": datetime.utcnow().isoformat(),
                            "identifier": icao_code or str(feature.get("id", "")),
                            "popup_title": f"{name} ({icao_code})",
                            "metadata_keys": "name,icao_code,country,country_code,type,source",
                            **{f"meta_{k}": v for k, v in metadata.items()},
                        },
                    )
                    features.append(feature)

            logger.info(f"Fetched {len(features)} FIRs")
            return features

        except Exception as e:
            logger.error(f"Error fetching FIR data: {e}")
            return []

    async def fetch_by_country(self, country_code: str) -> List[GeoJSONFeature]:
        """Fetch FIRs for a specific country."""
        try:
            # Fetch all FIRs and filter by country
            all_features = await self.fetch_data()
            filtered = [
                f for f in all_features
                if f.properties.get("meta_country_code", "").upper() == country_code.upper()
            ]
            return filtered

        except Exception as e:
            logger.error(f"Error fetching FIRs for country {country_code}: {e}")
            return []

    async def fetch_by_icao(self, icao_code: str) -> List[GeoJSONFeature]:
        """Fetch a specific FIR by ICAO code."""
        try:
            all_features = await self.fetch_data()
            filtered = [
                f for f in all_features
                if f.properties.get("meta_icao_code", "").upper() == icao_code.upper()
            ]
            return filtered

        except Exception as e:
            logger.error(f"Error fetching FIR by ICAO {icao_code}: {e}")
            return []

    async def fetch(self, **kwargs) -> List[GeoJSONFeature]:
        """Fetch FIR data - default implementation calls fetch_data."""
        return await self.fetch_data(**kwargs)

    async def close(self):
        """Close the HTTP client."""
        if hasattr(self, '_client') and self._client and not self._client.is_closed:
            await self._client.aclose()
