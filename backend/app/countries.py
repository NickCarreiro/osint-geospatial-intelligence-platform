"""Resolve country names and codes to bounding boxes."""
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional

import httpx

from app.models import BoundingBox

COUNTRY_BOUNDARIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/"
    "ne_10m_admin_0_countries.geojson"
)
CACHE_PATH = Path(__file__).resolve().parents[2] / ".cache" / "countries" / "ne_10m_admin_0_countries.geojson"

COUNTRY_ALIASES = {
    "uk": "united kingdom",
    "great britain": "united kingdom",
    "britain": "united kingdom",
    "usa": "united states of america",
    "united states": "united states of america",
    "us": "united states of america",
    "uae": "united arab emirates",
    "dr congo": "democratic republic of the congo",
    "drc": "democratic republic of the congo",
    "congo kinshasa": "democratic republic of the congo",
    "congo brazzaville": "republic of the congo",
    "czech republic": "czechia",
    "swaziland": "eswatini",
    "macedonia": "north macedonia",
    "burma": "myanmar",
    "east timor": "timor leste",
    "cape verde": "cabo verde",
    "vatican city": "vatican",
}

EXACT_MATCH_FIELDS = (
    ("ISO_A2", 220),
    ("ISO_A3", 210),
    ("WB_A2", 205),
    ("WB_A3", 200),
    ("ADM0_A3", 195),
    ("ADM0_ISO", 190),
    ("POSTAL", 185),
    ("ADMIN", 180),
    ("NAME", 178),
    ("NAME_LONG", 176),
    ("BRK_NAME", 174),
    ("FORMAL_EN", 172),
    ("ABBREV", 168),
    ("SOVEREIGNT", 140),
)

FUZZY_MATCH_FIELDS = (
    ("ADMIN", 95),
    ("NAME", 94),
    ("NAME_LONG", 92),
    ("BRK_NAME", 90),
    ("FORMAL_EN", 88),
    ("ABBREV", 84),
    ("SOVEREIGNT", 60),
)

_country_features_cache: Optional[list[dict]] = None


class CountryResolutionError(ValueError):
    """Raised when a country query cannot be resolved."""


@dataclass(frozen=True)
class ResolvedCountry:
    """Resolved country metadata and its bounding box."""

    query: str
    name: str
    admin: str
    iso_a2: Optional[str]
    iso_a3: Optional[str]
    bbox: BoundingBox

    def model_dump(self) -> dict:
        """Convert the resolved country into JSON-serializable data."""
        return {
            "query": self.query,
            "name": self.name,
            "admin": self.admin,
            "iso_a2": self.iso_a2,
            "iso_a3": self.iso_a3,
            "bbox": self.bbox.model_dump(),
        }


def _normalize_country_name(value: str) -> str:
    """Normalize a country name or code for matching."""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.casefold().replace("&", " and ")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _apply_alias(query: str) -> str:
    """Expand common aliases to a canonical matching form."""
    normalized = _normalize_country_name(query)
    return COUNTRY_ALIASES.get(normalized, normalized)


def _iter_coordinates(coordinates) -> Iterator[tuple[float, float]]:
    """Yield lon/lat coordinate pairs from a nested GeoJSON geometry."""
    if not isinstance(coordinates, list):
        return
    if len(coordinates) >= 2 and all(isinstance(value, (int, float)) for value in coordinates[:2]):
        yield coordinates[0], coordinates[1]
        return
    for item in coordinates:
        yield from _iter_coordinates(item)


def _geometry_bbox(geometry: dict) -> BoundingBox:
    """Compute a bounding box from a GeoJSON geometry."""
    coords = list(_iter_coordinates(geometry.get("coordinates", [])))
    if not coords:
        raise CountryResolutionError("Country geometry did not contain any coordinates")

    min_lon = min(lon for lon, _ in coords)
    max_lon = max(lon for lon, _ in coords)
    min_lat = min(lat for _, lat in coords)
    max_lat = max(lat for _, lat in coords)
    return BoundingBox(lamin=min_lat, lomin=min_lon, lamax=max_lat, lomax=max_lon)


def _best_alpha2_code(properties: dict) -> Optional[str]:
    """Choose the best two-letter country code available in the dataset."""
    for key in ("ISO_A2", "WB_A2", "POSTAL"):
        value = properties.get(key)
        if isinstance(value, str) and len(value) == 2 and value.isalpha() and value != "-99":
            return value.upper()
    return None


def _best_alpha3_code(properties: dict) -> Optional[str]:
    """Choose the best three-letter country code available in the dataset."""
    for key in ("ISO_A3", "WB_A3", "ADM0_A3", "ADM0_ISO"):
        value = properties.get(key)
        if isinstance(value, str) and len(value) == 3 and value.isalpha() and value != "-99":
            return value.upper()
    return None


def _score_feature(query: str, properties: dict) -> int:
    """Score how well a feature matches a normalized query."""
    best_score = 0

    for field, score in EXACT_MATCH_FIELDS:
        value = properties.get(field)
        if not value:
            continue
        if _normalize_country_name(str(value)) == query:
            best_score = max(best_score, score)

    if best_score:
        return best_score

    for field, score in FUZZY_MATCH_FIELDS:
        value = properties.get(field)
        if not value:
            continue
        normalized_value = _normalize_country_name(str(value))
        if query in normalized_value or normalized_value in query:
            best_score = max(best_score, score)

    return best_score


async def _load_country_features() -> list[dict]:
    """Load and cache the Natural Earth country boundaries dataset."""
    global _country_features_cache

    if _country_features_cache is not None:
        return _country_features_cache

    if not CACHE_PATH.exists():
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(COUNTRY_BOUNDARIES_URL)
            response.raise_for_status()
            CACHE_PATH.write_text(response.text, encoding="utf-8")

    data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    _country_features_cache = data.get("features", [])
    return _country_features_cache


async def resolve_country(country_query: str) -> ResolvedCountry:
    """Resolve a country name or code into metadata and a bbox."""
    features = await _load_country_features()
    normalized_query = _apply_alias(country_query)

    best_feature = None
    best_score = 0
    for feature in features:
        score = _score_feature(normalized_query, feature.get("properties", {}))
        if score > best_score:
            best_feature = feature
            best_score = score

    if not best_feature:
        raise CountryResolutionError(f"Could not resolve country '{country_query}'")

    properties = best_feature.get("properties", {})
    return ResolvedCountry(
        query=country_query,
        name=properties.get("NAME") or properties.get("ADMIN") or country_query,
        admin=properties.get("ADMIN") or properties.get("NAME") or country_query,
        iso_a2=_best_alpha2_code(properties),
        iso_a3=_best_alpha3_code(properties),
        bbox=_geometry_bbox(best_feature.get("geometry", {})),
    )


async def list_countries() -> list[ResolvedCountry]:
    """Return all countries with defined boundaries and usable ISO alpha-2 codes."""
    features = await _load_country_features()
    countries: list[ResolvedCountry] = []
    seen_codes: set[str] = set()

    for feature in features:
        properties = feature.get("properties", {})
        iso_a2 = _best_alpha2_code(properties)
        if not iso_a2 or iso_a2 in seen_codes:
            continue

        try:
            bbox = _geometry_bbox(feature.get("geometry", {}))
        except CountryResolutionError:
            continue

        countries.append(
            ResolvedCountry(
                query=properties.get("NAME") or properties.get("ADMIN") or iso_a2,
                name=properties.get("NAME") or properties.get("ADMIN") or iso_a2,
                admin=properties.get("ADMIN") or properties.get("NAME") or iso_a2,
                iso_a2=iso_a2,
                iso_a3=_best_alpha3_code(properties),
                bbox=bbox,
            )
        )
        seen_codes.add(iso_a2)

    countries.sort(key=lambda country: (country.iso_a2 or "", country.name))
    return countries
