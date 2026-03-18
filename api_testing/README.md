# API Testing Suite

This directory contains test scripts for validating the OSINT Geospatial Intelligence Platform API endpoints.

## Test Scripts

### Individual Provider Tests

Each test script validates a specific data provider:

- **[`test_health.py`](test_health.py)** - Tests the `/health` endpoint (baseline test)
- **[`test_unified.py`](test_unified.py)** - Tests the `/api/unified` endpoint with various filters
- **[`test_opensky.py`](test_opensky.py)** - Tests OpenSky aircraft data
- **[`test_aisstream.py`](test_aisstream.py)** - Tests AISStream vessel data
- **[`test_firms.py`](test_firms.py)** - Tests FIRMS thermal event data
- **[`test_celestrak.py`](test_celestrak.py)** - Tests CelesTrak satellite data

### Master Test Script

- **[`run_all_tests.py`](run_all_tests.py)** - Runs all tests sequentially and reports results

## Prerequisites

1. The API server must be running on `http://localhost:8002`
2. Python 3 with `requests` library installed
3. Required provider credentials must be present in the project `.env`

## Credentials

- Never hardcode provider secrets in these scripts.
- AISStream debug scripts read `AISSTREAM_API_KEY` from the project `.env`.
- FIRMS debug scripts read `FIRMS_API_KEY` from the project `.env`.
- Debug output should only show redacted credential values.

## Running Tests

### Run All Tests

```bash
cd api_testing
python3 run_all_tests.py
```

### Run Individual Tests

```bash
cd api_testing

# Test health endpoint
python3 test_health.py

# Test unified API
python3 test_unified.py

# Test OpenSky (aircraft)
python3 test_opensky.py

# Test AISStream (vessels)
python3 test_aisstream.py

# Test FIRMS (thermal events)
python3 test_firms.py

# Test CelesTrak (satellites)
python3 test_celestrak.py
```

## Test Coverage

Each test script validates:

1. **API Connectivity** - Can connect to the endpoint
2. **Response Structure** - Valid JSON with expected fields
3. **Data Validation** - Features have correct structure and required fields
4. **Metadata Validation** - Source, entity type, timestamp, identifier present
5. **Geospatial Validation** - Valid coordinates in Point geometry
6. **Provider-specific Fields** - Expected metadata fields for each provider

## Expected Results

### Health Endpoint

- Returns overall system status
- Shows health status for each source
- Displays metrics (requests, errors, cache stats)

### Unified API

- Returns GeoJSON FeatureCollection
- Supports filtering by:
  - Bounding box (lamin, lomin, lamax, lomax)
  - Entity types (aircraft, vessel, thermal_event, satellite)
  - Sources (opensky, aisstream, firms, celestrak)
  - Time window (start_time, end_time)

### OpenSky (Aircraft)

- Returns aircraft state vectors
- Includes: icao24, callsign, altitude, velocity, heading
- Validates OAuth authentication

### AISStream (Vessels)

- Returns vessel position reports
- Includes: mmsi, name, speed, course, ship_type
- Validates WebSocket streaming

### FIRMS (Thermal Events)

- Returns thermal anomaly data
- Includes: confidence, fire radiative power, satellite
- Respects rate limits (5000/10min)

### CelesTrak (Satellites)

- Returns satellite orbital positions
- Includes: norad_id, name, altitude, inclination
- Validates orbital propagation

## Troubleshooting

### Connection Errors

```
✗ Connection Error: Could not connect to the API
```

**Solution**: Make sure the server is running:
```bash
./start.sh
```

### No Data Returned

```
⚠ No aircraft data returned
```

**Possible causes**:
- Credentials not configured in `.env`
- API rate limit exceeded
- No entities in requested area
- Source API is down

### Timeout Errors

```
✗ Timeout Error: Request timed out
```

**Possible causes**:
- AISStream WebSocket taking longer to connect
- CelesTrak orbital propagation taking time
- Network connectivity issues

## Exit Codes

- `0` - All tests passed
- `1` - One or more tests failed
