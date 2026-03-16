#!/usr/bin/env python3
"""
Test script for AISStream vessel data.
Tests the AISStream adapter directly without the HTTP server.
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.adapters.aisstream import AISStreamAdapter
from app.models import BoundingBox


async def test_aisstream_data():
    """Test fetching AISStream vessel data."""
    print("=" * 60)
    print("Testing AISStream Vessel Data")
    print("=" * 60)
    print()

    adapter = AISStreamAdapter()
    
    try:
        # Test with global bounding box
        bbox = BoundingBox(
            lamin=-90.0,
            lomin=-180.0,
            lamax=90.0,
            lomax=180.0
        )
        
        print(f"Fetching vessel data...")
        print(f"Bounding Box: Global")
        print()
        
        features = await adapter.fetch(bbox)
        
        print(f"Vessels returned: {len(features)}")
        print()
        
        if len(features) == 0:
            print("⚠ No vessel data returned")
            print("  This could mean:")
            print("  - AISStream API key is not configured")
            print("  - AISStream WebSocket connection failed")
            print("  - No vessels in the requested area")
            print()
            return False
        
        # Validate response structure
        print("Validation:")
        valid_count = 0
        for i, feature in enumerate(features[:5]):  # Check first 5
            # Access Pydantic model fields
            props = feature.properties
            geom = feature.geometry
            
            has_source = props.get('source') == 'aisstream'
            has_entity_type = props.get('entity_type') == 'vessel'
            has_timestamp = 'timestamp' in props
            has_identifier = 'identifier' in props
            has_metadata = 'metadata' in props
            has_coords = geom.get('type') == 'Point' and len(geom.get('coordinates', [])) == 2
            
            if all([has_source, has_entity_type, has_timestamp, has_identifier, has_metadata, has_coords]):
                valid_count += 1
            
            print(f"  Vessel {i+1}:")
            print(f"    ✓ Source: {props.get('source')}")
            print(f"    ✓ Entity Type: {props.get('entity_type')}")
            print(f"    ✓ Timestamp: {props.get('timestamp')}")
            print(f"    ✓ Identifier (MMSI): {props.get('identifier')}")
            print(f"    ✓ Coordinates: {geom.get('coordinates')}")
            
            # Show metadata
            meta = props.get('metadata', {})
            print(f"    Metadata:")
            print(f"      MMSI: {meta.get('mmsi')}")
            print(f"      Name: {meta.get('name')}")
            print(f"      Speed: {meta.get('speed')} kts")
            print(f"      Course: {meta.get('course')}°")
            print(f"      Ship Type: {meta.get('ship_type')}")
            print()
        
        print(f"Validation Summary: {valid_count}/{min(5, len(features))} vessels valid")
        print()
        
        if valid_count == min(5, len(features)):
            print("✓ AISStream data test PASSED")
            return True
        else:
            print("✗ AISStream data test FAILED - Invalid feature structure")
            return False
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await adapter.close()


async def test_aisstream_with_bbox():
    """Test AISStream data with bounding box filter."""
    print("=" * 60)
    print("Testing AISStream with Bounding Box")
    print("=" * 60)
    print()
    
    adapter = AISStreamAdapter()
    
    try:
        # Test with Mediterranean bounding box
        bbox = BoundingBox(
            lamin=35.0,
            lomin=-10.0,
            lamax=45.0,
            lomax=20.0
        )
        
        print(f"Fetching vessel data...")
        print(f"Bounding Box: Mediterranean")
        print()
        
        features = await adapter.fetch(bbox)
        
        print(f"Vessels in bounding box: {len(features)}")
        print()
        
        if len(features) > 0:
            # Show sample
            sample = features[0]
            props = sample.properties
            geom = sample.geometry
            coords = geom.get('coordinates', [])
            
            print("Sample Vessel:")
            print(f"  Position: {coords[1]:.4f}, {coords[0]:.4f}")
            print(f"  MMSI: {props.get('metadata', {}).get('mmsi', 'N/A')}")
            print(f"  Name: {props.get('metadata', {}).get('name', 'N/A')}")
            print(f"  Speed: {props.get('metadata', {}).get('speed', 'N/A')} kts")
            print(f"  Course: {props.get('metadata', {}).get('course', 'N/A')}°")
            print()
        
        print("✓ AISStream bounding box test PASSED")
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
    
    success1 = await test_aisstream_data()
    print()
    success2 = await test_aisstream_with_bbox()
    
    return success1 and success2


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)