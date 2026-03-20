"""Shared helpers for Overpass-backed adapters."""
import json
from typing import Optional

import httpx

from app.adapters.base import AdapterError

DEFAULT_OVERPASS_URLS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

OVERPASS_CLIENT_HEADERS = {
    "User-Agent": "sit_mon/1.0 (+backend report generator)",
    "Accept": "application/json, text/plain;q=0.9, */*;q=0.8",
}

OVERPASS_FORM_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
}


def build_overpass_urls(preferred_url: Optional[str] = None) -> list[str]:
    """Build a de-duplicated, ordered list of Overpass endpoints."""
    urls = []
    for url in (preferred_url, *DEFAULT_OVERPASS_URLS):
        if url and url not in urls:
            urls.append(url)
    return urls


def create_overpass_client(timeout_s: float = 25.0) -> httpx.AsyncClient:
    """Create a shared HTTP client configured for Overpass requests."""
    return httpx.AsyncClient(
        timeout=timeout_s,
        follow_redirects=True,
        headers=OVERPASS_CLIENT_HEADERS,
    )


def parse_overpass_payload(response: httpx.Response, url: str) -> dict:
    """Validate and parse an Overpass JSON response."""
    response.raise_for_status()

    body = response.text.strip()
    if not body:
        raise AdapterError(f"Overpass upstream returned an empty response from {url}")

    try:
        payload = response.json()
    except json.JSONDecodeError as exc:
        preview = body[:200].replace("\n", " ")
        raise AdapterError(f"Overpass upstream returned non-JSON from {url}: {preview}") from exc

    if not isinstance(payload, dict):
        raise AdapterError(f"Overpass upstream returned an unexpected payload type from {url}")

    if "elements" not in payload:
        raise AdapterError(f"Overpass upstream payload from {url} did not include 'elements'")

    return payload
