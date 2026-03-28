import pytest
from langchain_core.messages import AIMessage, HumanMessage

from deerflow.agents.middlewares.citation_middleware import CitationMiddleware


def test_extract_markdown_citations():
    """Test extracting URLs from markdown citation format."""
    middleware = CitationMiddleware()

    state = {
        "messages": [
            HumanMessage(content="test"),
            AIMessage(content="DeerFlow is great[citation:1](https://github.com/bytedance/deer-flow).")
        ],
        "citations": []
    }

    result = middleware.after_model(state, {})

    assert result == {"citations": ["https://github.com/bytedance/deer-flow"]}


def test_extract_multiple_citations():
    """Test extracting multiple URLs."""
    middleware = CitationMiddleware()

    state = {
        "messages": [
            AIMessage(content="Source A[citation:1](https://example.com) and B[citation:2](https://test.com).")
        ],
        "citations": []
    }

    result = middleware.after_model(state, {})

    assert len(result["citations"]) == 2
    assert "https://example.com" in result["citations"]
    assert "https://test.com" in result["citations"]


def test_deduplicate_citations():
    """Test that duplicate URLs are not added."""
    middleware = CitationMiddleware()

    state = {
        "messages": [
            AIMessage(content="Test[citation:1](https://example.com).")
        ],
        "citations": ["https://example.com"]
    }

    result = middleware.after_model(state, {})

    assert result == {}


def test_extract_plain_urls():
    """Test extracting plain URLs."""
    middleware = CitationMiddleware()

    state = {
        "messages": [
            AIMessage(content="See https://example.com for details.")
        ],
        "citations": []
    }

    result = middleware.after_model(state, {})

    assert result == {"citations": ["https://example.com"]}


def test_no_citations_in_message():
    """Test when message has no citations."""
    middleware = CitationMiddleware()

    state = {
        "messages": [
            AIMessage(content="Just plain text.")
        ],
        "citations": []
    }

    result = middleware.after_model(state, {})

    assert result == {}
