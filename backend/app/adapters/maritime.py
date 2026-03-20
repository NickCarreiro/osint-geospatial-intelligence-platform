"""Maritime boundaries adapter using Natural Earth marine polygons."""
import logging
from datetime import datetime
from typing import Iterator, List, Optional

import httpx

from app.adapters.base import AdapterError, BaseAdapter
from app.models import DataSource, EntityType, GeoJSONFeature

logger = logging.getLogger(__name__)


class MaritimeAdapter(BaseAdapter):
    """Adapter for maritime boundaries."""

    def __init__(
        self,
        api_url: str = (
            "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
            "ne_10m_geography_marine_polys.geojson"
        ),
    ):
        super().__init__(DataSource.MARITIME_API)
        self.api_url = api_url
        self.cache_key_prefix = "maritime_boundaries"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _iter_coordinates(self, coordinates) -> Iterator[tuple[float, float]]:
        """Yield lon/lat pairs from nested GeoJSON coordinate arrays."""
        if not isinstance(coordinates, list):
            return
        if len(coordinates) >= 2 and all(isinstance(value, (int, float)) for value in coordinates[:2]):
            yield coordinates[0], coordinates[1]
            return
        for item in coordinates:
            yield from self._iter_coordinates(item)

    def _intersects_bbox(
        self,
        geometry: dict,
        lamin: Optional[float],
        lomin: Optional[float],
        lamax: Optional[float],
        lomax: Optional[float],
    ) -> bool:
        """Approximate bbox intersection test using geometry extents."""
        if None in (lamin, lomin, lamax, lomax):
            return True

        coords = list(self._iter_coordinates(geometry.get("coordinates", [])))
        if not coords:
            return False

        min_lon = min(lon for lon, _ in coords)
        max_lon = max(lon for lon, _ in coords)
        min_lat = min(lat for _, lat in coords)
        max_lat = max(lat for _, lat in coords)

        return not (
            max_lat < lamin or min_lat > lamax or max_lon < lomin or min_lon > lomax
        )

    async def fetch_data(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch maritime boundaries, optionally filtered to a bbox."""
        try:
            logger.info(f"Fetching maritime boundaries from {self.api_url}")
            client = await self._get_client()
            response = await client.get(self.api_url)
            response.raise_for_status()

            data = response.json()
            if data.get("type") == "FeatureCollection":
                geojson_features = data.get("features", [])
            elif data.get("type") == "Feature":
                geojson_features = [data]
            else:
                raise AdapterError(f"Unexpected GeoJSON structure: {data.get('type')}")

            features = []
            for feature in geojson_features:
                geometry = feature.get("geometry")
                properties = feature.get("properties", {})
                if not geometry or not self._intersects_bbox(geometry, lamin, lomin, lamax, lomax):
                    continue

                name = properties.get("name", properties.get("NAME", "Unknown"))
                water_type = properties.get("featurecla", properties.get("FEATURECLA", "marine_area"))
                country = properties.get("country", properties.get("COUNTRY", "Unknown"))
                country_code = properties.get("country_code", properties.get("ISO_A2", ""))
                featurecla = properties.get("featurecla", properties.get("FEATURECLA", ""))
                is_international = country in {"", "Unknown"} or water_type.lower() == "ocean"
                is_national = not is_international

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

                features.append(
                    GeoJSONFeature(
                        type="Feature",
                        geometry=geometry,
                        properties={
                            "source": self.source.value,
                            "entity_type": EntityType.MARITIME_BOUNDARY.value,
                            "timestamp": datetime.utcnow().isoformat(),
                            "identifier": str(feature.get("id", "")),
                            "popup_title": f"{name} ({water_type})",
                            "metadata": metadata,
                            "metadata_keys": (
                                "name,water_type,country,country_code,featurecla,"
                                "is_international,is_national,type"
                            ),
                            **{f"meta_{key}": value for key, value in metadata.items()},
                        },
                    )
                )

            logger.info(f"Fetched {len(features)} maritime boundaries")
            return features
        except Exception as e:
            logger.error(f"Error fetching maritime boundaries: {e}")
            raise AdapterError(f"Maritime fetch failed: {e}") from e

    async def fetch_international_waters(self) -> List[GeoJSONFeature]:
        """Fetch only international waters."""
        all_features = await self.fetch_data()
        return [feature for feature in all_features if feature.properties.get("meta_is_international", False)]

    async def fetch_national_waters(self) -> List[GeoJSONFeature]:
        """Fetch only national waters."""
        all_features = await self.fetch_data()
        return [feature for feature in all_features if feature.properties.get("meta_is_national", False)]

    async def fetch_by_country(self, country_code: str) -> List[GeoJSONFeature]:
        """Fetch maritime boundaries for a specific country."""
        all_features = await self.fetch_data()
        return [
            feature
            for feature in all_features
            if feature.properties.get("meta_country_code", "").upper() == country_code.upper()
        ]

    async def fetch(self, country_code: Optional[str] = None, **kwargs) -> List[GeoJSONFeature]:
        """Fetch maritime data - default implementation calls fetch_data."""
        if country_code:
            return await self.fetch_by_country(country_code)
        return await self.fetch_data(**kwargs)

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
