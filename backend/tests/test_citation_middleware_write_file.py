import re
from unittest.mock import MagicMock

import pytest

from deerflow.agents.middlewares.citation_middleware import CitationMiddleware


class MockToolCallRequest:
    """Mock ToolCallRequest for testing."""

    def __init__(self, tool_name: str, args: dict, handler=None):
        self.tool_call = {"name": tool_name, "args": args}
        self.handler = handler or (lambda req: MagicMock())


class MockRuntime:
    """Mock Runtime for testing."""

    def __init__(self, state: dict):
        self.state = state


def test_wrap_tool_call_basic():
    """Test basic citation processing in write_file."""
    middleware = CitationMiddleware()
    state = {"citations": []}
    runtime = MockRuntime(state)

    content = "参考 [citation](doc1.pdf)"
    request = MockToolCallRequest("write_file", {"content": content})

    middleware.wrap_tool_call(request, runtime)

    assert state["citations"] == ["doc1.pdf"]
    assert request.tool_call["args"]["content"] == "参考 [citation:1](doc1.pdf)"


def test_wrap_tool_call_deduplication():
    """Test citation deduplication."""
    middleware = CitationMiddleware()
    state = {"citations": ["doc1.pdf"]}
    runtime = MockRuntime(state)

    content = "参考 [citation](doc1.pdf) 和 [citation](doc2.pdf)"
    request = MockToolCallRequest("write_file", {"content": content})

    middleware.wrap_tool_call(request, runtime)

    assert state["citations"] == ["doc1.pdf", "doc2.pdf"]
    assert request.tool_call["args"]["content"] == "参考 [citation:1](doc1.pdf) 和 [citation:2](doc2.pdf)"


def test_wrap_tool_call_reordering():
    """Test citation reordering."""
    middleware = CitationMiddleware()
    state = {"citations": ["doc1.pdf", "doc2.pdf"]}
    runtime = MockRuntime(state)

    content = "参考 [citation](doc3.pdf) 和 [citation](doc1.pdf)"
    request = MockToolCallRequest("write_file", {"content": content})

    middleware.wrap_tool_call(request, runtime)

    assert state["citations"] == ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    assert request.tool_call["args"]["content"] == "参考 [citation:3](doc3.pdf) 和 [citation:1](doc1.pdf)"


def test_wrap_tool_call_non_write_file_tool():
    """Test that non-write_file tools are not intercepted."""
    middleware = CitationMiddleware()
    state = {"citations": []}
    runtime = MockRuntime(state)

    content = "参考 [citation](doc1.pdf)"
    request = MockToolCallRequest("read_file", {"path": "/test.md"})
    original_args = request.tool_call["args"].copy()

    middleware.wrap_tool_call(request, runtime)

    assert state["citations"] == []
    assert request.tool_call["args"] == original_args


def test_wrap_tool_call_empty_content():
    """Test handling of empty content."""
    middleware = CitationMiddleware()
    state = {"citations": []}
    runtime = MockRuntime(state)

    request = MockToolCallRequest("write_file", {"content": ""})

    middleware.wrap_tool_call(request, runtime)

    assert state["citations"] == []
    assert request.tool_call["args"]["content"] == ""


def test_wrap_tool_call_no_citations():
    """Test content without citations."""
    middleware = CitationMiddleware()
    state = {"citations": []}
    runtime = MockRuntime(state)

    content = "这是普通文本，没有引用"
    request = MockToolCallRequest("write_file", {"content": content})

    middleware.wrap_tool_call(request, runtime)

    assert state["citations"] == []
    assert request.tool_call["args"]["content"] == content


def test_wrap_tool_call_already_numbered():
    """Test handling of already numbered citations."""
    middleware = CitationMiddleware()
    state = {"citations": ["doc1.pdf"]}
    runtime = MockRuntime(state)

    content = "参考 [citation:1](doc1.pdf) 和 [citation](doc2.pdf)"
    request = MockToolCallRequest("write_file", {"content": content})

    middleware.wrap_tool_call(request, runtime)

    assert state["citations"] == ["doc1.pdf", "doc2.pdf"]
    assert request.tool_call["args"]["content"] == "参考 [citation:1](doc1.pdf) 和 [citation:2](doc2.pdf)"


