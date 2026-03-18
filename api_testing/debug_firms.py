#!/usr/bin/env python3
"""Debug script to test FIRMS API directly."""
import httpx
from datetime import datetime, timedelta

from env_utils import load_project_env, redact_secret, require_env

load_project_env()
API_KEY = require_env("FIRMS_API_KEY")
BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area"

# Get data from the last 24 hours
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=1)

# FIRMS API parameters
params = {
    "api_key": API_KEY,
    "bbox": "-180.0,-90.0,180.0,90.0",
    "date_range": f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}",
    "satellite": "MODIS_NRT,VIIRS_NOAA20_NRT,VIIRS_SNPP_NRT",
    "output_format": "json",
}

print(f"Requesting FIRMS API...")
print(f"URL: {BASE_URL}/csv/2.0")
safe_params = {**params, "api_key": redact_secret(API_KEY)}
print(f"Params: {safe_params}")
print()

try:
    response = httpx.get(
        f"{BASE_URL}/csv/2.0",
        params=params,
        timeout=30.0
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print()
    
    if response.status_code == 200:
        print("Response Content:")
        print("=" * 80)
        print(response.text)
        print("=" * 80)
        print()
        
        # Try to parse as CSV
        lines = response.text.strip().split("\n")
        print(f"Total lines: {len(lines)}")
        print()
        
        if len(lines) >= 2:
            print("Header:")
            print(lines[0])
            print()
            
            print("First 5 data rows:")
            for i, line in enumerate(lines[1:6]):
                print(f"Row {i+1}: {line}")
    else:
        print(f"Error: {response.text}")
        
except Exception as e:
    print(f"Exception: {e}")
