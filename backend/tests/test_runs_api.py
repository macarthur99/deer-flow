"""Tests for runs API endpoints."""
import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.gateway.app import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def mock_checkpointer():
    """Mock checkpointer."""
    checkpointer = MagicMock()
    checkpointer.get.return_value = {
        "channel_values": {
            "messages": [],
            "title": "Test Thread"
        }
    }
    return checkpointer


def test_stream_run_missing_messages(client):
    """Test stream endpoint with missing messages."""
    response = client.post(
        "/api/threads/test-thread/runs/stream",
        json={"input": {}}
    )
    assert response.status_code == 400
    assert "No messages" in response.json()["detail"]


def test_stream_run_empty_content(client):
    """Test stream endpoint with empty message content."""
    response = client.post(
        "/api/threads/test-thread/runs/stream",
        json={"input": {"messages": [{"content": ""}]}}
    )
    assert response.status_code == 400
    assert "Empty message" in response.json()["detail"]


def test_get_history_no_checkpointer(client):
    """Test history endpoint without checkpointer."""
    response = client.get("/api/threads/test-thread/history")
    assert response.status_code == 503


def test_get_history_thread_not_found(client, mock_checkpointer):
    """Test history endpoint with non-existent thread."""
    mock_checkpointer.get.return_value = None
    client.app.state.checkpointer = mock_checkpointer

    response = client.get("/api/threads/test-thread/history")
    assert response.status_code == 404


def test_get_history_success(client, mock_checkpointer):
    """Test successful history retrieval."""
    client.app.state.checkpointer = mock_checkpointer

    response = client.get("/api/threads/test-thread/history")
    assert response.status_code == 200
    data = response.json()
    assert data["thread_id"] == "test-thread"
    assert data["title"] == "Test Thread"
    assert isinstance(data["messages"], list)
