"""Tests for MySQL memory storage."""

import pytest
from sqlalchemy import select, func

from deerflow.agents.memory.mysql_storage import MySQLMemoryStorage
from deerflow.database.memory import user_memory_table


@pytest.fixture
def storage():
    """Create a MySQL memory storage instance."""
    return MySQLMemoryStorage()


def test_agent_name_none_normalized_to_empty_string(storage):
    """Test that agent_name=None is normalized to empty string."""
    memory_data = {"test": "data", "version": "1.0", "lastUpdated": "2024-01-01T00:00:00Z"}

    # Save with None
    result = storage.save(memory_data, "test_user_1", agent_name=None)
    assert result is True

    # Verify database has empty string, not NULL
    engine = storage._get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            select(user_memory_table.c.agent_name).where(
                user_memory_table.c.user_id == "test_user_1"
            )
        ).scalar()
        assert result == ""  # Not NULL

    # Load with None should return the same data
    loaded = storage.load("test_user_1", agent_name=None)
    assert loaded["test"] == "data"


def test_no_duplicates_with_none_agent_name(storage):
    """Test that multiple saves with agent_name=None don't create duplicates."""
    # Save multiple times
    for i in range(5):
        storage.save({"version": str(i), "lastUpdated": "2024-01-01T00:00:00Z"}, "test_user_2", agent_name=None)

    # Verify only one record
    engine = storage._get_engine()
    with engine.connect() as conn:
        count = conn.execute(
            select(func.count()).where(
                user_memory_table.c.user_id == "test_user_2"
            )
        ).scalar()
        assert count == 1


def test_cleanup_duplicates_removes_null_duplicates(storage):
    """Test that cleanup_duplicates removes NULL duplicates."""
    engine = storage._get_engine()

    # Manually insert duplicate NULL records
    with engine.begin() as conn:
        for i in range(3):
            conn.execute(
                user_memory_table.insert().values(
                    user_id="test_user_3",
                    agent_name=None,
                    memory_data={"version": str(i)},
                    version="1.0"
                )
            )

    # Verify duplicates exist
    with engine.connect() as conn:
        count = conn.execute(
            select(func.count()).where(
                user_memory_table.c.user_id == "test_user_3"
            )
        ).scalar()
        assert count == 3

    # Run cleanup
    removed = storage.cleanup_duplicates()
    assert removed == 2

    # Verify only one record remains
    with engine.connect() as conn:
        count = conn.execute(
            select(func.count()).where(
                user_memory_table.c.user_id == "test_user_3"
            )
        ).scalar()
        assert count == 1
