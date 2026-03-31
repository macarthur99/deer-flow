"""MySQL-based memory storage implementation."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text, func
from sqlalchemy.dialects.mysql import insert as mysql_insert

from deerflow.agents.memory.storage import MemoryStorage, create_empty_memory
from deerflow.config.agents_config import AGENT_NAME_PATTERN
from deerflow.database.connection import get_sync_engine
from deerflow.database.memory import user_memory_table

logger = logging.getLogger(__name__)


class MySQLMemoryStorage(MemoryStorage):
    """MySQL-based memory storage provider."""

    def __init__(self):
        """Initialize the MySQL memory storage."""
        self._cache: dict[tuple[str, str | None], tuple[dict[str, Any], datetime | None]] = {}

    def _validate_user_id(self, user_id: str) -> None:
        """Validate that the user_id is safe to use."""
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")
        if not 1 <= len(user_id) <= 64:
            raise ValueError("user_id must be 1-64 characters")
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", user_id):
            raise ValueError("user_id must contain only alphanumeric, underscore, or dash characters")

    def _validate_agent_name(self, agent_name: str) -> None:
        """Validate that the agent name is safe to use."""
        if not agent_name:
            raise ValueError("Agent name must be a non-empty string.")
        if not AGENT_NAME_PATTERN.match(agent_name):
            raise ValueError(f"Invalid agent name {agent_name!r}: names must match {AGENT_NAME_PATTERN.pattern}")

    def _get_engine(self):
        """Get the sync database engine."""
        return get_sync_engine()

    def load(self, user_id: str, agent_name: str | None = None) -> dict[str, Any]:
        """Load memory data from database."""
        self._validate_user_id(user_id)
        agent_name = agent_name or ""
        if agent_name:
            self._validate_agent_name(agent_name)

        engine = self._get_engine()
        if engine is None:
            return create_empty_memory()

        cache_key = (user_id, agent_name)

        try:
            with engine.connect() as conn:
                stmt = select(
                    user_memory_table.c.memory_data,
                    user_memory_table.c.updated_at
                ).where(
                    user_memory_table.c.user_id == user_id,
                    user_memory_table.c.agent_name == agent_name
                )
                result = conn.execute(stmt).first()

                if result is None:
                    return create_empty_memory()

                memory_data, updated_at = result
                self._cache[cache_key] = (memory_data, updated_at)
                return memory_data
        except Exception as e:
            logger.error(f"Failed to load memory from database: {e}")
            cached = self._cache.get(cache_key)
            return cached[0] if cached else create_empty_memory()

    def reload(self, user_id: str, agent_name: str | None = None) -> dict[str, Any]:
        """Force reload memory data from database."""
        agent_name = agent_name or ""
        cache_key = (user_id, agent_name)
        if cache_key in self._cache:
            del self._cache[cache_key]
        return self.load(user_id, agent_name)

    def save(self, memory_data: dict[str, Any], user_id: str, agent_name: str | None = None) -> bool:
        """Save memory data to database."""
        self._validate_user_id(user_id)
        agent_name = agent_name or ""
        if agent_name:
            self._validate_agent_name(agent_name)

        engine = self._get_engine()
        if engine is None:
            return False

        try:
            last_updated_str = memory_data.get("lastUpdated", "")
            last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
        except Exception:
            last_updated = datetime.now(timezone.utc)

        try:
            with engine.begin() as conn:
                stmt = mysql_insert(user_memory_table).values(
                    user_id=user_id,
                    agent_name=agent_name,
                    memory_data=memory_data,
                    version=memory_data.get("version", "1.0"),
                    last_updated=last_updated
                )
                stmt = stmt.on_duplicate_key_update(
                    memory_data=stmt.inserted.memory_data,
                    version=stmt.inserted.version,
                    last_updated=stmt.inserted.last_updated
                )
                conn.execute(stmt)

            cache_key = (user_id, agent_name)
            self._cache[cache_key] = (memory_data, datetime.now(timezone.utc))
            logger.info(f"Memory saved to database for user_id={user_id}, agent_name={agent_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save memory to database: {e}")
            return False

    def cleanup_duplicates(self) -> int:
        """Remove duplicate records where agent_name is NULL, keeping the most recent."""
        engine = self._get_engine()
        if engine is None:
            return 0

        try:
            with engine.begin() as conn:
                # Find user_ids with multiple NULL agent_name records
                duplicates_query = text("""
                    SELECT user_id, COUNT(*) as cnt
                    FROM user_memory
                    WHERE agent_name IS NULL
                    GROUP BY user_id
                    HAVING cnt > 1
                """)
                duplicates = conn.execute(duplicates_query).fetchall()

                removed_count = 0
                for user_id, _ in duplicates:
                    # Keep most recent, delete others
                    delete_query = text("""
                        DELETE FROM user_memory
                        WHERE user_id = :user_id AND agent_name IS NULL
                        AND id NOT IN (
                            SELECT id FROM (
                                SELECT id FROM user_memory
                                WHERE user_id = :user_id AND agent_name IS NULL
                                ORDER BY updated_at DESC
                                LIMIT 1
                            ) AS keeper
                        )
                    """)
                    result = conn.execute(delete_query, {"user_id": user_id})
                    removed_count += result.rowcount

                logger.info(f"Cleaned up {removed_count} duplicate records")
                return removed_count
        except Exception as e:
            logger.error(f"Failed to cleanup duplicates: {e}")
            return 0
