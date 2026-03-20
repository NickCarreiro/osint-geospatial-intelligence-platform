#!/usr/bin/env python3
"""Generate backend JSON report files for selected sources."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def ensure_project_python() -> None:
    """Re-exec inside the project virtualenv when available."""
    try:
        import pydantic  # noqa: F401
    except ModuleNotFoundError:
        for candidate in (REPO_ROOT / ".venv" / "bin" / "python", REPO_ROOT / "venv" / "bin" / "python"):
            if candidate.exists() and Path(sys.executable) != candidate:
                os.execv(str(candidate), [str(candidate), str(Path(__file__).resolve()), *sys.argv[1:]])
        raise


ensure_project_python()

from app.countries import resolve_country  # noqa: E402
from app.models import BoundingBox  # noqa: E402
from app.reporting import REPORT_SOURCES, generate_reports  # noqa: E402


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sources",
        default=",".join(REPORT_SOURCES.keys()),
        help="Comma-separated sources to snapshot into their stable JSON files",
    )
    parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory where per-source JSON files should be written; defaults to reports/",
    )
    parser.add_argument("--country", help="Country name or code to resolve into a report area")
    parser.add_argument("--lamin", type=float, help="Minimum latitude")
    parser.add_argument("--lomin", type=float, help="Minimum longitude")
    parser.add_argument("--lamax", type=float, help="Maximum latitude")
    parser.add_argument("--lomax", type=float, help="Maximum longitude")
    return parser.parse_args()


def parse_bbox(args: argparse.Namespace) -> BoundingBox | None:
    """Build an optional bbox from CLI args."""
    values = [args.lamin, args.lomin, args.lamax, args.lomax]
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise SystemExit("Provide all of --lamin, --lomin, --lamax, and --lomax together.")
    return BoundingBox(lamin=args.lamin, lomin=args.lomin, lamax=args.lamax, lomax=args.lomax)


async def main() -> None:
    """Run the report generator."""
    args = parse_args()
    if args.country and any(value is not None for value in (args.lamin, args.lomin, args.lamax, args.lomax)):
        raise SystemExit("Use either --country or an explicit bbox, not both together.")

    bbox = parse_bbox(args)
    country = await resolve_country(args.country) if args.country else None
    sources = [source.strip() for source in args.sources.split(",") if source.strip()]
    summary = await generate_reports(
        output_dir=Path(args.output_dir),
        sources=sources,
        bbox_override=bbox,
        country_override=country,
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
