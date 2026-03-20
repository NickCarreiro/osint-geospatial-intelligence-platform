"""Health check endpoint for monitoring system status."""
import asyncio
import logging
from typing import Dict, Any
from datetime import datetime

from fastapi import APIRouter

from app.models import HealthResponse, SourceStatus, DataSource
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

router = APIRouter(tags=["health"])

def get_source_health_fetch_kwargs(source: DataSource) -> dict:
    """Get default fetch kwargs for source health checks."""
    report_source = REPORT_SOURCES.get(source.value)
    if not report_source or not report_source.default_bbox:
        return {}
    return report_source.default_bbox.model_dump()


# Global metrics tracking
_metrics: Dict[str, Any] = {
    "total_requests": 0,
    "total_errors": 0,
    "ingestion_latency_ms": {},
    "entity_counts": {},
    "cache_hit_rates": {},
    "source_failures": {},
}


def increment_requests():
    """Increment total request counter."""
    _metrics["total_requests"] += 1


def increment_errors():
    """Increment total error counter."""
    _metrics["total_errors"] += 1


def update_latency(source: str, latency_ms: float):
    """Update ingestion latency for a source."""
    if source not in _metrics["ingestion_latency_ms"]:
        _metrics["ingestion_latency_ms"][source] = []
    _metrics["ingestion_latency_ms"][source].append(latency_ms)

    # Keep only last 100 measurements
    if len(_metrics["ingestion_latency_ms"][source]) > 100:
        _metrics["ingestion_latency_ms"][source] = _metrics["ingestion_latency_ms"][source][-100:]


def update_entity_count(source: str, count: int):
    """Update entity count for a source."""
    _metrics["entity_counts"][source] = count


def record_failure(source: str):
    """Record a failure for a source."""
    if source not in _metrics["source_failures"]:
        _metrics["source_failures"][source] = 0
    _metrics["source_failures"][source] += 1


def get_metrics() -> Dict[str, Any]:
    """Get current metrics."""
    # Calculate average latencies
    avg_latencies = {}
    for source, latencies in _metrics["ingestion_latency_ms"].items():
        if latencies:
            avg_latencies[source] = sum(latencies) / len(latencies)

    return {
        "total_requests": _metrics["total_requests"],
        "total_errors": _metrics["total_errors"],
        "ingestion_latency_ms": avg_latencies,
        "entity_counts": _metrics["entity_counts"],
        "source_failures": _metrics["source_failures"],
    }


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """
    Get system health status.

    Returns the health status of all data sources and system metrics.
    """
    increment_requests()

    # Check all sources concurrently
    source_statuses = await check_all_sources()

    # Get cache stats
    cache_stats = await cache.get_stats()

    # Determine overall status
    all_healthy = all(status.healthy for status in source_statuses)
    overall_status = "healthy" if all_healthy else "degraded"

    # Build metrics
    metrics = get_metrics()
    metrics["cache_stats"] = cache_stats

    return HealthResponse(
        status=overall_status,
        sources=source_statuses,
        metrics=metrics,
    )


async def check_all_sources() -> list[SourceStatus]:
    """Check health status of all sources."""
    tasks = [
        check_opensky(),
        check_aisstream(),
        check_firms(),
        check_celestrak(),
        check_radio(),
        check_oil_rig(),
        check_power_grid(),
        check_fir(),
        check_maritime(),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    statuses = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"Health check error: {result}")
        elif isinstance(result, SourceStatus):
            statuses.append(result)

    return statuses


async def check_opensky() -> SourceStatus:
    """Check OpenSky source health."""
    adapter = OpenSkyAdapter()

    try:
        start_time = datetime.utcnow()
        features = await adapter.fetch_with_retry(
            max_retries=1,
            timeout=REPORT_SOURCES[DataSource.OIL_RIG_API.value].timeout_s,
            **get_source_health_fetch_kwargs(DataSource.OIL_RIG_API),
        )
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000
        update_latency("opensky", latency_ms)
        update_entity_count("opensky", len(features))

        return adapter.get_status()

    except Exception as e:
        logger.error(f"OpenSky health check failed: {e}")
        record_failure("opensky")
        return SourceStatus(
            source=DataSource.OPENSKY,
            healthy=False,
            error_message=str(e),
            entity_count=0,
        )
    finally:
        await adapter.close()


async def check_aisstream() -> SourceStatus:
    """Check AISStream source health."""
    adapter = AISStreamAdapter()

    try:
        start_time = datetime.utcnow()
        features = await adapter.fetch_with_retry(
            max_retries=1,
            timeout=REPORT_SOURCES[DataSource.POWER_GRID_API.value].timeout_s,
            **get_source_health_fetch_kwargs(DataSource.POWER_GRID_API),
        )
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000
        update_latency("aisstream", latency_ms)
        update_entity_count("aisstream", len(features))

        return adapter.get_status()

    except Exception as e:
        logger.error(f"AISStream health check failed: {e}")
        record_failure("aisstream")
        return SourceStatus(
            source=DataSource.AISSTREAM,
            healthy=False,
            error_message=str(e),
            entity_count=0,
        )
    finally:
        await adapter.close()


async def check_firms() -> SourceStatus:
    """Check FIRMS source health."""
    adapter = FIRMSAdapter()

    try:
        start_time = datetime.utcnow()
        features = await adapter.fetch_with_retry(
            max_retries=1,
            timeout=10.0,
        )
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000
        update_latency("firms", latency_ms)
        update_entity_count("firms", len(features))

        return adapter.get_status()

    except Exception as e:
        logger.error(f"FIRMS health check failed: {e}")
        record_failure("firms")
        return SourceStatus(
            source=DataSource.FIRMS,
            healthy=False,
            error_message=str(e),
            entity_count=0,
        )
    finally:
        await adapter.close()


async def check_celestrak() -> SourceStatus:
    """Check CelesTrak source health."""
    adapter = CelesTrakAdapter()

    try:
        start_time = datetime.utcnow()
        features = await adapter.fetch_with_retry(
            max_retries=1,
            timeout=10.0,
        )
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000
        update_latency("celestrak", latency_ms)
        update_entity_count("celestrak", len(features))

        return adapter.get_status()

    except Exception as e:
        logger.error(f"CelesTrak health check failed: {e}")
        record_failure("celestrak")
        return SourceStatus(
            source=DataSource.CELESTRAK,
            healthy=False,
            error_message=str(e),
            entity_count=0,
        )
    finally:
        await adapter.close()


async def check_radio() -> SourceStatus:
    """Check Radio Browser API source health."""
    adapter = RadioAdapter()

    try:
        start_time = datetime.utcnow()
        features = await adapter.fetch_with_retry(
            max_retries=1,
            timeout=10.0,
        )
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000
        update_latency("radio_api", latency_ms)
        update_entity_count("radio_api", len(features))

        return adapter.get_status()

    except Exception as e:
        logger.error(f"Radio API health check failed: {e}")
        record_failure("radio_api")
        return SourceStatus(
            source=DataSource.RADIO_API,
            healthy=False,
            error_message=str(e),
            entity_count=0,
        )
    finally:
        await adapter.close()


async def check_oil_rig() -> SourceStatus:
    """Check Oil Rig API source health."""
    adapter = OilRigAdapter()

    try:
        start_time = datetime.utcnow()
        features = await adapter.fetch_with_retry(
            max_retries=1,
            timeout=REPORT_SOURCES[DataSource.OIL_RIG_API.value].timeout_s,
            **get_source_health_fetch_kwargs(DataSource.OIL_RIG_API),
        )
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000
        update_latency("oil_rig_api", latency_ms)
        update_entity_count("oil_rig_api", len(features))

        return adapter.get_status()

    except Exception as e:
        logger.error(f"Oil Rig API health check failed: {e}")
        record_failure("oil_rig_api")
        return SourceStatus(
            source=DataSource.OIL_RIG_API,
            healthy=False,
            error_message=str(e),
            entity_count=0,
        )
    finally:
        await adapter.close()


async def check_power_grid() -> SourceStatus:
    """Check Power Grid API source health."""
    adapter = PowerGridAdapter()

    try:
        start_time = datetime.utcnow()
        features = await adapter.fetch_with_retry(
            max_retries=1,
            timeout=REPORT_SOURCES[DataSource.POWER_GRID_API.value].timeout_s,
            **get_source_health_fetch_kwargs(DataSource.POWER_GRID_API),
        )
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000
        update_latency("power_grid_api", latency_ms)
        update_entity_count("power_grid_api", len(features))

        return adapter.get_status()

    except Exception as e:
        logger.error(f"Power Grid API health check failed: {e}")
        record_failure("power_grid_api")
        return SourceStatus(
            source=DataSource.POWER_GRID_API,
            healthy=False,
            error_message=str(e),
            entity_count=0,
        )
    finally:
        await adapter.close()


async def check_fir() -> SourceStatus:
    """Check FIR API source health."""
    adapter = FIRAdapter()

    try:
        start_time = datetime.utcnow()
        features = await adapter.fetch_with_retry(
            max_retries=1,
            timeout=10.0,
        )
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000
        update_latency("fir_api", latency_ms)
        update_entity_count("fir_api", len(features))

        return adapter.get_status()

    except Exception as e:
        logger.error(f"FIR API health check failed: {e}")
        record_failure("fir_api")
        return SourceStatus(
            source=DataSource.FIR_API,
            healthy=False,
            error_message=str(e),
            entity_count=0,
        )
    finally:
        await adapter.close()


async def check_maritime() -> SourceStatus:
    """Check Maritime API source health."""
    adapter = MaritimeAdapter()

    try:
        start_time = datetime.utcnow()
        features = await adapter.fetch_with_retry(
            max_retries=1,
            timeout=10.0,
        )
        end_time = datetime.utcnow()

        latency_ms = (end_time - start_time).total_seconds() * 1000
        update_latency("maritime_api", latency_ms)
        update_entity_count("maritime_api", len(features))

        return adapter.get_status()

    except Exception as e:
        logger.error(f"Maritime API health check failed: {e}")
        record_failure("maritime_api")
        return SourceStatus(
            source=DataSource.MARITIME_API,
            healthy=False,
            error_message=str(e),
            entity_count=0,
        )
    finally:
        await adapter.close()
