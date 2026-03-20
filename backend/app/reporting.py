"""Generate backend-only JSON snapshots for selected data sources."""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

from app.adapters import MaritimeAdapter, OilRigAdapter, PowerGridAdapter, RadioAdapter
from app.countries import ResolvedCountry
from app.models import BoundingBox, DataSource

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
REPORT_INDEX_NAME = "index.json"


@dataclass(frozen=True)
class ReportSource:
    """Configuration for a reportable source."""

    source: str
    adapter_factory: Callable[[], object]
    timeout_s: float
    max_retries: int = 1
    country_mode: str = "bbox"
    default_bbox: Optional[BoundingBox] = None
    report_filename: Optional[str] = None

    @property
    def output_filename(self) -> str:
        """Return the JSON filename for this source report."""
        return self.report_filename or f"{self.source}.json"


REPORT_SOURCES = {
    DataSource.RADIO_API.value: ReportSource(
        source=DataSource.RADIO_API.value,
        adapter_factory=RadioAdapter,
        timeout_s=30.0,
        country_mode="country_code",
    ),
    DataSource.OIL_RIG_API.value: ReportSource(
        source=DataSource.OIL_RIG_API.value,
        adapter_factory=OilRigAdapter,
        timeout_s=120.0,
        max_retries=2,
        default_bbox=BoundingBox(lamin=28.6, lomin=-90.6, lamax=28.8, lomax=-90.2),
    ),
    DataSource.POWER_GRID_API.value: ReportSource(
        source=DataSource.POWER_GRID_API.value,
        adapter_factory=PowerGridAdapter,
        timeout_s=120.0,
        max_retries=2,
        default_bbox=BoundingBox(lamin=52.505, lomin=13.398, lamax=52.528, lomax=13.447),
    ),
    DataSource.MARITIME_API.value: ReportSource(
        source=DataSource.MARITIME_API.value,
        adapter_factory=MaritimeAdapter,
        timeout_s=30.0,
        country_mode="country_code",
    ),
}


def _bbox_payload(bbox: Optional[BoundingBox]) -> Optional[dict]:
    """Convert a BoundingBox into a JSON-serializable payload."""
    if bbox is None:
        return None
    return bbox.model_dump()


def _country_payload(country: Optional[ResolvedCountry]) -> Optional[dict]:
    """Convert resolved country metadata into a JSON-serializable payload."""
    if country is None:
        return None
    return country.model_dump()


def _utc_now_iso() -> str:
    """Return an ISO-8601 UTC timestamp with timezone information."""
    return datetime.now(timezone.utc).isoformat()


def get_reports_dir(output_dir: Optional[Path] = None) -> Path:
    """Resolve the report output directory."""
    return (output_dir or REPORTS_DIR).resolve()


def get_source_report_path(source_name: str, output_dir: Optional[Path] = None) -> Path:
    """Return the stable JSON file path for a report source."""
    source = get_report_source(source_name)
    return get_reports_dir(output_dir) / source.output_filename


def get_index_report_path(output_dir: Optional[Path] = None) -> Path:
    """Return the JSON file path for the batch report index."""
    return get_reports_dir(output_dir) / REPORT_INDEX_NAME


async def build_source_report(
    source: ReportSource,
    bbox_override: Optional[BoundingBox] = None,
    country_override: Optional[ResolvedCountry] = None,
) -> dict:
    """Fetch one source and build its report payload."""
    adapter = source.adapter_factory()
    bbox = bbox_override or source.default_bbox
    fetch_kwargs = bbox.model_dump() if bbox else {}

    if country_override:
        bbox = country_override.bbox
        if source.country_mode == "country_code" and country_override.iso_a2:
            fetch_kwargs = {"country_code": country_override.iso_a2}
        else:
            fetch_kwargs = bbox.model_dump()

    generated_at = _utc_now_iso()

    try:
        features = await adapter.fetch_with_retry(
            max_retries=source.max_retries,
            timeout=source.timeout_s,
            **fetch_kwargs,
        )
        status = adapter.get_status()
        warning_message = getattr(adapter, "warning_message", None)

        if status.error_message:
            report_status = "error"
        elif warning_message:
            report_status = "partial"
        elif features:
            report_status = "ok"
        else:
            report_status = "empty"

        return {
            "source": source.source,
            "report_file": source.output_filename,
            "generated_at": generated_at,
            "status": report_status,
            "healthy": status.healthy,
            "error_message": status.error_message,
            "warning_message": warning_message,
            "country": _country_payload(country_override),
            "bbox": _bbox_payload(bbox),
            "entity_count": len(features),
            "latency_ms": status.latency_ms,
            "source_url": getattr(adapter, "api_url", None),
            "features": [feature.model_dump(mode="json") for feature in features],
        }
    except Exception as e:
        return {
            "source": source.source,
            "report_file": source.output_filename,
            "generated_at": generated_at,
            "status": "error",
            "healthy": False,
            "error_message": str(e),
            "warning_message": None,
            "country": _country_payload(country_override),
            "bbox": _bbox_payload(bbox),
            "entity_count": 0,
            "latency_ms": None,
            "source_url": getattr(adapter, "api_url", None),
            "features": [],
        }
    finally:
        if hasattr(adapter, "close"):
            await adapter.close()


def get_report_source(source_name: str) -> ReportSource:
    """Look up a configured report source."""
    if source_name not in REPORT_SOURCES:
        raise ValueError(f"Unsupported report source: {source_name}")
    return REPORT_SOURCES[source_name]


async def write_source_report(
    source_name: str,
    output_dir: Optional[Path] = None,
    bbox_override: Optional[BoundingBox] = None,
    country_override: Optional[ResolvedCountry] = None,
) -> tuple[dict, Path]:
    """Generate and write a single source report file."""
    output_dir = get_reports_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    source = get_report_source(source_name)
    report = await build_source_report(
        source,
        bbox_override=bbox_override,
        country_override=country_override,
    )
    report_path = output_dir / source.output_filename
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report, report_path


async def generate_reports(
    output_dir: Optional[Path] = None,
    sources: Optional[Sequence[str]] = None,
    bbox_override: Optional[BoundingBox] = None,
    country_override: Optional[ResolvedCountry] = None,
) -> dict:
    """Generate JSON snapshot files for the configured sources."""
    output_dir = get_reports_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_sources = list(sources or REPORT_SOURCES.keys())
    reports = []

    for source_name in selected_sources:
        report, report_path = await write_source_report(
            source_name=source_name,
            output_dir=output_dir,
            bbox_override=bbox_override,
            country_override=country_override,
        )
        reports.append(
            {
                "source": source_name,
                "report_file": report["report_file"],
                "status": report["status"],
                "entity_count": report["entity_count"],
                "error_message": report["error_message"],
                "warning_message": report["warning_message"],
                "country": report["country"],
                "file": str(report_path),
                "bbox": report["bbox"],
            }
        )

    summary = {
        "generated_at": _utc_now_iso(),
        "output_dir": str(output_dir),
        "reports": reports,
    }
    get_index_report_path(output_dir).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
