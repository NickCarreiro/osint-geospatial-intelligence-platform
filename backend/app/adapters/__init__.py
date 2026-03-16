"""Data source adapters for the OSINT platform."""
from app.adapters.base import BaseAdapter, AdapterError, RateLimitError
from app.adapters.opensky import OpenSkyAdapter
from app.adapters.aisstream import AISStreamAdapter
from app.adapters.firms import FIRMSAdapter
from app.adapters.celestrak import CelesTrakAdapter

__all__ = [
    "BaseAdapter",
    "AdapterError",
    "RateLimitError",
    "OpenSkyAdapter",
    "AISStreamAdapter",
    "FIRMSAdapter",
    "CelesTrakAdapter",
]