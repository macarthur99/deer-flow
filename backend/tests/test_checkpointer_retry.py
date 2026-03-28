"""Tests for resilient checkpointer retry logic."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest

from deerflow.agents.checkpointer.resilient_checkpointer import ResilientCheckpointer

pytestmark = pytest.mark.anyio


class MockOperationalError(Exception):
    """Mock psycopg OperationalError."""

    pass


class MockDatabaseError(Exception):
    """Mock psycopg DatabaseError."""

    pass


@pytest.fixture
def mock_checkpointer():
    """Create a mock checkpointer."""
    checkpointer = Mock()
    checkpointer.aget_tuple = AsyncMock()
    checkpointer.aput = AsyncMock()
    checkpointer.alist = Mock()
    checkpointer.adelete = AsyncMock()
    return checkpointer


async def test_success_on_first_attempt(mock_checkpointer):
    """Test that successful operations don't retry."""
    mock_checkpointer.aget_tuple.return_value = {"test": "data"}

    resilient = ResilientCheckpointer(mock_checkpointer)
    result = await resilient.aget_tuple({"thread_id": "test"})

    assert result == {"test": "data"}
    assert mock_checkpointer.aget_tuple.call_count == 1


async def test_retry_on_operational_error(mock_checkpointer):
    """Test retry on OperationalError."""
    mock_checkpointer.aget_tuple.side_effect = [
        MockOperationalError("Connection lost"),
        {"test": "data"},
    ]

    resilient = ResilientCheckpointer(mock_checkpointer)
    result = await resilient.aget_tuple({"thread_id": "test"})

    assert result == {"test": "data"}
    assert mock_checkpointer.aget_tuple.call_count == 2


async def test_retry_on_database_error(mock_checkpointer):
    """Test retry on DatabaseError."""
    mock_checkpointer.aput.side_effect = [
        MockDatabaseError("Transaction failed"),
        {"checkpoint_id": "123"},
    ]

    resilient = ResilientCheckpointer(mock_checkpointer)
    result = await resilient.aput({}, {}, {}, {})

    assert result == {"checkpoint_id": "123"}
    assert mock_checkpointer.aput.call_count == 2


async def test_max_retries_exhausted(mock_checkpointer):
    """Test that operation fails after max retries."""
    mock_checkpointer.aget_tuple.side_effect = MockOperationalError("Connection lost")

    resilient = ResilientCheckpointer(mock_checkpointer)

    with pytest.raises(MockOperationalError):
        await resilient.aget_tuple({"thread_id": "test"})

    assert mock_checkpointer.aget_tuple.call_count == 3


async def test_no_retry_on_non_connection_error(mock_checkpointer):
    """Test that non-connection errors are not retried."""
    mock_checkpointer.aget_tuple.side_effect = ValueError("Invalid config")

    resilient = ResilientCheckpointer(mock_checkpointer)

    with pytest.raises(ValueError):
        await resilient.aget_tuple({"thread_id": "test"})

    assert mock_checkpointer.aget_tuple.call_count == 1


async def test_exponential_backoff_timing(mock_checkpointer):
    """Test exponential backoff timing."""
    mock_checkpointer.aget_tuple.side_effect = [
        MockOperationalError("Connection lost"),
        MockOperationalError("Connection lost"),
        {"test": "data"},
    ]

    resilient = ResilientCheckpointer(mock_checkpointer)

    import time
    start = time.time()
    result = await resilient.aget_tuple({"thread_id": "test"})
    elapsed = time.time() - start

    assert result == {"test": "data"}
    assert mock_checkpointer.aget_tuple.call_count == 3
    # Should wait 1s + 2s = 3s total (with some tolerance)
    assert 2.5 < elapsed < 3.5


async def test_adelete_with_retry(mock_checkpointer):
    """Test adelete operation with retry."""
    mock_checkpointer.adelete.side_effect = [
        MockOperationalError("Connection lost"),
        None,
    ]

    resilient = ResilientCheckpointer(mock_checkpointer)
    await resilient.adelete({"thread_id": "test"})

    assert mock_checkpointer.adelete.call_count == 2


def test_attribute_delegation(mock_checkpointer):
    """Test that other attributes are delegated to underlying checkpointer."""
    mock_checkpointer.some_attribute = "test_value"

    resilient = ResilientCheckpointer(mock_checkpointer)

    assert resilient.some_attribute == "test_value"

