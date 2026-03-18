#!/usr/bin/env python3
"""
Test script for CelesTrak satellite data.
Tests the CelesTrak adapter directly without the HTTP server.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.adapters.celestrak import CelesTrakAdapter
from app.models import BoundingBox


async def test_celestrak_data():
    """Test fetching CelesTrak satellite data."""
    print("=" * 60)
    print("Testing CelesTrak Satellite Data")
    print("=" * 60)
    print()

    adapter = CelesTrakAdapter()
    
    try:
        # Test with global bounding box
        bbox = BoundingBox(
            lamin=-90.0,
            lomin=-180.0,
            lamax=90.0,
            lomax=180.0
        )
        
        print(f"Fetching satellite data...")
        print(f"Bounding Box: Global")
        print()
        
        features = await adapter.fetch(bbox)
        
        print(f"Satellites returned: {len(features)}")
        print()
        
        if len(features) == 0:
            print("⚠ No satellite data returned")
            print("  This could mean:")
            print("  - CelesTrak TLE URL is not accessible")
            print("  - TLE catalog refresh failed")
            print("  - Orbital propagation error")
            print()
            return False
        
        # Validate response structure
        print("Validation:")
        valid_count = 0
        for i, feature in enumerate(features[:5]):  # Check first 5
            # Access Pydantic model fields
            props = feature.properties
            geom = feature.geometry
            
            has_source = props.get('source') == 'celestrak'
            has_entity_type = props.get('entity_type') == 'satellite'
            has_timestamp = 'timestamp' in props
            has_identifier = 'identifier' in props
            has_metadata = 'metadata' in props
            has_coords = geom.get('type') == 'Point' and len(geom.get('coordinates', [])) == 2
            
            if all([has_source, has_entity_type, has_timestamp, has_identifier, has_metadata, has_coords]):
                valid_count += 1
            
            print(f"  Satellite {i+1}:")
            print(f"    ✓ Source: {props.get('source')}")
            print(f"    ✓ Entity Type: {props.get('entity_type')}")
            print(f"    ✓ Timestamp: {props.get('timestamp')}")
            print(f"    ✓ Identifier (NORAD): {props.get('identifier')}")
            print(f"    ✓ Coordinates: {geom.get('coordinates')}")
            
            # Show metadata
            meta = props.get('metadata', {})
            print(f"    Metadata:")
            print(f"      NORAD ID: {meta.get('norad_id')}")
            print(f"      Name: {meta.get('name')}")
            print(f"      Altitude: {meta.get('altitude')} km")
            print(f"      Inclination: {meta.get('inclination')}°")
            print()
        
        print(f"Validation Summary: {valid_count}/{min(5, len(features))} satellites valid")
        print()
        
        if valid_count == min(5, len(features)):
            print("✓ CelesTrak data test PASSED")
            return True
        else:
            print("✗ CelesTrak data test FAILED - Invalid feature structure")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await adapter.close()


async def test_celestrak_with_bbox():
    """Test CelesTrak data with bounding box filter."""
    print("=" * 60)
    print("Testing CelesTrak with Bounding Box")
    print("=" * 60)
    print()
    
    adapter = CelesTrakAdapter()
    
    try:
        # Test with North America bounding box
        bbox = BoundingBox(
            lamin=25.0,
            lomin=-125.0,
            lamax=50.0,
            lomax=-65.0
        )
        
        print(f"Fetching satellite data...")
        print(f"Bounding Box: North America")
        print()
        
        features = await adapter.fetch(bbox)
        
        print(f"Satellites in bounding box: {len(features)}")
        print()
        
        if len(features) > 0:
            # Show sample
            sample = features[0]
            # Access Pydantic model fields
            props = sample.properties
            geom = sample.geometry
            coords = geom.get('coordinates', [])
            
            print("Sample Satellite:")
            print(f"  Position: {coords[1]:.4f}, {coords[0]:.4f}")
            print(f"  NORAD ID: {props.get('metadata', {}).get('norad_id', 'N/A')}")
            print(f"  Name: {props.get('metadata', {}).get('name', 'N/A')}")
            print(f"  Altitude: {props.get('metadata', {}).get('altitude', 'N/A')} km")
            print(f"  Inclination: {props.get('metadata', {}).get('inclination', 'N/A')}°")
            print()
        
        print("✓ CelesTrak bounding box test PASSED")
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await adapter.close()


async def main():
    """Run all tests."""
    # Load environment variables
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    
    success1 = await test_celestrak_data()
    print()
    success2 = await test_celestrak_with_bbox()
    
    return success1 and success2


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)