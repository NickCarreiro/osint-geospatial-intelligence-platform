#!/usr/bin/env python3
"""
Test script for FIRMS thermal/fire data.
Tests fetching thermal event data from the unified API filtered by source.
"""

import requests
import json
from datetime import datetime

# API base URL
API_BASE = "http://localhost:8002"

def test_firms_data():
    """Test fetching FIRMS thermal event data."""
    print("=" * 60)
    print("Testing FIRMS Thermal Event Data")
    print("=" * 60)
    print()

    url = f"{API_BASE}/api/unified"
    params = {
        'sources': 'firms',
        'entity_types': 'thermal_event',
    }

    print(f"Requesting: {url}")
    print(f"Parameters: {params}")
    print()

    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])
            metadata = data.get('metadata', {})

            print(f"Thermal events returned: {len(features)}")
            print()

            if len(features) == 0:
                print("⚠ No thermal event data returned")
                print("  This could mean:")
                print("  - FIRMS API key is not configured")
                print("  - FIRMS API is down")
                print("  - No thermal events in the requested area")
                print("  - Rate limit exceeded (5000 requests / 10 minutes)")
                print()
                return False

            # Validate response structure
            print("Validation:")
            valid_count = 0
            for i, feature in enumerate(features[:5]):  # Check first 5
                props = feature.get('properties', {})
                geom = feature.get('geometry', {})

                has_source = props.get('source') == 'firms'
                has_entity_type = props.get('entity_type') == 'thermal_event'
                has_timestamp = 'timestamp' in props
                has_identifier = 'identifier' in props
                has_metadata = 'metadata' in props
                has_coords = geom.get('type') == 'Point' and len(geom.get('coordinates', [])) == 2

                if all([has_source, has_entity_type, has_timestamp, has_identifier, has_metadata, has_coords]):
                    valid_count += 1

                print(f"  Thermal Event {i+1}:")
                print(f"    ✓ Source: {props.get('source')}")
                print(f"    ✓ Entity Type: {props.get('entity_type')}")
                print(f"    ✓ Timestamp: {props.get('timestamp')}")
                print(f"    ✓ Identifier: {props.get('identifier')}")
                print(f"    ✓ Coordinates: {geom.get('coordinates')}")

                # Show metadata
                meta = props.get('metadata', {})
                print(f"    Metadata:")
                print(f"      Confidence: {meta.get('confidence')}")
                print(f"      Fire Radiative Power: {meta.get('fire_radiative_power')} MW")
                print(f"      Satellite: {meta.get('satellite')}")
                print(f"      Brightness: {meta.get('brightness')} K")
                print(f"      Day/Night: {meta.get('daynight')}")
                print()

            print(f"Validation Summary: {valid_count}/{min(5, len(features))} events valid")
            print()

            if valid_count == min(5, len(features)):
                print("✓ FIRMS data test PASSED")
                return True
            else:
                print("✗ FIRMS data test FAILED - Invalid feature structure")
                return False

        else:
            print(f"✗ FIRMS data test FAILED")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("✗ Connection Error: Could not connect to the API")
        print("  Make sure the server is running on http://localhost:8002")
        return False
    except requests.exceptions.Timeout:
        print("✗ Timeout Error: Request timed out")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_firms_with_bbox():
    """Test FIRMS data with bounding box filter."""
    print("=" * 60)
    print("Testing FIRMS with Bounding Box")
    print("=" * 60)
    print()

    url = f"{API_BASE}/api/unified"
    params = {
        'sources': 'firms',
        'entity_types': 'thermal_event',
        'lamin': -30.0,  # Australia (fire prone area)
        'lomin': 115.0,
        'lamax': -10.0,
        'lomax': 155.0,
    }

    print(f"Requesting: {url}")
    print(f"Bounding Box: Australia")
    print(f"Parameters: {params}")
    print()

    try:
        response = requests.get(url, params=params, timeout=30)
        print(f"Status Code: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()
            features = data.get('features', [])

            print(f"Thermal events in bounding box: {len(features)}")
            print()

            if len(features) > 0:
                # Show sample
                sample = features[0]
                props = sample.get('properties', {})
                geom = sample.get('geometry', {})
                coords = geom.get('coordinates', [])

                print("Sample Thermal Event:")
                print(f"  Position: {coords[1]:.4f}, {coords[0]:.4f}")
                print(f"  Confidence: {props.get('metadata', {}).get('confidence', 'N/A')}")
                print(f"  FRP: {props.get('metadata', {}).get('fire_radiative_power', 'N/A')} MW")
                print(f"  Satellite: {props.get('metadata', {}).get('satellite', 'N/A')}")
                print(f"  Timestamp: {props.get('timestamp', 'N/A')}")
                print()

            print("✓ FIRMS bounding box test PASSED")
            return True
        else:
            print(f"✗ FIRMS bounding box test FAILED")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    success1 = test_firms_data()
    print()
    success2 = test_firms_with_bbox()
    exit(0 if (success1 and success2) else 1)