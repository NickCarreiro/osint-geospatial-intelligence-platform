#!/usr/bin/env python3
"""
Test script for OpenSky aircraft data.
Tests the OpenSky adapter directly without the HTTP server.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.adapters.opensky import OpenSkyAdapter
from app.models import BoundingBox


async def test_opensky_data():
    """Test fetching OpenSky aircraft data."""
    print("=" * 60)
    print("Testing OpenSky Aircraft Data")
    print("=" * 60)
    print()

    adapter = OpenSkyAdapter()
    
    try:
        # Test with global bounding box
        bbox = BoundingBox(
            lamin=-85.0,
            lomin=-180.0,
            lamax=85.0,
            lomax=180.0
        )
        
        print(f"Fetching aircraft data...")
        print(f"Bounding Box: Global")
        print()
        
        features = await adapter.fetch(bbox)
        
        print(f"Aircraft returned: {len(features)}")
        print()
        
        if len(features) == 0:
            print("⚠ No aircraft data returned")
            print("  This could mean:")
            print("  - OpenSky credentials are not configured")
            print("  - OpenSky API is down")
            print("  - No aircraft in the requested area")
            print()
            return False
        
        # Validate response structure
        print("Validation:")
        valid_count = 0
        for i, feature in enumerate(features[:5]):  # Check first 5
            # Access Pydantic model fields
            props = feature.properties
            geom = feature.geometry
            
            has_source = props.get('source') == 'opensky'
            has_entity_type = props.get('entity_type') == 'aircraft'
            has_timestamp = 'timestamp' in props
            has_identifier = 'identifier' in props
            has_metadata = 'metadata' in props
            has_coords = geom.get('type') == 'Point' and len(geom.get('coordinates', [])) == 2
            
            if all([has_source, has_entity_type, has_timestamp, has_identifier, has_metadata, has_coords]):
                valid_count += 1
            
            print(f"  Feature {i+1}:")
            print(f"    ✓ Source: {props.get('source')}")
            print(f"    ✓ Entity Type: {props.get('entity_type')}")
            print(f"    ✓ Timestamp: {props.get('timestamp')}")
            print(f"    ✓ Identifier: {props.get('identifier')}")
            print(f"    ✓ Coordinates: {geom.get('coordinates')}")
            
            # Show metadata
            meta = props.get('metadata', {})
            print(f"    Metadata:")
            print(f"      ICAO24: {meta.get('icao24')}")
            print(f"      Callsign: {meta.get('callsign')}")
            print(f"      Altitude: {meta.get('altitude')}")
            print(f"      Velocity: {meta.get('velocity')}")
            print(f"      Heading: {meta.get('heading')}")
            print()
        
        print(f"Validation Summary: {valid_count}/{min(5, len(features))} features valid")
        print()
        
        if valid_count == min(5, len(features)):
            print("✓ OpenSky data test PASSED")
            return True
        else:
            print("✗ OpenSky data test FAILED - Invalid feature structure")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await adapter.close()


async def test_opensky_with_bbox():
    """Test OpenSky data with bounding box filter."""
    print("=" * 60)
    print("Testing OpenSky with Bounding Box")
    print("=" * 60)
    print()
    
    adapter = OpenSkyAdapter()
    
    try:
        # Test with Northern Europe bounding box
        bbox = BoundingBox(
            lamin=40.0,
            lomin=-10.0,
            lamax=55.0,
            lomax=10.0
        )
        
        print(f"Fetching aircraft data...")
        print(f"Bounding Box: Northern Europe")
        print()
        
        features = await adapter.fetch(bbox)
        
        print(f"Aircraft in bounding box: {len(features)}")
        print()
        
        if len(features) > 0:
            # Show sample
            sample = features[0]
            coords = sample.geometry.get('coordinates', [])
            meta = sample.properties.get('metadata', {})
            
            print("Sample Aircraft:")
            print(f"  Position: {coords[1]:.4f}, {coords[0]:.4f}")
            print(f"  Callsign: {meta.get('callsign', 'N/A')}")
            print(f"  Altitude: {meta.get('altitude', 'N/A')} ft")
            print(f"  Velocity: {meta.get('velocity', 'N/A')} kts")
            print()
        
        print("✓ OpenSky bounding box test PASSED")
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
    
    success1 = await test_opensky_data()
    print()
    success2 = await test_opensky_with_bbox()
    
    return success1 and success2


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)