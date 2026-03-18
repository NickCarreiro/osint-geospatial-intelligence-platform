"""Data models for the OSINT platform."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class EntityType(str, Enum):
    """Entity types supported by the platform."""
    AIRCRAFT = "aircraft"
    VESSEL = "vessel"
    THERMAL_EVENT = "thermal_event"
    SATELLITE = "satellite"
    RADIO_STATION = "radio_station"
    OIL_RIG = "oil_rig"
    POWER_GRID = "power_grid"
    POWER_SUBSTATION = "power_substation"
    FIR = "fir"
    MARITIME_BOUNDARY = "maritime_boundary"


class DataSource(str, Enum):
    """Data sources supported by the platform."""
    OPENSKY = "opensky"
    AISSTREAM = "aisstream"
    FIRMS = "firms"
    CELESTRAK = "celestrak"
    RADIO_API = "radio_api"
    OIL_RIG_API = "oil_rig_api"
    POWER_GRID_API = "power_grid_api"
    FIR_API = "fir_api"
    MARITIME_API = "maritime_api"


class GeoJSONFeature(BaseModel):
    """Standard GeoJSON Feature model."""
    type: str = Field(default="Feature", description="GeoJSON type")
    geometry: Dict[str, Any] = Field(description="Geometry object")
    properties: Dict[str, Any] = Field(description="Feature properties")

    @classmethod
    def create_point(
        cls,
        lon: float,
        lat: float,
        source: DataSource,
        entity_type: EntityType,
        identifier: str,
        timestamp: datetime,
        metadata: Dict[str, Any],
    ) -> "GeoJSONFeature":
        """Create a point feature."""
        return cls(
            geometry={
                "type": "Point",
                "coordinates": [lon, lat],
            },
            properties={
                "source": source.value,
                "entity_type": entity_type.value,
                "timestamp": timestamp.isoformat(),
                "identifier": identifier,
                "metadata": metadata,
            },
        )


class BoundingBox(BaseModel):
    """Bounding box for filtering."""
    lamin: float = Field(description="Minimum latitude")
    lomin: float = Field(description="Minimum longitude")
    lamax: float = Field(description="Maximum latitude")
    lomax: float = Field(description="Maximum longitude")

    def contains(self, lon: float, lat: float) -> bool:
        """Check if a point is within the bounding box."""
        return (
            self.lamin <= lat <= self.lamax
            and self.lomin <= lon <= self.lomax
        )


class TimeWindow(BaseModel):
    """Time window for filtering."""
    start: Optional[datetime] = Field(default=None, description="Start time")
    end: Optional[datetime] = Field(default=None, description="End time")

    def contains(self, timestamp: datetime) -> bool:
        """Check if a timestamp is within the time window."""
        if self.start and timestamp < self.start:
            return False
        if self.end and timestamp > self.end:
            return False
        return True


class UnifiedQuery(BaseModel):
    """Query parameters for the unified API."""
    bbox: Optional[BoundingBox] = Field(default=None, description="Bounding box filter")
    time_window: Optional[TimeWindow] = Field(default=None, description="Time window filter")
    entity_types: Optional[List[EntityType]] = Field(default=None, description="Entity type filter")
    sources: Optional[List[DataSource]] = Field(default=None, description="Source filter")


class SourceStatus(BaseModel):
    """Status of a data source."""
    source: DataSource
    healthy: bool
    last_update: Optional[datetime] = None
    error_message: Optional[str] = None
    entity_count: int = 0
    latency_ms: Optional[float] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(description="Overall status")
    sources: List[SourceStatus] = Field(description="Source statuses")
    metrics: Dict[str, Any] = Field(description="System metrics")


class Metrics(BaseModel):
    """System metrics."""
    ingestion_latency_ms: Dict[str, float] = Field(default_factory=dict)
    entity_counts: Dict[str, int] = Field(default_factory=dict)
    cache_hit_rates: Dict[str, float] = Field(default_factory=dict)
    source_failures: Dict[str, int] = Field(default_factory=dict)
    total_requests: int = 0
    total_errors: int = 0