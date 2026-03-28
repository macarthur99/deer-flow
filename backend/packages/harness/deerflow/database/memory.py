"""Memory table definition for SQLAlchemy."""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Index, JSON, MetaData, String, Table, func

_metadata = MetaData()

user_memory_table = Table(
    "user_memory",
    _metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", String(64), nullable=False),
    Column("agent_name", String(128), nullable=True),
    Column("memory_data", JSON, nullable=False),
    Column("version", String(16), default="1.0", nullable=False),
    Column("last_updated", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    Index("idx_user_id", "user_id"),
    Index("idx_user_agent", "user_id", "agent_name", unique=True),
)


def create_memory_table_sync(engine):
    """Create user_memory table if not exists (sync version).

    Args:
        engine: SQLAlchemy sync engine
    """
    _metadata.create_all(engine)
    print("user_memory table ensured")


async def create_memory_table_async(engine):
    """Create user_memory table if not exists (async version).

    Args:
        engine: SQLAlchemy async engine
    """
    async with engine.begin() as conn:
        await conn.run_sync(_metadata.create_all)
    print("user_memory table ensured")
