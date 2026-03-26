"""Thread-user ownership table: bind thread_id → user_id in TiDB."""

import logging
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Table, MetaData, select, delete
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)

_metadata = MetaData()

thread_users_table = Table(
    "thread_users",
    _metadata,
    Column("thread_id", String(255), primary_key=True),
    Column("user_id", String(255), nullable=False, index=True),
    Column("created_at", DateTime, nullable=False),
)


async def create_table(engine: AsyncEngine) -> None:
    """Create the thread_users table if it does not exist."""
    async with engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    logger.info("thread_users table ensured")


async def bind_thread_user(engine: AsyncEngine, thread_id: str, user_id: str) -> None:
    """Insert a thread_id → user_id binding (upsert by replacing)."""
    async with engine.begin() as conn:
        # Use INSERT ... ON DUPLICATE KEY UPDATE for idempotency
        from sqlalchemy.dialects.mysql import insert as mysql_insert

        stmt = mysql_insert(thread_users_table).values(
            thread_id=thread_id,
            user_id=str(user_id),
            created_at=datetime.now(timezone.utc),
        )
        stmt = stmt.on_duplicate_key_update(user_id=stmt.inserted.user_id)
        await conn.execute(stmt)
    logger.debug("Bound thread %s to user %s", thread_id, user_id)


async def get_user_for_thread(engine: AsyncEngine, thread_id: str) -> str | None:
    """Return the user_id that owns thread_id, or None if not found."""
    async with engine.connect() as conn:
        result = await conn.execute(select(thread_users_table.c.user_id).where(thread_users_table.c.thread_id == thread_id))
        row = result.fetchone()
        return row[0] if row else None


async def list_threads_for_user(engine: AsyncEngine, user_id: str) -> list[str]:
    """Return all thread_ids owned by user_id."""
    async with engine.connect() as conn:
        result = await conn.execute(select(thread_users_table.c.thread_id).where(thread_users_table.c.user_id == str(user_id)))
        return [row[0] for row in result.fetchall()]


async def delete_thread_user(engine: AsyncEngine, thread_id: str) -> None:
    """Remove the thread_id → user_id binding."""
    async with engine.begin() as conn:
        await conn.execute(delete(thread_users_table).where(thread_users_table.c.thread_id == thread_id))
    logger.debug("Deleted thread-user binding for thread %s", thread_id)
