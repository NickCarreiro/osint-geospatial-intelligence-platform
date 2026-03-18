"""Cache module for the OSINT platform."""
from app.cache.redis_client import RedisCache, cache

__all__ = ["RedisCache", "cache"]