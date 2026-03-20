# Sit Mon New Features Implementation Plan

## Overview
This document outlines the implementation plan for adding new data layers and features to the OSINT Geospatial Intelligence Platform.

## New Features Summary

1. **Radio Stations** - Live broadcast capability with global coverage
2. **Oil Rig Locations** - Offshore drilling infrastructure
3. **Infrastructure Lines** - Power grids and substations
4. **Flight Information Regions (FIRs)** - Airspace boundaries with country attribution
5. **Maritime Boundaries** - International and national waters
6. **Data Type Icons** - Visual icons for all entity types

---

## Architecture Changes

### Backend Changes

#### 1. Update `backend/app/models.py`

Add new entity types and data sources:

```python
class EntityType(str, Enum):
    AIRCRAFT = "aircraft"
    VESSEL = "vessel"
    THERMAL_EVENT = "thermal_event"
    SATELLITE = "satellite"
    RADIO_STATION = "radio_station"      # NEW
    OIL_RIG = "oil_rig"                  # NEW
    POWER_GRID = "power_grid"            # NEW
    POWER_SUBSTATION = "power_substation"# NEW
    FIR = "fir"                          # NEW
    MARITIME_BOUNDARY = "maritime_boundary"# NEW

class DataSource(str, Enum):
    OPENSKY = "opensky"
    AISSTREAM = "aisstream"
    FIRMS = "firms"
    CELESTRAK = "celestrak"
    RADIO_API = "radio_api"              # NEW
    OIL_RIG_API = "oil_rig_api"          # NEW
    POWER_GRID_API = "power_grid_api"    # NEW
    FIR_API = "fir_api"                  # NEW
    MARITIME_API = "maritime_api"        # NEW
```

#### 2. Create New Adapters

**`backend/app/adapters/radio.py`**
- Source: Radio Browser API (free, open-source)
- Data: Radio stations with frequencies, locations, live streams
- Features: Filter by country, language, format

**`backend/app/adapters/oil_rig.py`**
- Source: Open data from offshore platforms
- Data: Rig coordinates, operator, status, production
- Features: Filter by region, operator

**`backend/app/adapters/power_grid.py`**
- Source: OpenStreetMap power lines data
- Data: Transmission lines, substations, voltage levels
- Features: Filter by voltage, type

**`backend/app/adapters/fir.py`**
- Source: ICAO FIR boundaries (GeoJSON)
- Data: Airspace polygons with country attribution
- Features: Filter by country, FIR name

**`backend/app/adapters/maritime.py`**
- Source: Natural Earth maritime boundaries
- Data: EEZ (Exclusive Economic Zone) boundaries
- Features: International vs national waters

#### 3. Update `backend/app/api/unified.py`

Add new entity types to query parameters and response handling.

#### 4. Update `backend/app/cache/redis_client.py`

Add TTL configurations for new entity types.

### Frontend Changes

#### 1. Update `frontend/index.html`

Add new layer controls with icons:

```html
<div class="layer-toggle">
    <span class="layer-icon">📻</span>
    <input type="checkbox" id="toggle-radio">
    <span>Radio Stations</span>
</div>

<div class="layer-toggle">
    <span class="layer-icon">🛢️</span>
    <input type="checkbox" id="toggle-oilrig">
    <span>Oil Rigs</span>
</div>

<div class="layer-toggle">
    <span class="layer-icon">⚡</span>
    <input type="checkbox" id="toggle-powergrid">
    <span>Power Grid</span>
</div>

<div class="layer-toggle">
    <span class="layer-icon">🔌</span>
    <input type="checkbox" id="toggle-substation">
    <span>Substations</span>
</div>

<div class="layer-toggle">
    <span class="layer-icon">✈️</span>
    <input type="checkbox" id="toggle-fir">
    <span>Flight Regions</span>
</div>

<div class="layer-toggle">
    <span class="layer-icon">🌊</span>
    <input type="checkbox" id="toggle-maritime">
    <span>Maritime Boundaries</span>
</div>
```

Add radio player UI component.

#### 2. Update `frontend/src/main.js`

Add new layer definitions with appropriate styling:

- **Radio Stations**: Circle markers with frequency info, clickable to play
- **Oil Rigs**: Square markers with operator info
- **Power Grid**: Line layer for transmission lines
- **Substations**: Circle markers with voltage info
- **FIRs**: Polygon layer with country colors
- **Maritime Boundaries**: Polygon layer with water types

Add radio player functionality.

---

## Data Sources

### Radio Stations
- **API**: Radio Browser API (https://de1.api.radio-browser.info/)
- **Data Points**: Name, frequency, country, city, stream URL, tags
- **Live Streaming**: HTML5 audio player integration

### Oil Rigs
- **API**: Open data from offshore platform registries
- **Data Points**: Coordinates, operator, status, production volume
- **Sources**: NOAA, national offshore registries

### Power Grid
- **API**: OpenStreetMap power data (overpass API)
- **Data Points**: Line coordinates, voltage, type (transmission/distribution)
- **Substations**: Node points with voltage levels

### Flight Information Regions
- **API**: ICAO FIR boundaries (GeoJSON from various sources)
- **Data Points**: Polygon coordinates, country, FIR name
- **Sources**: ICAO, Natural Earth

### Maritime Boundaries
- **API**: Natural Earth maritime boundaries
- **Data Points**: EEZ boundaries, water type (international/national)
- **Sources**: Natural Earth, UN OCHA

---

## Implementation Steps

### Phase 1: Backend Infrastructure
1. Update `models.py` with new entity types
2. Create base adapter structure
3. Implement radio station adapter
4. Implement oil rig adapter
5. Implement power grid adapter
6. Implement FIR adapter
7. Implement maritime boundary adapter

### Phase 2: API Updates
1. Update unified API endpoint
2. Add health checks for new sources
3. Update caching strategy

### Phase 3: Frontend UI
1. Update HTML with new layer controls
2. Add radio player component
3. Implement new map layers
4. Add icons for all entity types
5. Update popups for new data types

### Phase 4: Testing & Documentation
1. Test all new data sources
2. Update README with new features
3. Update API documentation
4. Add configuration examples

---

## Data Schema Updates

### Radio Station
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [lon, lat]
  },
  "properties": {
    "source": "radio_api",
    "entity_type": "radio_station",
    "timestamp": "2026-03-18T08:00:00",
    "identifier": "uuid",
    "name": "Station Name",
    "frequency": 98.5,
    "country": "United States",
    "city": "New York",
    "stream_url": "https://stream.url",
    "tags": ["news", "talk"]
  }
}
```

### Oil Rig
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [lon, lat]
  },
  "properties": {
    "source": "oil_rig_api",
    "entity_type": "oil_rig",
    "timestamp": "2026-03-18T08:00:00",
    "identifier": "uuid",
    "name": "Rig Name",
    "operator": "Operator Name",
    "status": "active",
    "production": "1000 bpd"
  }
}
```

### Power Grid Line
```json
{
  "type": "Feature",
  "geometry": {
    "type": "LineString",
    "coordinates": [[lon1, lat1], [lon2, lat2]]
  },
  "properties": {
    "source": "power_grid_api",
    "entity_type": "power_grid",
    "timestamp": "2026-03-18T08:00:00",
    "identifier": "uuid",
    "voltage": "230000",
    "type": "transmission"
  }
}
```

### Power Substation
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Point",
    "coordinates": [lon, lat]
  },
  "properties": {
    "source": "power_grid_api",
    "entity_type": "power_substation",
    "timestamp": "2026-03-18T08:00:00",
    "identifier": "uuid",
    "name": "Substation Name",
    "voltage": "230000",
    "capacity": "500 MW"
  }
}
```

### FIR (Flight Information Region)
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
  },
  "properties": {
    "source": "fir_api",
    "entity_type": "fir",
    "timestamp": "2026-03-18T08:00:00",
    "identifier": "uuid",
    "name": "FIR Name",
    "country": "Country Name",
    "icao_code": "KJFK"
  }
}
```

### Maritime Boundary
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[lon1, lat1], [lon2, lat2], ...]]
  },
  "properties": {
    "source": "maritime_api",
    "entity_type": "maritime_boundary",
    "timestamp": "2026-03-18T08:00:00",
    "identifier": "uuid",
    "water_type": "international",
    "country": "Country Name",
    "name": "EEZ Name"
  }
}
```

---

## Visual Design

### Entity Type Icons
| Entity Type | Icon | Color |
|-------------|------|-------|
| Aircraft | ✈️ | Blue |
| Vessel | 🚢 | Green |
| Thermal Event | 🔥 | Red |
| Satellite | 🛰️ | Orange |
| Radio Station | 📻 | Purple |
| Oil Rig | 🛢️ | Teal |
| Power Grid | ⚡ | Cyan |
| Substation | 🔌 | Magenta |
| FIR | ✈️ | Indigo |
| Maritime Boundary | 🌊 | Blue |

### Layer Styling
- **Points**: Circle markers with appropriate colors and sizes
- **Lines**: Stroke with varying widths based on importance
- **Polygons**: Fill with low opacity, stroke with country colors

---

## Configuration

### Environment Variables

```bash
# Radio API
RADIO_API_URL=https://de1.api.radio-browser.info/json/stations/search

# Oil Rig API
OIL_RIG_API_URL=https://api.oilrigs.org/v1

# Power Grid API
POWER_GRID_API_URL=https://overpass-api.de/api/interpreter

# FIR API
FIR_API_URL=https://raw.githubusercontent.com/...

# Maritime API
MARITIME_API_URL=https://raw.githubusercontent.com/...
```

---

## Performance Considerations

1. **Caching**: Implement Redis caching for static data (FIRs, maritime boundaries)
2. **Pagination**: Use pagination for radio stations (large dataset)
3. **Debouncing**: Debounce map viewport changes
4. **Lazy Loading**: Load new layers on demand
5. **Rate Limiting**: Respect API rate limits

---

## Dependencies

### Backend
- `fastapi` - Already installed
- `httpx` - Already installed
- `redis` - Already installed
- `pydantic` - Already installed

### Frontend
- `maplibre-gl` - Already installed
- No additional dependencies needed

---

## Testing Strategy

1. **Unit Tests**: Test each adapter independently
2. **Integration Tests**: Test unified API endpoint
3. **UI Tests**: Verify layer visibility and interactions
4. **Performance Tests**: Measure API latency with new data sources

---

## Rollback Plan

If any feature fails:
1. Disable the problematic adapter in config
2. Remove layer toggle from UI
3. Update documentation

---

## Future Enhancements

1. **Real-time Radio Streaming**: WebSocket for live audio
2. **Oil Rig Production Data**: Historical production charts
3. **Power Grid Status**: Real-time outage data
4. **FIR Weather Data**: Weather overlays for each region
5. **Maritime Traffic**: AIS integration for ships in EEZ
