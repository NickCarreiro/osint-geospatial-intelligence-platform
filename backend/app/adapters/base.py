"""Base adapter with retry/backoff logic."""
import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from app.models import GeoJSONFeature, DataSource, SourceStatus
from app.config import settings

logger = logging.getLogger(__name__)


class AdapterError(Exception):
    """Base exception for adapter errors."""
    pass


class RateLimitError(AdapterError):
    """Exception raised when rate limit is exceeded."""
    pass


class BaseAdapter(ABC):
    """Base adapter with retry/backoff logic."""

    def __init__(self, source: DataSource):
        """Initialize the adapter."""
        self.source = source
        self._healthy = True
        self._last_update: Optional[datetime] = None
        self._error_message: Optional[str] = None
        self._entity_count = 0
        self._latency_ms: Optional[float] = None
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._429_cooldown_until: Optional[float] = None

    @abstractmethod
    async def fetch(self, **kwargs) -> List[GeoJSONFeature]:
        """Fetch data from the source."""
        pass

    @abstractmethod
    def get_status(self) -> SourceStatus:
        """Get the current status of the adapter."""
        pass

    async def fetch_with_retry(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        timeout: Optional[float] = None,
        **fetch_kwargs,
    ) -> List[GeoJSONFeature]:
        """Fetch data with retry and exponential backoff."""
        # Check if we're in a 429 cooldown
        if self._429_cooldown_until and time.time() < self._429_cooldown_until:
            wait_time = self._429_cooldown_until - time.time()
            logger.warning(
                f"{self.source.value}: In 429 cooldown, waiting {wait_time:.1f}s"
            )
            return []

        last_error = None
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                result = await asyncio.wait_for(
                    self.fetch(**fetch_kwargs),
                    timeout=timeout,
                )
                latency_ms = (time.time() - start_time) * 1000
                self._latency_ms = latency_ms
                self._entity_count = len(result)
                self._healthy = True
                self._error_message = None
                self._last_update = datetime.utcnow()
                self._failure_count = 0
                logger.info(
                    f"{self.source.value}: Fetched {len(result)} entities in {latency_ms:.1f}ms"
                )
                return result

            except RateLimitError as e:
                # Handle rate limit with cooldown
                self._handle_rate_limit()
                logger.error(f"{self.source.value}: Rate limit exceeded - {e}")
                return []

            except asyncio.TimeoutError as e:
                last_error = e
                self._healthy = False
                self._error_message = f"Timeout after {timeout}s"
                self._failure_count += 1
                self._last_failure_time = datetime.utcnow()
                logger.warning(
                    f"{self.source.value}: Timeout on attempt {attempt + 1}/{max_retries}"
                )

            except Exception as e:
                last_error = e
                self._healthy = False
                self._error_message = str(e)
                self._failure_count += 1
                self._last_failure_time = datetime.utcnow()
                logger.warning(
                    f"{self.source.value}: Error on attempt {attempt + 1}/{max_retries}: {e}"
                )

            # Exponential backoff
            if attempt < max_retries - 1:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.info(f"{self.source.value}: Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)

        # All retries failed
        logger.error(f"{self.source.value}: All {max_retries} retries failed")
        return []

    def _handle_rate_limit(self):
        """Handle rate limit by setting cooldown."""
        # Use source-specific cooldown if available
        cooldown = getattr(settings, f"{self.source.value}_429_cooldown_s", 180)
        self._429_cooldown_until = time.time() + cooldown
        self._healthy = False
        self._error_message = f"Rate limited, cooldown until {self._429_cooldown_until}"

    def get_status(self) -> SourceStatus:
        """Get the current status of the adapter."""
        return SourceStatus(
            source=self.source,
            healthy=self._healthy,
            last_update=self._last_update,
            error_message=self._error_message,
            entity_count=self._entity_count,
            latency_ms=self._latency_ms,
        )
