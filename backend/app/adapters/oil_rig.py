"""Oil rig adapter backed by OpenStreetMap offshore platform data."""
import logging
from datetime import datetime
from typing import List, Optional

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


class OilRigAdapter(BaseAdapter):
    """Adapter for offshore platforms using Overpass."""

    def __init__(self, api_url: str = DEFAULT_OVERPASS_URLS[0]):
        super().__init__(DataSource.OIL_RIG_API)
        self.api_url = api_url
        self.api_urls = build_overpass_urls(api_url)
        self.cache_key_prefix = "oil_rigs"
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = create_overpass_client(timeout_s=25.0)
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
            raise AdapterError("Oil rig fetch requires lamin, lomin, lamax, and lomax")
        return lamin, lomin, lamax, lomax

    @staticmethod
    def _element_coordinates(element: dict) -> tuple[Optional[float], Optional[float]]:
        """Extract coordinates from an OSM node/way/relation."""
        center = element.get("center", {})
        lat = element.get("lat", center.get("lat"))
        lon = element.get("lon", center.get("lon"))
        if lat is None or lon is None:
            return None, None
        return lat, lon

    async def fetch_data(
        self,
        lamin: Optional[float] = None,
        lomin: Optional[float] = None,
        lamax: Optional[float] = None,
        lomax: Optional[float] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch offshore platforms within a bbox."""
        try:
            lamin, lomin, lamax, lomax = self._require_bbox(lamin, lomin, lamax, lomax)
            query = f"""
            [out:json][timeout:60];
            (
              node["man_made"="offshore_platform"]({lamin},{lomin},{lamax},{lomax});
              way["man_made"="offshore_platform"]({lamin},{lomin},{lamax},{lomax});
              relation["man_made"="offshore_platform"]({lamin},{lomin},{lamax},{lomax});
            );
            out center tags;
            """

            logger.info("Fetching oil rigs from Overpass-compatible APIs")
            client = await self._get_client()
            errors = []
            elements = []
            for url in self.api_urls:
                try:
                    response = await client.post(
                        url,
                        data={"data": query},
                        headers=OVERPASS_FORM_HEADERS,
                    )
                    payload = parse_overpass_payload(response, url)
                    self.api_url = url
                    elements = payload.get("elements", [])
                    break
                except (AdapterError, httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError) as e:
                    error_detail = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                    logger.warning(f"Oil rig query failed against {url}: {error_detail}")
                    errors.append(f"{url}: {error_detail}")
            else:
                raise AdapterError("All oil rig upstreams failed: " + " | ".join(errors))

            features = []
            for element in elements:
                lat, lon = self._element_coordinates(element)
                if lat is None or lon is None:
                    continue

                tags = element.get("tags", {})
                metadata = {
                    "name": tags.get("name", f"Offshore Platform {element.get('id', '')}"),
                    "operator": tags.get("operator"),
                    "country": tags.get("addr:country"),
                    "country_code": tags.get("ISO3166-1"),
                    "region": tags.get("region"),
                    "status": tags.get("status"),
                    "production": tags.get("production"),
                    "water_depth": tags.get("seamark:platform:water_depth"),
                    "type": tags.get("man_made"),
                    "commissioned": tags.get("start_date"),
                    "latitude": lat,
                    "longitude": lon,
                    "osm_id": element.get("id"),
                    "osm_type": element.get("type"),
                    "tags": tags,
                }

                features.append(
                    GeoJSONFeature.create_point(
                        lon=lon,
                        lat=lat,
                        source=self.source,
                        entity_type=EntityType.OIL_RIG,
                        identifier=str(element.get("id", "")),
                        timestamp=datetime.utcnow(),
                        metadata=metadata,
                    )
                )

            logger.info(f"Fetched {len(features)} oil rigs")
            return features
        except Exception as e:
            logger.error(f"Error fetching oil rigs: {e}")
            raise AdapterError(f"Oil rig fetch failed: {e}") from e

    async def fetch_by_region(self, region: str) -> List[GeoJSONFeature]:
        """Region-specific filtering is not implemented for OSM oil rigs."""
        raise AdapterError(
            f"Region filter '{region}' is not implemented for the Overpass-backed oil rig adapter"
        )

    async def fetch_by_country(self, country_code: str) -> List[GeoJSONFeature]:
        """Country-specific filtering is not implemented for OSM oil rigs."""
        raise AdapterError(
            f"Country filter '{country_code}' is not implemented for the Overpass-backed oil rig adapter"
        )

    async def fetch(self, **kwargs) -> List[GeoJSONFeature]:
        """Fetch oil rigs - default implementation calls fetch_data."""
        return await self.fetch_data(**kwargs)

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
