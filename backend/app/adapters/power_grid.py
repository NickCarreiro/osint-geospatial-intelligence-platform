"""Power grid and substation infrastructure adapter using OpenStreetMap Overpass API."""
import logging
from typing import List, Optional
from datetime import datetime

import httpx

from app.models import DataSource, EntityType, GeoJSONFeature
from app.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class PowerGridAdapter(BaseAdapter):
    """Adapter for power grid infrastructure (lines and substations)."""

    def __init__(self, api_url: str = "https://overpass-api.de/api/interpreter"):
        super().__init__(DataSource.POWER_GRID_API)
        self.api_url = api_url
        self.cache_key_prefix = "power_grid"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def fetch_data(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch power grid data within bounding box."""
        try:
            # Build Overpass QL query for power lines and substations
            query = f"""
            [out:json][timeout:60];
            (
              way["power"~"line|cable"](around:50000,{(lamin+lamax)/2},{(lomin+lomax)/2});
              node["power"~"substation"](around:50000,{(lamin+lamax)/2},{(lomin+lomax)/2});
            );
            out body;
            >;
            out skel qt;
            """

            logger.info(f"Fetching power grid data from Overpass API")
            response = await self.client.post(
                self.api_url,
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])

            features = []

            # Process power lines (ways)
            for element in elements:
                if element.get("type") == "way" and element.get("tags", {}).get("power") in ["line", "cable"]:
                    tags = element.get("tags", {})
                    coordinates = []

                    for node in element.get("nodes", []):
                        # Get node coordinates from cached data
                        node_data = next((n for n in elements if n.get("id") == node), None)
                        if node_data and "lat" in node_data and "lon" in node_data:
                            coordinates.append([node_data["lon"], node_data["lat"]])

                    if len(coordinates) >= 2:
                        metadata = {
                            "type": "line",
                            "voltage": tags.get("voltage"),
                            "frequency": tags.get("frequency"),
                            "cables": tags.get("cables"),
                            "circuits": tags.get("circuits"),
                            "ref": tags.get("ref"),
                            "name": tags.get("name"),
                            "operator": tags.get("operator"),
                            "power": tags.get("power"),
                            "substation": tags.get("substation"),
                        }

                        feature = GeoJSONFeature(
                            type="Feature",
                            geometry={
                                "type": "LineString",
                                "coordinates": coordinates,
                            },
                            properties={
                                "source": self.source.value,
                                "entity_type": EntityType.POWER_GRID.value,
                                "timestamp": datetime.utcnow().isoformat(),
                                "identifier": str(element.get("id", "")),
                                "popup_title": f"Power Line {tags.get('ref', 'Unknown')}",
                                "metadata_keys": "type,voltage,frequency,cables,circuits,ref,name,operator,substation",
                                **{f"meta_{k}": v for k, v in metadata.items()},
                            },
                        )
                        features.append(feature)

            # Process substations (nodes)
            for element in elements:
                if element.get("type") == "node" and element.get("tags", {}).get("power") == "substation":
                    tags = element.get("tags", {})
                    lat = element.get("lat")
                    lon = element.get("lon")

                    if lat is None or lon is None:
                        continue

                    metadata = {
                        "type": "substation",
                        "voltage": tags.get("voltage"),
                        "frequency": tags.get("frequency"),
                        "substation": tags.get("substation"),
                        "name": tags.get("name"),
                        "operator": tags.get("operator"),
                        "power": tags.get("power"),
                        "rating": tags.get("rating"),
                        "ref": tags.get("ref"),
                    }

                    feature = GeoJSONFeature.create_point(
                        lon=lon,
                        lat=lat,
                        source=self.source,
                        entity_type=EntityType.POWER_SUBSTATION,
                        identifier=str(element.get("id", "")),
                        timestamp=datetime.utcnow(),
                        metadata=metadata,
                    )
                    features.append(feature)

            logger.info(f"Fetched {len(features)} power grid features")
            return features

        except Exception as e:
            logger.error(f"Error fetching power grid data: {e}")
            return []

    async def fetch_lines_only(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch only power lines (not substations)."""
        try:
            query = f"""
            [out:json][timeout:60];
            way["power"~"line|cable"](around:50000,{(lamin+lamax)/2},{(lomin+lomax)/2});
            out body;
            >;
            out skel qt;
            """

            response = await self.client.post(
                self.api_url,
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])

            features = []

            for element in elements:
                if element.get("type") == "way" and element.get("tags", {}).get("power") in ["line", "cable"]:
                    tags = element.get("tags", {})
                    coordinates = []

                    for node in element.get("nodes", []):
                        node_data = next((n for n in elements if n.get("id") == node), None)
                        if node_data and "lat" in node_data and "lon" in node_data:
                            coordinates.append([node_data["lon"], node_data["lat"]])

                    if len(coordinates) >= 2:
                        metadata = {
                            "type": "line",
                            "voltage": tags.get("voltage"),
                            "frequency": tags.get("frequency"),
                            "cables": tags.get("cables"),
                            "circuits": tags.get("circuits"),
                            "ref": tags.get("ref"),
                            "name": tags.get("name"),
                            "operator": tags.get("operator"),
                        }

                        feature = GeoJSONFeature(
                            type="Feature",
                            geometry={
                                "type": "LineString",
                                "coordinates": coordinates,
                            },
                            properties={
                                "source": self.source.value,
                                "entity_type": EntityType.POWER_GRID.value,
                                "timestamp": datetime.utcnow().isoformat(),
                                "identifier": str(element.get("id", "")),
                                "popup_title": f"Power Line {tags.get('ref', 'Unknown')}",
                                "metadata_keys": "type,voltage,frequency,cables,circuits,ref,name,operator",
                                **{f"meta_{k}": v for k, v in metadata.items()},
                            },
                        )
                        features.append(feature)

            return features

        except Exception as e:
            logger.error(f"Error fetching power lines: {e}")
            return []

    async def fetch_substations_only(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch only substations (not lines)."""
        try:
            query = f"""
            [out:json][timeout:60];
            node["power"~"substation"](around:50000,{(lamin+lamax)/2},{(lomin+lomax)/2});
            out body;
            >;
            out skel qt;
            """

            response = await self.client.post(
                self.api_url,
                data={"data": query},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()

            data = response.json()
            elements = data.get("elements", [])

            features = []

            for element in elements:
                if element.get("type") == "node" and element.get("tags", {}).get("power") == "substation":
                    tags = element.get("tags", {})
                    lat = element.get("lat")
                    lon = element.get("lon")

                    if lat is None or lon is None:
                        continue

                    metadata = {
                        "type": "substation",
                        "voltage": tags.get("voltage"),
                        "frequency": tags.get("frequency"),
                        "substation": tags.get("substation"),
                        "name": tags.get("name"),
                        "operator": tags.get("operator"),
                        "power": tags.get("power"),
                        "rating": tags.get("rating"),
                        "ref": tags.get("ref"),
                    }

                    feature = GeoJSONFeature.create_point(
                        lon=lon,
                        lat=lat,
                        source=self.source,
                        entity_type=EntityType.POWER_SUBSTATION,
                        identifier=str(element.get("id", "")),
                        timestamp=datetime.utcnow(),
                        metadata=metadata,
                    )
                    features.append(feature)

            return features

        except Exception as e:
            logger.error(f"Error fetching substations: {e}")
            return []

    async def fetch(self, **kwargs) -> List[GeoJSONFeature]:
        """Fetch power grid data - default implementation calls fetch_data."""
        return await self.fetch_data(**kwargs)

    async def close(self):
        """Close the HTTP client."""
        if hasattr(self, '_client') and self._client and not self._client.is_closed:
            await self._client.aclose()
