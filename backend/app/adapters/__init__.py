"""Data source adapters for the OSINT platform."""
from app.adapters.base import BaseAdapter, AdapterError, RateLimitError
from app.adapters.opensky import OpenSkyAdapter
from app.adapters.aisstream import AISStreamAdapter
from app.adapters.firms import FIRMSAdapter
from app.adapters.celestrak import CelesTrakAdapter
from app.adapters.radio import RadioAdapter
from app.adapters.oil_rig import OilRigAdapter
from app.adapters.power_grid import PowerGridAdapter
from app.adapters.fir import FIRAdapter
from app.adapters.maritime import MaritimeAdapter

__all__ = [
    "BaseAdapter",
    "AdapterError",
    "RateLimitError",
    "OpenSkyAdapter",
    "AISStreamAdapter",
    "FIRMSAdapter",
    "CelesTrakAdapter",
    "RadioAdapter",
    "OilRigAdapter",
    "PowerGridAdapter",
    "FIRAdapter",
    "MaritimeAdapter",
]
