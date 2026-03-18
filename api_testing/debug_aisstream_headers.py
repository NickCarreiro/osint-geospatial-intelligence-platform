#!/usr/bin/env python3
"""
Debug script for AISStream WebSocket connection - testing different header formats.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import websockets
from env_utils import load_project_env, redact_secret, require_env

load_project_env()
API_KEY = require_env("AISSTREAM_API_KEY")
WS_URL = "wss://stream.aisstream.io/v0/stream"

async def test_header_format(header_name, header_value):
    """Test AISStream WebSocket connection with specific header format."""
    print(f"Testing header: {header_name}")
    print(f"  Value: {redact_secret(header_value)}")
    
    try:
        extra_headers = {header_name: header_value}
        
        websocket = await websockets.connect(
            WS_URL,
            extra_headers=extra_headers,
            close_timeout=10.0,
        )
        
        # Send subscription message
        subscribe_msg = {
            "type": "Subscribe",
            "filters": {
                "messageTypes": "PositionReport",
                "boundingBox": {
                    "minLat": -90.0,
                    "maxLat": 90.0,
                    "minLon": -180.0,
                    "maxLon": 180.0,
                },
            },
        }
        
        await websocket.send(json.dumps(subscribe_msg))
        
        # Listen for first message
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            
            if "error" in data:
                print(f"  ✗ Error: {data['error']}")
                await websocket.close()
                return False
            else:
                print(f"  ✓ Success! Received message type: {data.get('type', 'Unknown')}")
                await websocket.close()
                return True
                
        except asyncio.TimeoutError:
            print(f"  ✗ Timeout - no response")
            await websocket.close()
            return False
            
    except Exception as e:
        print(f"  ✗ Connection error: {e}")
        return False

async def main():
    """Test different header formats."""
    print("=" * 60)
    print("Testing AISStream WebSocket Header Formats")
    print("=" * 60)
    print()
    
    header_formats = [
        ("Api-Key", API_KEY),
        ("api-key", API_KEY),
        ("API-Key", API_KEY),
        ("X-API-Key", API_KEY),
        ("x-api-key", API_KEY),
        ("Authorization", f"Bearer {API_KEY}"),
        ("Authorization", API_KEY),
    ]
    
    results = []
    for header_name, header_value in header_formats:
        result = await test_header_format(header_name, header_value)
        results.append((header_name, result))
        print()
    
    print("=" * 60)
    print("Results:")
    print("=" * 60)
    for header_name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {header_name}")
    
    # Check if any worked
    if any(result for _, result in results):
        print("\n✓ At least one header format worked!")
        return True
    else:
        print("\n✗ No header format worked")
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
