"""AISStream adapter for vessel data via WebSocket."""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta

import websockets

from app.adapters.base import BaseAdapter, AdapterError
from app.models import GeoJSONFeature, DataSource, EntityType, BoundingBox
from app.config import settings

logger = logging.getLogger(__name__)


class AISStreamAdapter(BaseAdapter):
    """Adapter for AISStream WebSocket API."""

    def __init__(self):
        """Initialize the AISStream adapter."""
        super().__init__(DataSource.AISSTREAM)
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._connected = False
        self._vessel_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = asyncio.Lock()
        self._message_count = 0
        self._last_message_time: Optional[datetime] = None

    async def connect(self):
        """Connect to the AISStream WebSocket."""
        if self._connected and self._websocket and not self._websocket.closed:
            return

        try:
            # Prepare connection parameters
            extra_headers = {}

            # Force IPv4 if configured
            if settings.aisstream_force_ipv4:
                import socket
                extra_headers["Host"] = "stream.aisstream.io"

            self._websocket = await websockets.connect(
                settings.aisstream_ws_url,
                extra_headers=extra_headers,
                close_timeout=10.0,
            )

            # Send subscription message
            # AISStream API expects: APIKey, BoundingBoxes (nested array), FilterMessageTypes
            subscribe_msg = {
                "APIKey": settings.aisstream_api_key,
                "BoundingBoxes": [[[settings.aisstream_lamin, settings.aisstream_lomin], [settings.aisstream_lamax, settings.aisstream_lomax]]],
                "FilterMessageTypes": settings.aisstream_message_types,
            }

            await self._websocket.send(json.dumps(subscribe_msg))
            self._connected = True
            logger.info("AISStream: Connected successfully")

        except Exception as e:
            self._connected = False
            raise AdapterError(f"AISStream connection failed: {e}")

    async def disconnect(self):
        """Disconnect from the AISStream WebSocket."""
        if self._websocket and not self._websocket.closed:
            await self._websocket.close()
        self._connected = False
        logger.info("AISStream: Disconnected")

    async def _listen_loop(self, duration: float = 5.0):
        """Listen for messages for a specified duration."""
        if not self._connected:
            await self.connect()

        end_time = asyncio.get_event_loop().time() + duration
        max_messages = settings.aisstream_max_messages

        try:
            while asyncio.get_event_loop().time() < end_time:
                try:
                    message = await asyncio.wait_for(
                        self._websocket.recv(),
                        timeout=1.0,
                    )
                    await self._process_message(message)

                    self._message_count += 1
                    if self._message_count >= max_messages:
                        logger.warning(
                            f"AISStream: Reached max messages ({max_messages}), stopping"
                        )
                        break

                except asyncio.TimeoutError:
                    # No message, continue loop
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("AISStream: Connection closed")
                    self._connected = False
                    break

        except Exception as e:
            logger.error(f"AISStream: Error in listen loop: {e}")
            self._connected = False

    async def _process_message(self, message: str):
        """Process a single AIS message."""
        try:
            data = json.loads(message)
            
            # AISStream API returns messages with Message and MetaData keys
            message_data = data.get("Message", {})
            metadata = data.get("MetaData", {})
            
            # Extract message type from the nested Message structure
            # The Message key contains the actual message type as a nested key
            message_type = ""
            message_body = {}
            
            for key in message_data.keys():
                if key in ["PositionReport", "ShipStaticData", "StandardClassBPositionReport",
                          "ExtendedClassBPositionReport", "LongRangeAisBroadcastMessage",
                          "StaticDataReport"]:
                    message_type = key
                    message_body = message_data[key]
                    break
            
            if not message_type:
                return

            # Create a normalized data structure for processing
            normalized_data = {
                "type": message_type,
                "meta": metadata,
                "message": message_body
            }

            if message_type == "PositionReport":
                await self._process_position_report(normalized_data)
            elif message_type == "ShipStaticData":
                await self._process_static_data(normalized_data)
            elif message_type == "StandardClassBPositionReport":
                await self._process_position_report(normalized_data)
            elif message_type == "ExtendedClassBPositionReport":
                await self._process_position_report(normalized_data)
            elif message_type == "LongRangeAisBroadcastMessage":
                await self._process_position_report(normalized_data)
            elif message_type == "StaticDataReport":
                await self._process_static_data(normalized_data)

        except Exception as e:
            logger.warning(f"AISStream: Failed to process message: {e}")

    async def _process_position_report(self, data: Dict[str, Any]):
        """Process a position report message."""
        try:
            meta = data.get("meta", {})
            message = data.get("message", {})

            # AISStream API uses MMSI (uppercase) in MetaData
            mmsi = str(meta.get("MMSI", ""))
            if not mmsi:
                return

            # AISStream API uses Latitude and Longitude (capitalized)
            lat = message.get("Latitude")
            lon = message.get("Longitude")
            
            # AISStream API uses Sog (Speed over ground) and Cog (Course over ground)
            speed_kts = message.get("Sog")
            course = message.get("Cog")
            heading = message.get("TrueHeading")
            
            # Convert speed from knots to m/s
            speed_mps = (speed_kts * 0.514444) if speed_kts is not None else None
            
            # Get timestamp from MetaData
            timestamp = meta.get("time_utc", datetime.utcnow().isoformat())

            if lat is None or lon is None:
                return

            async with self._cache_lock:
                if mmsi not in self._vessel_cache:
                    self._vessel_cache[mmsi] = {}

                self._vessel_cache[mmsi].update({
                    "lat": lat,
                    "lon": lon,
                    "speed_mps": speed_mps,
                    "speed_kts": speed_kts,
                    "course": course,
                    "heading": heading,
                    "timestamp": timestamp,
                })

        except Exception as e:
            logger.warning(f"AISStream: Failed to process position report: {e}")

    async def _process_static_data(self, data: Dict[str, Any]):
        """Process static data message."""
        try:
            meta = data.get("meta", {})
            message = data.get("message", {})

            # AISStream API uses MMSI (uppercase) in MetaData
            mmsi = str(meta.get("MMSI", ""))
            if not mmsi:
                return

            # AISStream API uses capitalized field names for static data
            name = message.get("Name", "")
            ship_type = message.get("ShipType", 0)
            length = message.get("Length", 0)
            width = message.get("Width", 0)

            async with self._cache_lock:
                if mmsi not in self._vessel_cache:
                    self._vessel_cache[mmsi] = {}

                self._vessel_cache[mmsi].update({
                    "name": name,
                    "ship_type": ship_type,
                    "length": length,
                    "width": width,
                })

        except Exception as e:
            logger.warning(f"AISStream: Failed to process static data: {e}")

    async def fetch(
        self,
        bbox: Optional[BoundingBox] = None,
    ) -> List[GeoJSONFeature]:
        """Fetch vessel data from AISStream."""
        if not settings.aisstream_api_key:
            logger.warning("AISStream: No API key configured")
            return []

        try:
            # Listen for messages
            sample_duration = settings.aisstream_sample_s
            await self._listen_loop(duration=sample_duration)

            # Convert cache to GeoJSON features
            features = []
            stale_threshold = settings.aisstream_stale_s
            now = datetime.utcnow()

            async with self._cache_lock:
                for mmsi, vessel_data in list(self._vessel_cache.items()):
                    try:
                        lat = vessel_data.get("lat")
                        lon = vessel_data.get("lon")

                        if lat is None or lon is None:
                            continue

                        # Check if stale
                        timestamp_str = vessel_data.get("timestamp")
                        if timestamp_str:
                            try:
                                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                                age = (now - timestamp).total_seconds()
                                if age > stale_threshold:
                                    # Remove stale vessel
                                    del self._vessel_cache[mmsi]
                                    continue
                            except:
                                timestamp = now
                        else:
                            timestamp = now

                        # Create metadata
                        metadata = {
                            "mmsi": mmsi,
                            "name": vessel_data.get("name", ""),
                            "speed": vessel_data.get("speed"),
                            "course": vessel_data.get("course"),
                            "ship_type": vessel_data.get("ship_type"),
                            "length": vessel_data.get("length"),
                            "width": vessel_data.get("width"),
                        }

                        feature = GeoJSONFeature.create_point(
                            lon=lon,
                            lat=lat,
                            source=DataSource.AISSTREAM,
                            entity_type=EntityType.VESSEL,
                            identifier=mmsi,
                            timestamp=timestamp,
                            metadata=metadata,
                        )

                        features.append(feature)

                    except Exception as e:
                        logger.warning(f"AISStream: Failed to create feature for {mmsi}: {e}")
                        continue

            self._last_message_time = now
            logger.info(f"AISStream: Fetched {len(features)} vessels")
            return features

        except Exception as e:
            raise AdapterError(f"AISStream fetch error: {e}")

    async def close(self):
        """Close the WebSocket connection."""
        await self.disconnect()