# sit_mon

Backend-first OSINT data aggregation and JSON snapshot tooling.

The current focus is the backend. The FastAPI service is still available, but the active workflow is generating source-specific JSON files under `reports/` instead of building out the browser UI.

## Current report programs

Each standalone program writes one stable JSON file by default:

| Program | Default output |
| --- | --- |
| `python3 generate_radio_report.py` | `reports/radio_api.json` |
| `python3 generate_oil_rig_report.py` | `reports/oil_rig_api.json` |
| `python3 generate_power_grid_report.py` | `reports/power_grid_api.json` |
| `python3 generate_maritime_report.py` | `reports/maritime_api.json` |
| `python3 generate_reports.py` | refreshes all of the above plus `reports/index.json` |

The report directory is created automatically if it does not exist.

## Quick start

### Start the backend API

```bash
cd /home/admin/access/homelab/sit_mon
./start.sh
```

Available endpoints:

- API: `http://localhost:8002/api/unified`
- Health: `http://localhost:8002/health`
- Docs: `http://localhost:8002/docs`

### Generate snapshot files

Run any source program directly:

```bash
python3 generate_radio_report.py
python3 generate_oil_rig_report.py
python3 generate_power_grid_report.py
python3 generate_maritime_report.py
```

Or refresh all source files in one pass:

```bash
python3 generate_reports.py
```

## Country and bbox filters

All report programs support either a resolved country or an explicit bounding box.

Examples:

```bash
python3 generate_power_grid_report.py --country Luxembourg
python3 generate_oil_rig_report.py --lamin 28.6 --lomin -90.6 --lamax 28.8 --lomax -90.2
python3 generate_reports.py --sources power_grid_api,radio_api --country Luxembourg
```

Rules:

- Use either `--country` or the four bbox flags together.
- `Radio` and `Maritime` use the resolved country code directly when possible.
- `Oil Rig` and `Power Grid` use the resolved country bounding box.

## Current backend snapshot sources

- `radio_api`: Radio Browser stations
- `oil_rig_api`: offshore infrastructure from OpenStreetMap Overpass queries
- `power_grid_api`: transmission lines and substations from OpenStreetMap Overpass queries
- `maritime_api`: maritime boundaries from Natural Earth

## Report file shape

Each source JSON file includes:

- `source`
- `report_file`
- `generated_at`
- `status`
- `healthy`
- `error_message`
- `warning_message`
- `country`
- `bbox`
- `entity_count`
- `latency_ms`
- `source_url`
- `features`

`status` values:

- `ok`: source completed normally
- `partial`: source returned usable data with a warning
- `empty`: source completed but returned no entities
- `error`: source failed

## Notes

- Public Overpass-backed sources can still degrade upstream. When that happens, the JSON report should say so explicitly instead of failing silently.
- Generated artifacts such as `reports/`, `reports_*/`, `.cache/`, and `tmp/` are intentionally ignored by git.
- Frontend files may still exist in the repo, but they are not the current development focus.
