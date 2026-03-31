import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from deerflow.agents.middlewares.citation_middleware import CitationMiddleware


@pytest.fixture
def middleware():
    return CitationMiddleware()


def test_extract_unnumbered_citations(middleware):
    """Test extraction of unnumbered [citation](fileId) format."""
    state = {
        "messages": [
            AIMessage(content="Claim one [citation](https://example.com/a). Claim two [citation](https://example.com/b).")
        ]
    }
    result = middleware.after_model(state, {})

    assert result["citations"] == ["https://example.com/a", "https://example.com/b"]
    assert "[citation:1](https://example.com/a)" in result["messages"][0].content
    assert "[citation:2](https://example.com/b)" in result["messages"][0].content


def test_extract_numbered_citations_backward_compat(middleware):
    """Test backward compatibility with [citation:N](fileId) format."""
    state = {
        "messages": [
            AIMessage(content="Claim [citation:1](https://example.com/a).")
        ]
    }
    result = middleware.after_model(state, {})

    assert result["citations"] == ["https://example.com/a"]
    assert "[citation:1](https://example.com/a)" in result["messages"][0].content


def test_deduplication_across_messages(middleware):
    """Test global deduplication across multiple messages."""
    state = {
        "messages": [
            AIMessage(content="First [citation](https://example.com/a)."),
            AIMessage(content="Second [citation](https://example.com/b)."),
            AIMessage(content="Repeat [citation](https://example.com/a).")
        ]
    }
    result = middleware.after_model(state, {})

    assert result["citations"] == ["https://example.com/a", "https://example.com/b"]
    assert "[citation:1](https://example.com/a)" in result["messages"][0].content
    assert "[citation:2](https://example.com/b)" in result["messages"][1].content
    assert "[citation:1](https://example.com/a)" in result["messages"][2].content


def test_renumbering_with_existing_citations(middleware):
    """Test renumbering when existing citations are present."""
    state = {
        "citations": ["https://example.com/old"],
        "messages": [
            AIMessage(content="New claim [citation](https://example.com/new).")
        ]
    }
    result = middleware.after_model(state, {})

    assert result["citations"] == ["https://example.com/new"]
    assert "[citation:2](https://example.com/new)" in result["messages"][0].content


def test_tool_message_citations(middleware):
    """Test extraction and renumbering from ToolMessages."""
    state = {
        "messages": [
            ToolMessage(content="Result with [citation](https://example.com/tool).", tool_call_id="1")
        ]
    }
    result = middleware.after_model(state, {})

    assert result["citations"] == ["https://example.com/tool"]
    assert "[citation:1](https://example.com/tool)" in result["messages"][0].content


def test_non_url_file_ids(middleware):
    """Test support for non-URL fileIds like doc-12345."""
    state = {
        "messages": [
            AIMessage(content="Internal doc [citation](doc-12345). External [citation](https://example.com).")
        ]
    }
    result = middleware.after_model(state, {})

    assert result["citations"] == ["doc-12345", "https://example.com"]
    assert "[citation:1](doc-12345)" in result["messages"][0].content
    assert "[citation:2](https://example.com)" in result["messages"][0].content


def test_before_model_injection(middleware):
    """Test citation list injection into system prompt."""
    state = {
        "citations": ["https://example.com/a", "https://example.com/b"],
        "messages": [
            HumanMessage(content="System prompt")
        ]
    }
    result = middleware.before_model(state, {})

    # before_model modifies messages in place, check state
    assert "[1] https://example.com/a" in state["messages"][0].content
    assert "[2] https://example.com/b" in state["messages"][0].content


def test_empty_state(middleware):
    """Test handling of empty state."""
    state = {"messages": []}
    result = middleware.after_model(state, {})
    assert result == {}


def test_no_citations_in_messages(middleware):
    """Test messages without citations."""
    state = {
        "messages": [
            AIMessage(content="No citations here.")
        ]
    }
    result = middleware.after_model(state, {})
    assert result == {}
