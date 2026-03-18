
# AI Builder Instruction Sheet
## Project: Unified OSINT Geospatial Intelligence Platform

---

# Mission

Build a **high-volume geospatial OSINT fusion platform** that aggregates multiple public intelligence feeds into a single operational map.

The system must:

- Ingest **aircraft, vessel, thermal anomaly, and satellite position data**
- Normalize data into a **single geospatial schema**
- Serve results through a **single unified API**
- Render results on a **real-time map dashboard**

Primary goal: **situational awareness from multiple public intelligence streams**.

---

# Sources to Integrate

The platform must support these feeds.

## Aircraft
**Source:** OpenSky Network

**Data type**
- aircraft state vectors
- altitude
- heading
- velocity
- ICAO24 identifier

**Integration method**
- OAuth authentication
- API polling
- optional global tiling

---

## Vessels
**Source:** AISStream WebSocket

**Data type**
- vessel position reports
- MMSI identifier
- speed
- course
- vessel static data

**Integration method**
- WebSocket streaming
- bounding box filtering
- message type filtering

---

## Thermal / Fire Detection
**Source:** NASA FIRMS

**Data type**
- thermal anomaly
- fire radiative power
- detection confidence

**Integration method**
- periodic REST polling
- geographic bounding box queries

---

## Satellite Tracking
**Source:** CelesTrak TLE

**Data type**
- satellite orbital elements

**Integration method**
- periodic TLE catalog download
- propagate orbital positions locally
- compute real-time geospatial coordinates

---

# System Architecture

The builder should implement a **four-layer architecture**.

Sources → Ingestion Layer → Normalization Layer → Fusion API → Map Frontend

---

# Layer 1 — Ingestion

Goal: collect raw OSINT data.

Required ingestion modes:

| Source | Mode |
|------|------|
| OpenSky | REST polling |
| AISStream | WebSocket streaming |
| FIRMS | periodic REST polling |
| TLE | catalog refresh |

Key principles:

- isolate each source in **separate adapters**
- implement **timeouts**
- implement **retry logic**
- implement **rate limit backoff**

---

# Layer 2 — Normalization

All data must convert into a **common geospatial format**.

Standard format:

GeoJSON Feature

Each feature must include:

geometry:
  type: Point
  coordinates: [lon, lat]

properties:
  source
  entity_type
  timestamp
  identifier
  metadata

Entity types:

- aircraft
- vessel
- thermal_event
- satellite

Do **not expose vendor-specific schemas** to the frontend.

---

# Layer 3 — Data Fusion API

Expose a **single API endpoint** that returns normalized GeoJSON.

Example endpoint:

GET /api/unified

Parameters:

- bounding box
- time window
- entity filters

Requirements:

- concurrent fetching from all adapters
- cache layer
- graceful degradation when sources fail
- error reporting per source

---

# Layer 4 — Map Dashboard

Recommended libraries:

- Leaflet
- MapLibre

Map requirements:

- multiple layer groups
- clustering
- layer toggles
- refresh on viewport movement

Suggested icons:

| Entity | Icon |
|------|------|
| aircraft | ✈️ |
| vessel | 🚢 |
| thermal event | 🔥 |
| satellite | 🛰️ |

---

# Priority Build Order

### Phase 1 — Core Data Flow

1. OpenSky ingestion
2. AISStream ingestion
3. normalization layer
4. unified API
5. basic map

Goal: working end‑to‑end pipeline.

---

### Phase 2 — Secondary Sources

Add:

- FIRMS thermal feed
- satellite propagation

Goal: multi-domain intelligence view.

---

### Phase 3 — Performance Scaling

Add:

- caching
- clustering
- rate limiting
- entity pruning

Goal: stable high‑volume operation.

---

# Data Volume Considerations

Expected approximate volumes:

| Source | Typical Count |
|------|------|
| aircraft | ~12k |
| vessels | 10k–30k |
| satellites | ~20k |
| thermal events | hundreds |

Mitigation strategies:

- viewport filtering
- clustering
- entity cap limits
- TTL expiration

---

# Security Rules

## Do

- store credentials in environment variables
- rotate secrets regularly
- implement source timeouts
- sanitize all API responses
- validate all incoming parameters

## Do NOT

- hardcode credentials in code
- expose raw source APIs to the frontend
- trust external feeds blindly
- allow unrestricted CORS in production
- allow infinite entity rendering

---

# Reliability Rules

Each source adapter must support:

- timeout
- retry
- backoff
- cache TTL
- failure isolation

The system must **never fail completely because one source is down**.

---

# Observability Requirements

Expose:

Health endpoint:

/health

Metrics should track:

- ingestion latency
- entity counts
- cache hit rates
- source failures

---

# Performance Targets

| Metric | Goal |
|------|------|
| API latency | <500ms |
| map refresh | <1s |
| ingestion update | <60s |
| WebSocket lag | <5s |

---

# Scaling Strategy

When entity counts exceed limits apply:

- clustering
- sampling
- entity expiration
- zoom‑based filtering

Never render the full global dataset directly in the browser.

---

# Data Freshness Rules

| Entity | TTL |
|------|------|
| aircraft | 120s |
| vessels | 900s |
| satellites | 300s |
| thermal events | 24h |

---

# Failure Handling

If a source fails:

1. mark source degraded
2. log error
3. continue serving remaining data
4. retry later

Never crash the fusion service.

---

# Deliverables

### Infrastructure

- containerized services
- environment configuration
- deployment scripts

### Backend

- ingestion adapters
- normalization layer
- unified API

### Frontend

- interactive map
- entity layers
- refresh logic

---

# Non‑Goals

The platform must **NOT attempt to**:

- perform intelligence analysis
- classify military activity
- make predictions about conflict
- infer intent of entities

It is purely a **data aggregation and visualization platform**.

---

# Definition of Done

The system is complete when:

- multiple OSINT feeds appear on a **single map**
- the map updates in **near real‑time**
- each entity includes **source attribution**
- the API returns **normalized GeoJSON**.

---

# Suggested Technology Stack

Backend:
- Python
- FastAPI
- Redis

Frontend:
- Leaflet or MapLibre

Deployment:
- Docker
