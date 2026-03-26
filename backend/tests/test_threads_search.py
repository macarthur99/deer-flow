import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.gateway.routers.runs import search_threads, _extract_value, ThreadSearchRequest


class TestExtractValue:
    """Test the _extract_value helper function."""

    def test_simple_path(self):
        data = {"values": {"title": "Test Title"}}
        assert _extract_value(data, "values.title") == "Test Title"

    def test_nested_path(self):
        data = {"values": {"messages": [{"content": "Hello"}]}}
        assert _extract_value(data, "values.messages.0.content") == "Hello"

    def test_negative_index(self):
        data = {"values": {"messages": ["a", "b", "c"]}}
        assert _extract_value(data, "values.messages.-1") == "c"

    def test_missing_path(self):
        data = {"values": {}}
        assert _extract_value(data, "values.missing") is None

    def test_invalid_index(self):
        data = {"values": {"messages": []}}
        assert _extract_value(data, "values.messages.0") is None


class TestSearchThreads:
    """Test the search_threads endpoint."""

    @pytest.mark.anyio
    async def test_no_checkpointer(self):
        """Test error when checkpointer is not available."""
        request = MagicMock()
        request.app.state.checkpointer = None
        body = ThreadSearchRequest(limit=10, offset=0)

        with pytest.raises(HTTPException) as exc:
            await search_threads(request, body)
        assert exc.value.status_code == 503

    @pytest.mark.anyio
    async def test_non_postgres_checkpointer(self):
        """Test error when checkpointer is not PostgreSQL."""
        request = MagicMock()
        request.app.state.checkpointer = MagicMock()
        body = ThreadSearchRequest(limit=10, offset=0)

        with pytest.raises(HTTPException) as exc:
            await search_threads(request, body)
        assert exc.value.status_code == 501

    @pytest.mark.anyio
    async def test_basic_search(self):
        """Test basic search without filters."""
        request = MagicMock()
        checkpointer = MagicMock()
        checkpointer.__class__.__name__ = "AsyncPostgresSaver"
        request.app.state.checkpointer = checkpointer

        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (
                "thread-1",
                b'{}',
                "json",
                {"created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-01T00:00:00Z"},
            )
        ]
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        checkpointer.conn.cursor.return_value = cursor

        body = ThreadSearchRequest(limit=10, offset=0)

        # Mock the import and isinstance check
        mock_postgres_module = MagicMock()
        mock_postgres_saver = MagicMock()
        mock_postgres_module.AsyncPostgresSaver = mock_postgres_saver

        with patch.dict("sys.modules", {"langgraph.checkpoint.postgres": MagicMock(), "langgraph.checkpoint.postgres.aio": mock_postgres_module}):
            with patch("app.gateway.routers.runs.isinstance", return_value=True):
                with patch("langgraph.checkpoint.serde.jsonplus.JsonPlusSerializer") as mock_serde:
                    mock_serde_instance = MagicMock()
                    mock_serde_instance.loads_typed.return_value = {"channel_values": {"title": "Test"}}
                    mock_serde.return_value = mock_serde_instance

                    results = await search_threads(request, body)

        assert len(results) == 1
        assert results[0]["thread_id"] == "thread-1"
        assert results[0]["status"] == "idle"

    @pytest.mark.anyio
    async def test_search_with_extract(self):
        """Test search with extract parameter."""
        request = MagicMock()
        checkpointer = MagicMock()
        checkpointer.__class__.__name__ = "AsyncPostgresSaver"
        request.app.state.checkpointer = checkpointer

        cursor = MagicMock()
        cursor.fetchall.return_value = [
            (
                "thread-1",
                b'{}',
                "json",
                {"created_at": "2024-01-01T00:00:00Z"},
            )
        ]
        cursor.__enter__ = MagicMock(return_value=cursor)
        cursor.__exit__ = MagicMock(return_value=False)
        checkpointer.conn.cursor.return_value = cursor

        body = ThreadSearchRequest(
            limit=10, offset=0, extract={"title": "values.title", "last_msg": "values.messages.-1.content"}
        )

        # Mock the import and isinstance check
        mock_postgres_module = MagicMock()
        mock_postgres_saver = MagicMock()
        mock_postgres_module.AsyncPostgresSaver = mock_postgres_saver

        with patch.dict("sys.modules", {"langgraph.checkpoint.postgres": MagicMock(), "langgraph.checkpoint.postgres.aio": mock_postgres_module}):
            with patch("app.gateway.routers.runs.isinstance", return_value=True):
                with patch("langgraph.checkpoint.serde.jsonplus.JsonPlusSerializer") as mock_serde:
                    mock_serde_instance = MagicMock()
                    mock_serde_instance.loads_typed.return_value = {
                        "channel_values": {"title": "Test", "messages": [{"content": "Hello"}]}
                    }
                    mock_serde.return_value = mock_serde_instance

                    results = await search_threads(request, body)

        assert len(results) == 1
        assert results[0]["extracted"]["title"] == "Test"
        assert results[0]["extracted"]["last_msg"] == "Hello"

