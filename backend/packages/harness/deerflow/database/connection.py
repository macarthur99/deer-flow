"""Async and Sync SQLAlchemy engine singleton for TiDB/MySQL."""

import logging

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from deerflow.config.database_config import get_database_config

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_sync_engine: Engine | None = None


def get_async_engine() -> AsyncEngine | None:
    """Return the cached async engine, or None if no database URL is configured."""
    return _engine


def get_sync_engine() -> Engine | None:
    """Return the cached sync engine, or None if no database URL is configured.

    Used for synchronous operations like memory storage.
    """
    return _sync_engine


async def init_async_engine() -> AsyncEngine | None:
    """Initialize the async engine singleton from config.

    Returns None (and logs a warning) if no database URL is configured.
    """
    global _engine, _sync_engine
    if _engine is not None:
        return _engine

    config = get_database_config()
    if not config.url:
        logger.warning("No database.url configured — skipping database initialization. Running in-memory only.")
        return None

    # Create async engine
    _engine = create_async_engine(
        config.url,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_pre_ping=True,
    )

    # Create sync engine for synchronous operations (memory storage, etc.)
    # Convert mysql+aiomysql:// to mysql+pymysql://
    sync_url = config.url
    if "+aiomysql" in sync_url:
        sync_url = sync_url.replace("+aiomysql", "+pymysql")
    elif sync_url.startswith("mysql://"):
        sync_url = sync_url.replace("mysql://", "mysql+pymysql://", 1)
    # For TiDB or other databases, keep the URL as-is if no special handling needed

    _sync_engine = create_engine(
        sync_url,
        pool_size=config.pool_size,
        max_overflow=config.max_overflow,
        pool_pre_ping=True,
    )

    logger.info("Database engines initialized (async + sync): %s", config.url.split("@")[-1])



    return _engine


async def close_async_engine() -> None:
    """Dispose both engines on shutdown."""
    global _engine, _sync_engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None
