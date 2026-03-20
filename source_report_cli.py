#!/usr/bin/env python3
"""Shared CLI helpers for single-source report generators."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"


def ensure_project_python() -> None:
    """Re-exec inside the project virtualenv when available."""
    try:
        import pydantic  # noqa: F401
    except ModuleNotFoundError:
        for candidate in (REPO_ROOT / ".venv" / "bin" / "python", REPO_ROOT / "venv" / "bin" / "python"):
            if candidate.exists() and Path(sys.executable) != candidate:
                os.execv(str(candidate), [str(candidate), str(Path(sys.argv[0]).resolve()), *sys.argv[1:]])
        raise


def ensure_backend_path() -> None:
    """Add the backend package directory to sys.path."""
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))


def parse_args(description: str) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory where the source JSON report should be written; defaults to reports/",
    )
    parser.add_argument("--country", help="Country name or code to resolve into a report area")
    parser.add_argument("--lamin", type=float, help="Minimum latitude")
    parser.add_argument("--lomin", type=float, help="Minimum longitude")
    parser.add_argument("--lamax", type=float, help="Maximum latitude")
    parser.add_argument("--lomax", type=float, help="Maximum longitude")
    return parser.parse_args()


def parse_bbox(args: argparse.Namespace):
    """Build an optional bbox from CLI args."""
    values = [args.lamin, args.lomin, args.lamax, args.lomax]
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise SystemExit("Provide all of --lamin, --lomin, --lamax, and --lomax together.")

    from app.models import BoundingBox

    return BoundingBox(lamin=args.lamin, lomin=args.lomin, lamax=args.lamax, lomax=args.lomax)


async def run_source_report_cli(source_name: str, description: str) -> None:
    """Generate one source report and print a concise JSON summary."""
    ensure_project_python()
    ensure_backend_path()

    from app.countries import resolve_country
    from app.reporting import get_source_report_path, write_source_report

    args = parse_args(description)
    if args.country and any(value is not None for value in (args.lamin, args.lomin, args.lamax, args.lomax)):
        raise SystemExit("Use either --country or an explicit bbox, not both together.")

    bbox = parse_bbox(args)
    country = await resolve_country(args.country) if args.country else None
    report, report_path = await write_source_report(
        source_name=source_name,
        output_dir=Path(args.output_dir),
        bbox_override=bbox,
        country_override=country,
    )

    summary = {
        "source": report["source"],
        "report_file": report["report_file"],
        "status": report["status"],
        "entity_count": report["entity_count"],
        "error_message": report["error_message"],
        "warning_message": report["warning_message"],
        "country": report["country"],
        "bbox": report["bbox"],
        "source_url": report["source_url"],
        "default_file": str(get_source_report_path(source_name)),
        "file": str(report_path),
    }
    print(json.dumps(summary, indent=2))

    if report["status"] == "error":
        raise SystemExit(1)


def main(source_name: str, description: str) -> None:
    """Run the async CLI wrapper."""
    asyncio.run(run_source_report_cli(source_name, description))
