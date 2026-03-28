"""Resilient checkpointer wrapper with automatic retry on connection failures.

Wraps any async checkpointer to automatically retry operations when PostgreSQL
connections are lost due to network issues, database restarts, or idle timeouts.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class ResilientCheckpointer:
    """Wraps a checkpointer with retry logic for transient connection failures.

    Retries checkpoint operations on psycopg OperationalError and DatabaseError
    with exponential backoff. Logs only on final failure or successful recovery.
    """

    MAX_ATTEMPTS = 3
    BACKOFF_BASE = 1  # seconds

    def __init__(self, checkpointer: Any) -> None:
        """Initialize with underlying checkpointer.

        Args:
            checkpointer: The checkpointer to wrap (e.g., AsyncPostgresSaver)
        """
        self._checkpointer = checkpointer

    async def _retry(self, operation, *args, **kwargs):
        """Execute operation with exponential backoff retry.

        Args:
            operation: Async callable to execute
            *args: Positional arguments for operation
            **kwargs: Keyword arguments for operation

        Returns:
            Result from operation

        Raises:
            Last exception if all retries exhausted
        """
        last_error = None
        first_attempt = True

        for attempt in range(self.MAX_ATTEMPTS):
            try:
                result = await operation(*args, **kwargs)
                # Log recovery only if we had previous failures
                if not first_attempt:
                    logger.info("Checkpoint operation recovered after %d attempt(s)", attempt + 1)
                return result
            except Exception as e:
                # Check if it's a retryable psycopg error
                error_type = type(e).__name__
                if "OperationalError" not in error_type and "DatabaseError" not in error_type:
                    # Not a connection error, don't retry
                    raise

                last_error = e
                first_attempt = False

                if attempt < self.MAX_ATTEMPTS - 1:
                    wait_time = self.BACKOFF_BASE * (2**attempt)
                    await asyncio.sleep(wait_time)

        # All retries exhausted
        logger.error("Checkpoint operation failed after %d attempts: %s", self.MAX_ATTEMPTS, last_error)
        raise last_error

    async def aget_tuple(self, config):
        """Get checkpoint tuple with retry."""
        return await self._retry(self._checkpointer.aget_tuple, config)

    async def aput(self, config, checkpoint, metadata, new_channels):
        """Put checkpoint with retry."""
        return await self._retry(self._checkpointer.aput, config, checkpoint, metadata, new_channels)

    async def alist(self, config, *, limit=None, before=None):
        """List checkpoints with retry."""
        return self._checkpointer.alist(config, limit=limit, before=before)

    async def adelete(self, config):
        """Delete checkpoint with retry."""
        return await self._retry(self._checkpointer.adelete, config)

    def __getattr__(self, name):
        """Delegate other attributes to underlying checkpointer."""
        return getattr(self._checkpointer, name)
