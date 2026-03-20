"""Power grid and substation infrastructure adapter using Overpass."""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from app.adapters.base import AdapterError, BaseAdapter
from app.adapters.overpass import (
    DEFAULT_OVERPASS_URLS,
    OVERPASS_FORM_HEADERS,
    build_overpass_urls,
    create_overpass_client,
    parse_overpass_payload,
)
from app.models import DataSource, EntityType, GeoJSONFeature

logger = logging.getLogger(__name__)


class PowerGridAdapter(BaseAdapter):
    """Adapter for power lines and substations from OpenStreetMap."""

    def __init__(self, api_url: str = DEFAULT_OVERPASS_URLS[0]):
        super().__init__(DataSource.POWER_GRID_API)
        self.api_url = api_url
        self.api_urls = build_overpass_urls(api_url)
        self.cache_key_prefix = "power_grid"
        self._client: Optional[httpx.AsyncClient] = None
        self.warning_message: Optional[str] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = create_overpass_client(timeout_s=12.0)
        return self._client

    @staticmethod
    def _require_bbox(
        lamin: Optional[float],
        lomin: Optional[float],
        lamax: Optional[float],
        lomax: Optional[float],
    ) -> tuple[float, float, float, float]:
        """Validate the bbox required by the Overpass query."""
        if None in (lamin, lomin, lamax, lomax):
            raise AdapterError("Power grid fetch requires lamin, lomin, lamax, and lomax")
        return lamin, lomin, lamax, lomax

    async def _fetch_elements(
        self,
        query: str,
        endpoint_offset: int = 0,
    ) -> List[dict]:
        """Execute an Overpass query and return raw elements."""
        client = await self._get_client()
        errors = []
        urls = self.api_urls[endpoint_offset:] + self.api_urls[:endpoint_offset]
        for url in urls:
            try:
                response = await client.post(
                    url,
                    data={"data": query},
                    headers=OVERPASS_FORM_HEADERS,
                )
                payload = parse_overpass_payload(response, url)
                self.api_url = url
                self.api_urls = build_overpass_urls(url)
                return payload.get("elements", [])
            except (AdapterError, httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
                error_detail = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                logger.warning(f"Power grid query failed against {url}: {error_detail}")
                errors.append(f"{url}: {error_detail}")

        raise AdapterError("All power grid upstreams failed: " + " | ".join(errors))

    async def _fetch_elements_with_retries(
        self,
        query: str,
        label: str,
        max_attempts: int = 2,
    ) -> List[dict]:
        """Retry a single Overpass subquery before declaring it degraded."""
        last_error: Optional[Exception] = None
        for attempt in range(max_attempts):
            try:
                return await self._fetch_elements(query)
            except AdapterError as e:
                last_error = e
                if attempt < max_attempts - 1:
                    delay = min(2.0 * (attempt + 1), 5.0)
                    logger.info(f"Retrying power grid {label} query in {delay:.1f}s")
                    await asyncio.sleep(delay)

        raise AdapterError(f"{label} query failed after {max_attempts} attempts: {last_error}")

    @staticmethod
    def _node_lookup(elements: List[dict]) -> Dict[int, dict]:
        """Build a lookup table for node coordinates."""
        return {element["id"]: element for element in elements if element.get("type") == "node"}

    @staticmethod
    def _element_coordinates(element: dict) -> tuple[Optional[float], Optional[float]]:
        """Extract coordinates from an OSM node, way, or relation."""
        center = element.get("center", {})
        lat = element.get("lat", center.get("lat"))
        lon = element.get("lon", center.get("lon"))
        if lat is None or lon is None:
            return None, None
        return lat, lon

    def _line_features(self, elements: List[dict]) -> List[GeoJSONFeature]:
        """Convert Overpass line elements into GeoJSON features."""
        features = []
        nodes = self._node_lookup(elements)
        for element in elements:
            if element.get("type") != "way":
                continue

            tags = element.get("tags", {})
            if tags.get("power") not in {"line", "cable"}:
                continue

            coordinates = []
            for node_id in element.get("nodes", []):
                node = nodes.get(node_id)
                if node and "lat" in node and "lon" in node:
                    coordinates.append([node["lon"], node["lat"]])

            if len(coordinates) < 2:
                continue

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

            features.append(
                GeoJSONFeature(
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
                        "metadata": metadata,
                        "metadata_keys": "type,voltage,frequency,cables,circuits,ref,name,operator,substation",
                        **{f"meta_{key}": value for key, value in metadata.items()},
                    },
                )
            )

        return features

    @staticmethod
    def _substation_features(elements: List[dict], source: DataSource) -> List[GeoJSONFeature]:
        """Convert Overpass node elements into substation features."""
        features = []
        for element in elements:
            if element.get("type") not in {"node", "way", "relation"}:
                continue

            tags = element.get("tags", {})
            if tags.get("power") != "substation":
                continue

            lat, lon = PowerGridAdapter._element_coordinates(element)
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

            features.append(
                GeoJSONFeature.create_point(
                    lon=lon,
                    lat=lat,
                    source=source,
                    entity_type=EntityType.POWER_SUBSTATION,
                    identifier=str(element.get("id", "")),
                    timestamp=datetime.utcnow(),
                    metadata=metadata,
                )
            )

        return features

    async def fetch_data(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch power lines and substations within a bbox."""
        try:
            logger.info("Fetching power grid data from Overpass API")
            self.warning_message = None
            features: List[GeoJSONFeature] = []
            errors = []

            try:
                features.extend(
                    await self.fetch_lines_only(lamin=lamin, lomin=lomin, lamax=lamax, lomax=lomax)
                )
            except Exception as e:
                logger.warning(f"Power line fetch degraded: {e}")
                errors.append(f"lines: {e}")

            try:
                features.extend(
                    await self.fetch_substations_only(lamin=lamin, lomin=lomin, lamax=lamax, lomax=lomax)
                )
            except Exception as e:
                logger.warning(f"Power substation fetch degraded: {e}")
                errors.append(f"substations: {e}")

            if errors and features:
                self.warning_message = "Partial power grid data: " + " | ".join(errors)
                logger.warning(self.warning_message)

            if errors and not features:
                raise AdapterError(" | ".join(errors))

            logger.info(f"Fetched {len(features)} power grid features")
            return features
        except Exception as e:
            logger.error(f"Error fetching power grid data: {e}")
            raise AdapterError(f"Power grid fetch failed: {e}") from e

    async def fetch_lines_only(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch only power lines."""
        try:
            lamin, lomin, lamax, lomax = self._require_bbox(lamin, lomin, lamax, lomax)
            query = f"""
            [out:json][timeout:60];
            way["power"~"line|cable"]({lamin},{lomin},{lamax},{lomax});
            out body;
            >;
            out skel qt;
            """
            return self._line_features(await self._fetch_elements_with_retries(query, "lines"))
        except Exception as e:
            logger.error(f"Error fetching power lines: {e}")
            raise AdapterError(f"Power line fetch failed: {e}") from e

    async def fetch_substations_only(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch only substations."""
        try:
            lamin, lomin, lamax, lomax = self._require_bbox(lamin, lomin, lamax, lomax)
            query = f"""
            [out:json][timeout:60];
            node["power"="substation"]({lamin},{lomin},{lamax},{lomax});
            out body;
            """
            return self._substation_features(
                await self._fetch_elements_with_retries(query, "substations"),
                self.source,
            )
        except Exception as e:
            logger.error(f"Error fetching substations: {e}")
            raise AdapterError(f"Power substation fetch failed: {e}") from e

    async def fetch(self, **kwargs) -> List[GeoJSONFeature]:
        """Fetch power grid data - default implementation calls fetch_data."""
        return await self.fetch_data(**kwargs)

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
