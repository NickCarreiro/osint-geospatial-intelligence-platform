"""Unified API endpoint for fetching all OSINT data."""
import asyncio
import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from app.models import (
    GeoJSONFeature,
    BoundingBox,
    TimeWindow,
    EntityType,
    DataSource,
    UnifiedQuery,
)
from app.adapters import (
    OpenSkyAdapter,
    AISStreamAdapter,
    FIRMSAdapter,
    CelesTrakAdapter,
    RadioAdapter,
    OilRigAdapter,
    PowerGridAdapter,
    FIRAdapter,
    MaritimeAdapter,
)
from app.cache import cache
from app.reporting import REPORT_SOURCES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["unified"])


class GeoJSONResponse(BaseModel):
    """GeoJSON response wrapper."""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]
    metadata: dict


def get_fetch_kwargs(query: UnifiedQuery, source: Optional[DataSource] = None) -> dict:
    """Convert a query into adapter fetch kwargs."""
    if query.bbox:
        return query.bbox.model_dump()
    if source and source.value in REPORT_SOURCES:
        default_bbox = REPORT_SOURCES[source.value].default_bbox
        if default_bbox:
            return default_bbox.model_dump()
    return {}


@router.get("/unified", response_model=GeoJSONResponse)
async def get_unified_data(
    lamin: Optional[float] = Query(None, description="Minimum latitude"),
    lomin: Optional[float] = Query(None, description="Minimum longitude"),
    lamax: Optional[float] = Query(None, description="Maximum latitude"),
    lomax: Optional[float] = Query(None, description="Maximum longitude"),
    start_time: Optional[str] = Query(None, description="Start time (ISO 8601)"),
    end_time: Optional[str] = Query(None, description="End time (ISO 8601)"),
    entity_types: Optional[str] = Query(None, description="Comma-separated entity types"),
    sources: Optional[str] = Query(None, description="Comma-separated sources"),
    use_cache: bool = Query(True, description="Use cache if available"),
) -> GeoJSONResponse:
    """
    Get unified OSINT data from all sources.

    Returns normalized GeoJSON features from aircraft, vessels,
    thermal events, and satellites.
    """
    start_time_total = datetime.utcnow()

    # Parse query parameters
    bbox = None
    if all(v is not None for v in [lamin, lomin, lamax, lomax]):
        bbox = BoundingBox(lamin=lamin, lomin=lomin, lamax=lamax, lomax=lomax)

    time_window = None
    if start_time or end_time:
        time_window = TimeWindow(
            start=datetime.fromisoformat(start_time) if start_time else None,
            end=datetime.fromisoformat(end_time) if end_time else None,
        )

    entity_type_list = None
    if entity_types:
        entity_type_list = [
            EntityType(et.strip())
            for et in entity_types.split(",")
            if et.strip()
        ]

    source_list = None
    if sources:
        source_list = [
            DataSource(s.strip())
            for s in sources.split(",")
            if s.strip()
        ]

    # Create query
    query = UnifiedQuery(
        bbox=bbox,
        time_window=time_window,
        entity_types=entity_type_list,
        sources=source_list,
    )

    # Fetch data from all sources concurrently
    all_features = await fetch_all_sources(query, use_cache=use_cache)

    # Apply filters
    filtered_features = apply_filters(all_features, query)

    # Calculate metadata
    end_time_total = datetime.utcnow()
    latency_ms = (end_time_total - start_time_total).total_seconds() * 1000

    metadata = {
        "count": len(filtered_features),
        "latency_ms": round(latency_ms, 2),
        "timestamp": end_time_total.isoformat(),
        "sources": {
            "opensky": len([f for f in filtered_features if f.properties.get("source") == "opensky"]),
            "aisstream": len([f for f in filtered_features if f.properties.get("source") == "aisstream"]),
            "firms": len([f for f in filtered_features if f.properties.get("source") == "firms"]),
            "celestrak": len([f for f in filtered_features if f.properties.get("source") == "celestrak"]),
            "radio_api": len([f for f in filtered_features if f.properties.get("source") == "radio_api"]),
            "oil_rig_api": len([f for f in filtered_features if f.properties.get("source") == "oil_rig_api"]),
            "power_grid_api": len([f for f in filtered_features if f.properties.get("source") == "power_grid_api"]),
            "fir_api": len([f for f in filtered_features if f.properties.get("source") == "fir_api"]),
            "maritime_api": len([f for f in filtered_features if f.properties.get("source") == "maritime_api"]),
        },
        "entity_types": {
            "aircraft": len([f for f in filtered_features if f.properties.get("entity_type") == "aircraft"]),
            "vessel": len([f for f in filtered_features if f.properties.get("entity_type") == "vessel"]),
            "thermal_event": len([f for f in filtered_features if f.properties.get("entity_type") == "thermal_event"]),
            "satellite": len([f for f in filtered_features if f.properties.get("entity_type") == "satellite"]),
            "radio_station": len([f for f in filtered_features if f.properties.get("entity_type") == "radio_station"]),
            "oil_rig": len([f for f in filtered_features if f.properties.get("entity_type") == "oil_rig"]),
            "power_grid": len([f for f in filtered_features if f.properties.get("entity_type") == "power_grid"]),
            "power_substation": len([f for f in filtered_features if f.properties.get("entity_type") == "power_substation"]),
            "fir": len([f for f in filtered_features if f.properties.get("entity_type") == "fir"]),
            "maritime_boundary": len([f for f in filtered_features if f.properties.get("entity_type") == "maritime_boundary"]),
        },
    }

    return GeoJSONResponse(
        type="FeatureCollection",
        features=filtered_features,
        metadata=metadata,
    )


async def fetch_all_sources(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch data from all sources concurrently."""
    all_features = []

    # Determine which sources to fetch
    sources_to_fetch = query.sources or list(DataSource)

    # Create tasks for each source
    tasks = []

    for source in sources_to_fetch:
        if source == DataSource.OPENSKY:
            tasks.append(fetch_opensky(query, use_cache))
        elif source == DataSource.AISSTREAM:
            tasks.append(fetch_aisstream(query, use_cache))
        elif source == DataSource.FIRMS:
            tasks.append(fetch_firms(query, use_cache))
        elif source == DataSource.CELESTRAK:
            tasks.append(fetch_celestrak(query, use_cache))
        elif source == DataSource.RADIO_API:
            tasks.append(fetch_radio(query, use_cache))
        elif source == DataSource.OIL_RIG_API:
            tasks.append(fetch_oil_rig(query, use_cache))
        elif source == DataSource.POWER_GRID_API:
            tasks.append(fetch_power_grid(query, use_cache))
        elif source == DataSource.FIR_API:
            tasks.append(fetch_fir(query, use_cache))
        elif source == DataSource.MARITIME_API:
            tasks.append(fetch_maritime(query, use_cache))

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Source fetch error: {result}")
        elif isinstance(result, list):
            all_features.extend(result)

    return all_features


async def fetch_opensky(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch aircraft data from OpenSky."""
    adapter = OpenSkyAdapter()

    try:
        features = await adapter.fetch_with_retry(
            timeout=30.0,
            **get_fetch_kwargs(query),
        )

        # Cache features
        if use_cache and features:
            await cache.set_many(features)

        return features

    except Exception as e:
        logger.error(f"OpenSky fetch error: {e}")
        return []
    finally:
        await adapter.close()


async def fetch_aisstream(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch vessel data from AISStream."""
    adapter = AISStreamAdapter()

    try:
        features = await adapter.fetch_with_retry(
            timeout=60.0,
        )

        # Cache features
        if use_cache and features:
            await cache.set_many(features)

        return features

    except Exception as e:
        logger.error(f"AISStream fetch error: {e}")
        return []
    finally:
        await adapter.close()


async def fetch_firms(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch thermal data from FIRMS."""
    adapter = FIRMSAdapter()

    try:
        features = await adapter.fetch_with_retry(
            timeout=30.0,
            **get_fetch_kwargs(query),
        )

        # Cache features
        if use_cache and features:
            await cache.set_many(features)

        return features

    except Exception as e:
        logger.error(f"FIRMS fetch error: {e}")
        return []
    finally:
        await adapter.close()


async def fetch_celestrak(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch satellite data from CelesTrak."""
    adapter = CelesTrakAdapter()

    try:
        features = await adapter.fetch_with_retry(
            timeout=REPORT_SOURCES[DataSource.OIL_RIG_API.value].timeout_s,
            **get_fetch_kwargs(query, DataSource.OIL_RIG_API),
        )

        # Cache features
        if use_cache and features:
            await cache.set_many(features)

        return features

    except Exception as e:
        logger.error(f"CelesTrak fetch error: {e}")
        return []
    finally:
        await adapter.close()


async def fetch_radio(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch radio station data from Radio Browser API."""
    adapter = RadioAdapter()

    try:
        features = await adapter.fetch_with_retry(
            timeout=30.0,
        )

        # Cache features
        if use_cache and features:
            await cache.set_many(features)

        return features

    except Exception as e:
        logger.error(f"Radio API fetch error: {e}")
        return []
    finally:
        await adapter.close()


async def fetch_oil_rig(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch oil rig data from Oil Rig API."""
    adapter = OilRigAdapter()

    try:
        features = await adapter.fetch_with_retry(
            timeout=REPORT_SOURCES[DataSource.OIL_RIG_API.value].timeout_s,
            **get_fetch_kwargs(query, DataSource.OIL_RIG_API),
        )

        # Cache features
        if use_cache and features:
            await cache.set_many(features)

        return features

    except Exception as e:
        logger.error(f"Oil Rig API fetch error: {e}")
        return []
    finally:
        await adapter.close()


async def fetch_power_grid(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch power grid data from OpenStreetMap Overpass API."""
    adapter = PowerGridAdapter()

    try:
        features = await adapter.fetch_with_retry(
            timeout=REPORT_SOURCES[DataSource.POWER_GRID_API.value].timeout_s,
            **get_fetch_kwargs(query, DataSource.POWER_GRID_API),
        )

        # Cache features
        if use_cache and features:
            await cache.set_many(features)

        return features

    except Exception as e:
        logger.error(f"Power Grid API fetch error: {e}")
        return []
    finally:
        await adapter.close()


async def fetch_fir(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch FIR data from ICAO."""
    adapter = FIRAdapter()

    try:
        features = await adapter.fetch_with_retry(
            timeout=30.0,
            **get_fetch_kwargs(query, DataSource.FIR_API),
        )

        # Cache features
        if use_cache and features:
            await cache.set_many(features)

        return features

    except Exception as e:
        logger.error(f"FIR API fetch error: {e}")
        return []
    finally:
        await adapter.close()


async def fetch_maritime(
    query: UnifiedQuery,
    use_cache: bool = True,
) -> List[GeoJSONFeature]:
    """Fetch maritime boundary data from Natural Earth."""
    adapter = MaritimeAdapter()

    try:
        features = await adapter.fetch_with_retry(
            timeout=30.0,
            **get_fetch_kwargs(query, DataSource.MARITIME_API),
        )

        # Cache features
        if use_cache and features:
            await cache.set_many(features)

        return features

    except Exception as e:
        logger.error(f"Maritime API fetch error: {e}")
        return []
    finally:
        await adapter.close()


def apply_filters(
    features: List[GeoJSONFeature],
    query: UnifiedQuery,
) -> List[GeoJSONFeature]:
    """Apply filters to features."""
    filtered = features

    # Apply bounding box filter
    if query.bbox:
        filtered = [
            f for f in filtered
            if query.bbox.contains(
                f.geometry["coordinates"][0],
                f.geometry["coordinates"][1],
            )
        ]

    # Apply time window filter
    if query.time_window:
        filtered = [
            f for f in filtered
            if query.time_window.contains(
                datetime.fromisoformat(f.properties["timestamp"])
            )
        ]

    # Apply entity type filter
    if query.entity_types:
        filtered = [
            f for f in filtered
            if f.properties["entity_type"] in [et.value for et in query.entity_types]
        ]

    # Apply source filter
    if query.sources:
        filtered = [
            f for f in filtered
            if f.properties["source"] in [s.value for s in query.sources]
        ]

    return filtered
