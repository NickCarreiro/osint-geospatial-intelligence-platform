# Unified OSINT Geospatial Intelligence Platform - Implementation Plan

## Project Overview

Build a high-volume geospatial OSINT fusion platform that aggregates multiple public intelligence feeds into a single operational map for situational awareness.

## Technology Stack

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **Cache**: Redis
- **WebSocket**: websockets library
- **HTTP Client**: httpx
- **Orbital Propagation**: skyfield or pyorbital

### Frontend
- **Map Library**: MapLibre GL JS
- **Clustering**: maplibre-gl-leaflet (or custom clustering)
- **Build Tool**: Vite (for modern bundling)

### Deployment
- No Docker (direct deployment)
- Environment-based configuration
- Systemd services for production

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Layer 4: Frontend                         │
│                    MapLibre Dashboard (HTML/JS)                  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Layer 3: Fusion API (FastAPI)                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  GET /api/unified                                        │   │
│  │  - Bounding box filtering                               │   │
│  │  - Time window filtering                                 │   │
│  │  - Entity type filtering                                 │   │
│  │  - Concurrent fetching from all adapters                │   │
│  │  - Cache layer (Redis)                                   │   │
│  │  - Graceful degradation                                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  GET /health                                             │   │
│  │  - Source health status                                  │   │
│  │  - Metrics (latency, counts, cache hits, failures)       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Layer 2: Normalization Layer                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Common GeoJSON Schema                                   │   │
│  │  - geometry: Point [lon, lat]                            │   │
│  │  - properties: source, entity_type, timestamp,           │   │
│  │               identifier, metadata                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Entity Types: aircraft, vessel, thermal_event, satellite│   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Layer 1: Ingestion Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  OpenSky     │  │  AISStream   │  │   FIRMS      │          │
│  │  REST Poll   │  │  WebSocket   │  │  REST Poll   │          │
│  │  + OAuth     │  │  Streaming   │  │  + API Key   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  CelesTrak TLE                                           │   │
│  │  - Catalog refresh                                       │   │
│  │  - Orbital propagation                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
sit_mon/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI application entry point
│   │   ├── config.py               # Configuration from environment
│   │   ├── models.py               # Pydantic models
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── unified.py          # /api/unified endpoint
│   │   │   └── health.py           # /health endpoint
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base adapter with retry/backoff
│   │   │   ├── opensky.py          # OpenSky adapter
│   │   │   ├── aisstream.py        # AISStream adapter
│   │   │   ├── firms.py            # FIRMS adapter
│   │   │   └── celestrak.py        # CelesTrak TLE adapter
│   │   ├── normalizers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base normalizer
│   │   │   ├── aircraft.py         # Aircraft normalizer
│   │   │   ├── vessel.py           # Vessel normalizer
│   │   │   ├── thermal.py          # Thermal event normalizer
│   │   │   └── satellite.py        # Satellite normalizer
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   └── redis_client.py     # Redis cache wrapper
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── geo.py              # GeoJSON utilities
│   │       └── metrics.py          # Metrics tracking
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── index.html
│   ├── src/
│   │   ├── main.js                 # MapLibre initialization
│   │   ├── layers/
│   │   │   ├── aircraft.js
│   │   │   ├── vessel.js
│   │   │   ├── thermal.js
│   │   │   └── satellite.js
│   │   ├── clustering.js           # Entity clustering
│   │   └── api.js                  # API client
│   ├── package.json
│   └── vite.config.js
├── .env                            # Environment configuration
├── start.sh                        # Startup script
└── README.md
```

---

## Implementation Phases

### Phase 1: Core Data Flow (MVP)

**Goal**: Working end-to-end pipeline with aircraft and vessel data.

1. **Project Setup**
   - Create directory structure
   - Set up Python virtual environment
   - Install backend dependencies
   - Set up frontend with Vite + MapLibre

2. **Base Infrastructure**
   - Configuration module (load from .env)
   - Base adapter class with retry/backoff logic
   - Base normalizer class
   - Redis cache wrapper
   - Metrics tracking utilities

3. **OpenSky Adapter**
   - OAuth authentication
   - REST polling implementation
   - State vector parsing
   - Error handling and timeouts

4. **AISStream Adapter**
   - WebSocket connection
   - Message type filtering
   - Bounding box filtering
   - Position report parsing

5. **Normalization Layer**
   - Aircraft normalizer (OpenSky → GeoJSON)
   - Vessel normalizer (AISStream → GeoJSON)
   - Common GeoJSON schema definition

6. **Fusion API**
   - `/api/unified` endpoint
   - Bounding box filtering
   - Concurrent fetching from adapters
   - Basic caching

7. **Map Dashboard**
   - MapLibre initialization
   - Aircraft layer
   - Vessel layer
   - Layer toggles
   - Viewport-based refresh

---

### Phase 2: Secondary Sources

**Goal**: Multi-domain intelligence view with thermal and satellite data.

1. **FIRMS Adapter**
   - REST polling with API key
   - Geographic bounding box queries
   - Thermal anomaly parsing
   - Rate limit handling (5000/10min)

2. **CelesTrak TLE Adapter**
   - TLE catalog download
   - Orbital propagation (using skyfield)
   - Real-time coordinate computation
   - Periodic refresh (6 hours)

3. **Additional Normalizers**
   - Thermal event normalizer
   - Satellite normalizer

4. **Map Dashboard Updates**
   - Thermal event layer
   - Satellite layer
   - Entity icons (✈️, 🚢, 🔥, 🛰️)

---

### Phase 3: Performance & Reliability

**Goal**: Stable high-volume operation.

1. **Advanced Caching**
   - Per-source TTL configuration
   - Cache hit rate tracking
   - Cache warming strategies

2. **Clustering**
   - Client-side clustering for high entity counts
   - Zoom-based clustering
   - Entity cap limits

3. **Rate Limiting**
   - Per-source rate limits
   - 429 cooldown handling
   - Backoff strategies

4. **Entity Pruning**
   - TTL expiration per entity type
   - Motion history tracking
   - Stale entity removal

5. **Observability**
   - Enhanced `/health` endpoint
   - Source health status
   - Detailed metrics (latency, counts, failures)

---

## Data Schema

### Common GeoJSON Format

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

### Entity Type Metadata

**Aircraft**
- icao24
- callsign
- altitude
- heading
- velocity
- on_ground

**Vessel**
- mmsi
- name
- speed
- course
- ship_type

**Thermal Event**
- confidence
- fire_radiative_power
- satellite_source

**Satellite**
- norad_id
- name
- altitude
- inclination

---

## Configuration

### Environment Variables

From `imported_env`:

```bash
# OpenSky
OPENSKY_CLIENT_ID=your_opensky_client_id
OPENSKY_CLIENT_SECRET=your_opensky_client_secret
OPENSKY_MAX_AIRCRAFT=12000
OPENSKY_CACHE_TTL_S=60
OPENSKY_429_COOLDOWN_S=180
OPENSKY_LAMIN=-85.0
OPENSKY_LOMIN=-180.0
OPENSKY_LAMAX=85.0
OPENSKY_LOMAX=180.0

# AISStream
AISSTREAM_API_KEY=your_aisstream_api_key
AISSTREAM_WS_URL=wss://stream.aisstream.io/v0/stream
AISSTREAM_LAMIN=-90.0
AISSTREAM_LOMIN=-180.0
AISSTREAM_LAMAX=90.0
AISSTREAM_LOMAX=180.0
AISSTREAM_FILTER_MESSAGE_TYPES=PositionReport,StandardClassBPositionReport,ExtendedClassBPositionReport,LongRangeAisBroadcastMessage,ShipStaticData,StaticDataReport
AISSTREAM_SAMPLE_S=4.0
AISSTREAM_MAX_MESSAGES=10000
AISSTREAM_STALE_S=900
AISSTREAM_TIMEOUT_S=45.0
AISSTREAM_FORCE_IPV4=true

# FIRMS
FIRMS_API_KEY=your_firms_api_key
FIRMS_CACHE_TTL_S=3600
FIRMS_RATE_LIMIT=5000
FIRMS_RATE_WINDOW=600

# CelesTrak
SATELLITE_TLE_URL=https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle
SATELLITE_MAX_ENTITIES=20000
SATELLITE_CACHE_TTL_S=60
SATELLITE_CATALOG_REFRESH_S=21600
SATELLITE_TIMEOUT_S=20.0

# General
CORS_ORIGINS=*
REDIS_URL=redis://localhost:6379/0
API_HOST=0.0.0.0
API_PORT=8002
```

---

## Performance Targets

| Metric | Goal |
|--------|------|
| API latency | <500ms |
| Map refresh | <1s |
| Ingestion update | <60s |
| WebSocket lag | <5s |

---

## Data Freshness Rules

| Entity | TTL |
|--------|-----|
| Aircraft | 120s |
| Vessels | 900s |
| Satellites | 300s |
| Thermal events | 24h |

---

## Failure Handling

If a source fails:
1. Mark source as degraded
2. Log error with details
3. Continue serving remaining data
4. Retry with exponential backoff
5. Never crash the fusion service

---

## Security Rules

**Do:**
- Store credentials in environment variables
- Implement source timeouts
- Sanitize all API responses
- Validate all incoming parameters

**Do NOT:**
- Hardcode credentials in code
- Expose raw source APIs to frontend
- Trust external feeds blindly
- Allow unrestricted CORS in production
- Allow infinite entity rendering

---

## Definition of Done

The system is complete when:
- Multiple OSINT feeds appear on a single map
- The map updates in near real-time
- Each entity includes source attribution
- The API returns normalized GeoJSON
- All four data sources are integrated
- Health endpoint provides source status
- System handles source failures gracefully

---

## Next Steps

Once this plan is approved, switch to Code mode to begin implementation starting with Phase 1: Core Data Flow.
