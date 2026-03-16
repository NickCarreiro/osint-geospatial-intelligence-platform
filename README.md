# OSINT Geospatial Intelligence Platform

A high-volume geospatial OSINT fusion platform that aggregates multiple public intelligence feeds into a single operational map for situational awareness.

## Features

- **Multi-source data aggregation**: Aircraft, vessels, thermal events, and satellites
- **Real-time visualization**: Interactive MapLibre dashboard with live updates
- **Unified API**: Single endpoint returning normalized GeoJSON
- **Graceful degradation**: System continues operating even when sources fail
- **Caching**: Redis-based caching with per-entity TTL
- **Health monitoring**: Built-in health checks and metrics

## Data Sources

| Source | Type | Data |
|--------|------|-------|
| OpenSky Network | REST + OAuth | Aircraft state vectors, altitude, heading, velocity |
| AISStream | WebSocket | Vessel position reports, MMSI, speed, course |
| NASA FIRMS | REST | Thermal anomalies, fire radiative power, confidence |
| CelesTrak TLE | REST + Propagation | Satellite orbital elements, real-time positions |

## Technology Stack

### Backend
- Python 3.11+
- FastAPI
- Redis (caching)
- httpx (HTTP client)
- websockets (WebSocket client)
- skyfield (orbital propagation)

### Frontend
- MapLibre GL JS
- Vanilla JavaScript

## Quick Start

### Prerequisites

- Python 3.11+ (Python 3.13+ requires Rust toolchain for pydantic-core)
- Redis server
- API credentials (see `.env` file)

### Installation

1. Clone the repository:
```bash
cd /home/admin/access/homelab/sit_mon
```

2. Run the startup script:
```bash
./start.sh
```

The script will:
- Create a Python virtual environment
- Install dependencies
- Start Redis (if not running)
- Launch the application

### Python 3.13+ Note

If you're using Python 3.13 or newer, you may need to install Rust first:

```bash
# On Ubuntu/Debian
sudo apt-get install rustc cargo

# Then run the startup script
./start.sh
```

### Access

- **Frontend**: http://localhost:8002/
- **API Documentation**: http://localhost:8002/docs
- **Health Check**: http://localhost:8002/health
- **Unified API**: http://localhost:8002/api/unified

## Configuration

Configuration is managed through environment variables in the `.env` file.

### Key Settings

```bash
# API
API_HOST=0.0.0.0
API_PORT=8002

# Redis
REDIS_URL=redis://localhost:6379/0

# OpenSky
OPENSKY_CLIENT_ID=your_client_id
OPENSKY_CLIENT_SECRET=your_client_secret

# AISStream
AISSTREAM_API_KEY=your_api_key

# FIRMS
FIRMS_API_KEY=your_api_key
```

## API Endpoints

### GET /api/unified

Fetch unified OSINT data from all sources.

**Query Parameters:**
- `lamin`, `lomin`, `lamax`, `lomax`: Bounding box
- `start_time`, `end_time`: Time window (ISO 8601)
- `entity_types`: Comma-separated entity types (aircraft, vessel, thermal_event, satellite)
- `sources`: Comma-separated sources (opensky, aisstream, firms, celestrak)
- `use_cache`: Use cache if available (default: true)

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [lon, lat]
      },
      "properties": {
        "source": "opensky",
        "entity_type": "aircraft",
        "timestamp": "2024-01-01T00:00:00",
        "identifier": "abc123",
        "metadata": { ... }
      }
    }
  ],
  "metadata": {
    "count": 1000,
    "latency_ms": 250.5,
    "timestamp": "2024-01-01T00:00:00",
    "sources": { ... },
    "entity_types": { ... }
  }
}
```

### GET /health

Get system health status.

**Response:**
```json
{
  "status": "healthy",
  "sources": [
    {
      "source": "opensky",
      "healthy": true,
      "last_update": "2024-01-01T00:00:00",
      "entity_count": 5000,
      "latency_ms": 200.5
    }
  ],
  "metrics": { ... }
}
```

## Data Schema

All entities are returned in a common GeoJSON format:

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [longitude, latitude]
  },
  "properties": {
    "source": "opensky|aisstream|firms|celestrak",
    "entity_type": "aircraft|vessel|thermal_event|satellite",
    "timestamp": "ISO 8601 UTC",
    "identifier": "unique_id",
    "metadata": {
      // Source-specific fields
    }
  }
}
```

## Entity Types

### Aircraft
- icao24
- callsign
- altitude
- heading
- velocity
- on_ground

### Vessel
- mmsi
- name
- speed
- course
- ship_type

### Thermal Event
- confidence
- fire_radiative_power
- satellite_source

### Satellite
- norad_id
- name
- altitude
- inclination

## Performance Targets

| Metric | Goal |
|--------|------|
| API latency | <500ms |
| Map refresh | <1s |
| Ingestion update | <60s |
| WebSocket lag | <5s |

## Data Freshness

| Entity | TTL |
|--------|-----|
| Aircraft | 120s |
| Vessels | 900s |
| Satellites | 300s |
| Thermal events | 24h |

## Project Structure

```
sit_mon/
├── backend/
│   ├── app/
│   │   ├── adapters/          # Data source adapters
│   │   ├── api/               # API endpoints
│   │   ├── cache/             # Redis cache wrapper
│   │   ├── config.py          # Configuration
│   │   ├── main.py            # FastAPI app
│   │   └── models.py          # Pydantic models
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   └── src/
│       └── main.js            # MapLibre dashboard
├── .env                       # Environment configuration
├── start.sh                   # Startup script
└── README.md
```

## Security

- Credentials stored in environment variables
- Source timeouts implemented
- API responses sanitized
- Input parameters validated
- No hardcoded credentials

## License

This project is for educational and research purposes only.

## Disclaimer

This platform is purely a data aggregation and visualization tool. It does not perform intelligence analysis, classify military activity, make predictions about conflict, or infer intent of entities.