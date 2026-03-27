"""Memory table definition for SQLAlchemy."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, JSON, MetaData, String, Table

_metadata = MetaData()

user_memory_table = Table(
    "user_memory",
    _metadata,
    Column("user_id", String(255), primary_key=True),
    Column("memory_data", JSON, nullable=False),
    Column("version", String(10), default="1.0"),
    Column("updated_at", DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)),
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
