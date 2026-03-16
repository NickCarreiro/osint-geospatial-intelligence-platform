"""Configuration module for the OSINT platform."""
from typing import List
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8002, description="API port")
    cors_origins: str = Field(default="*", description="CORS origins")

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")

    # OpenSky Configuration
    opensky_states_url: str = Field(default="https://opensky-network.org/api/states/all", description="OpenSky states API URL")
    opensky_token_url: str = Field(default="https://opensky-network.org/api/token", description="OpenSky OAuth token URL")
    opensky_client_id: str = Field(default="", description="OpenSky OAuth client ID")
    opensky_client_secret: str = Field(default="", description="OpenSky OAuth client secret")
    opensky_max_aircraft: int = Field(default=12000, description="Max aircraft to fetch")
    opensky_cache_ttl_s: int = Field(default=60, description="Cache TTL in seconds")
    opensky_429_cooldown_s: int = Field(default=180, description="429 cooldown in seconds")
    opensky_lamin: float = Field(default=-85.0, description="Latitude min")
    opensky_lomin: float = Field(default=-180.0, description="Longitude min")
    opensky_lamax: float = Field(default=85.0, description="Latitude max")
    opensky_lomax: float = Field(default=180.0, description="Longitude max")
    opensky_auto_tile_when_capped: bool = Field(default=True, description="Auto tile when capped")
    opensky_cap_threshold: int = Field(default=256, description="Cap threshold")
    opensky_tile_rows: int = Field(default=7, description="Tile rows")
    opensky_tile_cols: int = Field(default=7, description="Tile cols")

    # AISStream Configuration
    aisstream_api_key: str = Field(default="", description="AISStream API key")
    aisstream_ws_url: str = Field(
        default="wss://stream.aisstream.io/v0/stream",
        description="AISStream WebSocket URL"
    )
    aisstream_lamin: float = Field(default=-90.0, description="Latitude min")
    aisstream_lomin: float = Field(default=-180.0, description="Longitude min")
    aisstream_lamax: float = Field(default=90.0, description="Latitude max")
    aisstream_lomax: float = Field(default=180.0, description="Longitude max")
    aisstream_filter_message_types: str = Field(
        default="PositionReport,StandardClassBPositionReport,ExtendedClassBPositionReport,LongRangeAisBroadcastMessage,ShipStaticData,StaticDataReport",
        description="Message types to filter"
    )
    aisstream_sample_s: float = Field(default=4.0, description="Sample rate in seconds")
    aisstream_max_messages: int = Field(default=10000, description="Max messages")
    aisstream_stale_s: int = Field(default=900, description="Stale threshold in seconds")
    aisstream_timeout_s: float = Field(default=45.0, description="Timeout in seconds")
    aisstream_force_ipv4: bool = Field(default=True, description="Force IPv4")

    # FIRMS Configuration
    firms_api_key: str = Field(default="", description="FIRMS API key")
    firms_cache_ttl_s: int = Field(default=3600, description="Cache TTL in seconds")
    firms_rate_limit: int = Field(default=5000, description="Rate limit")
    firms_rate_window: int = Field(default=600, description="Rate window in seconds")

    # Satellite Configuration
    satellite_tle_url: str = Field(
        default="https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle",
        description="TLE URL"
    )
    satellite_max_entities: int = Field(default=20000, description="Max satellites")
    satellite_cache_ttl_s: int = Field(default=60, description="Cache TTL in seconds")
    satellite_catalog_refresh_s: int = Field(default=21600, description="Catalog refresh in seconds")
    satellite_timeout_s: float = Field(default=20.0, description="Timeout in seconds")

    # Space-Track Configuration (alternative to CelesTrak)
    spacetrack_username: str = Field(default="", description="Space-Track username")
    spacetrack_password: str = Field(default="", description="Space-Track password")
    spacetrack_base_url: str = Field(default="https://www.space-track.org", description="Space-Track base URL")
    spacetrack_login_url: str = Field(default="https://www.space-track.org/ajaxauth/login", description="Space-Track login URL")
    spacetrack_tle_url: str = Field(
        default="https://www.space-track.org/basicspacedata/query/class/tle_latest/ORDINAL/1/limit/20000/format/tle",
        description="Space-Track TLE URL"
    )
    spacetrack_tle_url_alt: str = Field(
        default="https://www.space-track.org/basicspacedata/query/class/tle/ORDINAL/1/limit/20000/format/tle",
        description="Space-Track TLE URL (alternative)"
    )

    # Motion Configuration
    motion_projection_s: int = Field(default=60, description="Motion projection in seconds")
    motion_history_ttl_s: int = Field(default=900, description="Motion history TTL in seconds")
    motion_tracker_max_entities: int = Field(default=200000, description="Max tracked entities")

    # Entity TTL Configuration
    aircraft_ttl_s: int = Field(default=120, description="Aircraft TTL in seconds")
    vessel_ttl_s: int = Field(default=900, description="Vessel TTL in seconds")
    satellite_ttl_s: int = Field(default=300, description="Satellite TTL in seconds")
    thermal_ttl_s: int = Field(default=86400, description="Thermal event TTL in seconds")

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def aisstream_message_types(self) -> List[str]:
        """Parse AISStream message types into a list."""
        return [mt.strip() for mt in self.aisstream_filter_message_types.split(",")]

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Global settings instance
settings = Settings()