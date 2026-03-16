"""Redis cache wrapper for the OSINT platform."""
import json
import logging
from typing import Any, Optional, List
from datetime import datetime, timedelta

from redis.asyncio import Redis as AsyncRedis
from redis.exceptions import RedisError

from app.config import settings
from app.models import GeoJSONFeature, EntityType

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache wrapper with TTL support."""

    def __init__(self):
        """Initialize the Redis cache."""
        self._client: Optional[AsyncRedis] = None
        self._connected = False
        self._available = True

    async def get_client(self) -> Optional[AsyncRedis]:
        """Get or create Redis client."""
        if not self._available:
            return None

        if self._client is None:
            try:
                self._client = AsyncRedis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                # Test connection
                await self._client.ping()
                self._connected = True
            except RedisError as e:
                logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
                self._available = False
                self._client = None
                return None
        return self._client

    async def close(self):
        """Close the Redis connection."""
        if self._client:
            try:
                await self._client.close()
            except RedisError:
                pass
            self._connected = False

    def _get_ttl(self, entity_type: EntityType) -> int:
        """Get TTL for an entity type."""
        ttl_map = {
            EntityType.AIRCRAFT: settings.aircraft_ttl_s,
            EntityType.VESSEL: settings.vessel_ttl_s,
            EntityType.SATELLITE: settings.satellite_ttl_s,
            EntityType.THERMAL_EVENT: settings.thermal_ttl_s,
        }
        return ttl_map.get(entity_type, 300)

    def _make_key(self, source: str, entity_type: str, identifier: str) -> str:
        """Create a cache key."""
        return f"{source}:{entity_type}:{identifier}"

    async def get(
        self,
        source: str,
        entity_type: EntityType,
        identifier: str,
    ) -> Optional[GeoJSONFeature]:
        """Get a cached feature."""
        client = await self.get_client()
        if client is None:
            return None

        try:
            key = self._make_key(source, entity_type.value, identifier)
            data = await client.get(key)
            if data is None:
                return None

            feature_dict = json.loads(data)
            return GeoJSONFeature(**feature_dict)

        except RedisError as e:
            logger.warning(f"Redis get error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Redis get: {e}")
            return None

    async def set(
        self,
        feature: GeoJSONFeature,
    ) -> bool:
        """Cache a feature."""
        client = await self.get_client()
        if client is None:
            return False

        try:
            source = feature.properties.get("source")
            entity_type_str = feature.properties.get("entity_type")
            identifier = feature.properties.get("identifier")

            if not all([source, entity_type_str, identifier]):
                return False

            key = self._make_key(source, entity_type_str, identifier)

            # Get TTL based on entity type
            try:
                entity_type = EntityType(entity_type_str)
                ttl = self._get_ttl(entity_type)
            except ValueError:
                ttl = 300  # Default TTL

            # Serialize feature
            data = feature.model_dump_json()

            await client.setex(key, ttl, data)
            return True

        except RedisError as e:
            logger.warning(f"Redis set error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in Redis set: {e}")
            return False

    async def get_many(
        self,
        source: str,
        entity_type: EntityType,
        identifiers: List[str],
    ) -> List[GeoJSONFeature]:
        """Get multiple cached features."""
        client = await self.get_client()
        if client is None:
            return []

        try:
            keys = [
                self._make_key(source, entity_type.value, identifier)
                for identifier in identifiers
            ]

            if not keys:
                return []

            values = await client.mget(keys)
            features = []

            for value in values:
                if value is not None:
                    try:
                        feature_dict = json.loads(value)
                        features.append(GeoJSONFeature(**feature_dict))
                    except Exception as e:
                        logger.warning(f"Failed to parse cached feature: {e}")

            return features

        except RedisError as e:
            logger.warning(f"Redis get_many error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in Redis get_many: {e}")
            return []

    async def set_many(
        self,
        features: List[GeoJSONFeature],
    ) -> int:
        """Cache multiple features."""
        count = 0
        for feature in features:
            if await self.set(feature):
                count += 1
        return count

    async def delete(
        self,
        source: str,
        entity_type: EntityType,
        identifier: str,
    ) -> bool:
        """Delete a cached feature."""
        client = await self.get_client()
        if client is None:
            return False

        try:
            key = self._make_key(source, entity_type.value, identifier)
            await client.delete(key)
            return True

        except RedisError as e:
            logger.warning(f"Redis delete error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error in Redis delete: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        client = await self.get_client()
        if client is None:
            return 0

        try:
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await client.delete(*keys)

            return len(keys)

        except RedisError as e:
            logger.warning(f"Redis delete_pattern error: {e}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error in Redis delete_pattern: {e}")
            return 0

    async def clear_source(self, source: str) -> int:
        """Clear all cached data for a source."""
        pattern = f"{source}:*"
        return await self.delete_pattern(pattern)

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        client = await self.get_client()
        if client is None:
            return {
                "total_keys": 0,
                "source_counts": {},
                "available": False,
            }

        try:
            info = await client.info()
            db_size = info.get("db0", {}).get("keys", 0)

            # Count by source
            source_counts = {}
            for source in ["opensky", "aisstream", "firms", "celestrak"]:
                pattern = f"{source}:*"
                count = 0
                async for key in client.scan_iter(match=pattern):
                    count += 1
                source_counts[source] = count

            return {
                "total_keys": db_size,
                "source_counts": source_counts,
                "available": True,
            }

        except RedisError as e:
            logger.warning(f"Redis get_stats error: {e}")
            return {
                "total_keys": 0,
                "source_counts": {},
                "available": False,
            }
        except Exception as e:
            logger.error(f"Unexpected error in Redis get_stats: {e}")
            return {
                "total_keys": 0,
                "source_counts": {},
                "available": False,
            }


# Global cache instance
cache = RedisCache()