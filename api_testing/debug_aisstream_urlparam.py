#!/usr/bin/env python3
"""
Debug script for AISStream WebSocket connection - testing API key in URL parameter.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import websockets
from env_utils import load_project_env, require_env

load_project_env()
API_KEY = require_env("AISSTREAM_API_KEY")
WS_URL = f"wss://stream.aisstream.io/v0/stream?apiKey={API_KEY}"

async def test_api_key_in_url():
    """Test AISStream WebSocket connection with API key in URL parameter."""
    print("=" * 60)
    print("Testing AISStream WebSocket - API Key in URL Parameter")
    print("=" * 60)
    print()
    
    print("WebSocket URL: wss://stream.aisstream.io/v0/stream?apiKey=<redacted>")
    print()
    
    try:
        print("Connecting to WebSocket...")
        websocket = await websockets.connect(
            WS_URL,
            close_timeout=10.0,
        )
        
        print("✓ Connected successfully!")
        print()
        
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
        
        print(f"Sending subscription message: {json.dumps(subscribe_msg, indent=2)}")
        await websocket.send(json.dumps(subscribe_msg))
        print("✓ Subscription sent")
        print()
        
        # Listen for messages
        print("Listening for messages (10 seconds)...")
        print("-" * 60)
        
        message_count = 0
        timeout = 10
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                message_count += 1
                
                data = json.loads(message)
                msg_type = data.get("type", "Unknown")
                
                print(f"Message {message_count}: {msg_type}")
                
                if message_count <= 3:
                    print(f"  Content: {json.dumps(data, indent=2)[:200]}...")
                
                if message_count >= 10:
                    print(f"  (received {message_count} messages, stopping early)")
                    break
                    
            except asyncio.TimeoutError:
                print(".", end="", flush=True)
                continue
            except websockets.exceptions.ConnectionClosed as e:
                print(f"\n✗ Connection closed: {e}")
                break
        
        print()
        print("-" * 60)
        print(f"Total messages received: {message_count}")
        
        await websocket.close()
        print("✓ Connection closed")
        
        return message_count > 0
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_api_key_in_url())
    exit(0 if result else 1)
