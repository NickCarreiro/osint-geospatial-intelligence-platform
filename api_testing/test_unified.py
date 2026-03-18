#!/usr/bin/env python3
"""
Test script for the unified API endpoint.
Tests fetching data from all sources and filtering by entity type.
"""

import requests
import json
from datetime import datetime

# API base URL
API_BASE = "http://localhost:8002"

def test_unified_endpoint():
    """Test the /api/unified endpoint."""
    print("=" * 60)
    print("Testing Unified API Endpoint")
    print("=" * 60)
    print()

    url = f"{API_BASE}/api/unified"
    print(f"Requesting: {url}")
    print()

    try:
        response = requests.get(url, timeout=30)
        print(f"Status Code: {response.status_code}")
        print()

        if response.status_code == 200:
            data = response.json()
            print("Response Summary:")
            print(f"  Type: {data.get('type')}")
            print(f"  Feature Count: {len(data.get('features', []))}")
            print()

            # Validate response structure
            print("Validation:")
            print(f"  ✓ Has 'type' field: {'type' in data}")
            print(f"  ✓ Has 'features' field: {'features' in data}")
            print(f"  ✓ Has 'metadata' field: {'metadata' in data}")
            print()

            # Check metadata
            if 'metadata' in data:
                metadata = data['metadata']
                print("Metadata:")
                print(f"  Total Count: {metadata.get('count', 0)}")
                print(f"  Latency: {metadata.get('latency_ms', 0)}ms")
                print(f"  Timestamp: {metadata.get('timestamp', 'N/A')}")
                print()

                # Check source counts
                if 'sources' in metadata:
                    print("Source Counts:")
                    for source, count in metadata['sources'].items():
                        print(f"  {source}: {count}")
                    print()

                # Check entity type counts
                if 'entity_types' in metadata:
                    print("Entity Type Counts:")
                    for entity_type, count in metadata['entity_types'].items():
                        print(f"  {entity_type}: {count}")
                    print()

            # Show sample features
            features = data.get('features', [])
            if features:
                print(f"Sample Feature (first of {len(features)}):")
                sample = features[0]
                print(json.dumps(sample, indent=2))
                print()

            print("✓ Unified endpoint test PASSED")
            return True
        else:
            print(f"✗ Unified endpoint test FAILED")
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


def test_unified_with_filters():
    """Test the /api/unified endpoint with filters."""
    print("=" * 60)
    print("Testing Unified API with Filters")
    print("=" * 60)
    print()

    # Test with bounding box (Europe)
    url = f"{API_BASE}/api/unified"
    params = {
        'lamin': 35.0,
        'lomin': -10.0,
        'lamax': 60.0,
        'lomax': 40.0,
        'entity_types': 'aircraft,vessel',
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

            print(f"Features returned: {len(features)}")
            print()

            # Count by entity type
            entity_counts = {}
            for feature in features:
                entity_type = feature.get('properties', {}).get('entity_type', 'unknown')
                entity_counts[entity_type] = entity_counts.get(entity_type, 0) + 1

            print("Entity Type Breakdown:")
            for entity_type, count in entity_counts.items():
                print(f"  {entity_type}: {count}")
            print()

            # Count by source
            source_counts = {}
            for feature in features:
                source = feature.get('properties', {}).get('source', 'unknown')
                source_counts[source] = source_counts.get(source, 0) + 1

            print("Source Breakdown:")
            for source, count in source_counts.items():
                print(f"  {source}: {count}")
            print()

            print("✓ Unified endpoint with filters test PASSED")
            return True
        else:
            print(f"✗ Unified endpoint with filters test FAILED")
            print(f"Response: {response.text}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == "__main__":
    success1 = test_unified_endpoint()
    print()
    success2 = test_unified_with_filters()
    exit(0 if (success1 and success2) else 1)