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
    result = middleware.after_agent(state, {})

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
    result = middleware.after_agent(state, {})

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
    result = middleware.after_agent(state, {})

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
    result = middleware.after_agent(state, {})

    assert result["citations"] == ["https://example.com/old", "https://example.com/new"]
    assert "[citation:2](https://example.com/new)" in result["messages"][0].content


def test_tool_message_citations(middleware):
    """Test extraction and renumbering from ToolMessages."""
    state = {
        "messages": [
            ToolMessage(content="Result with [citation](https://example.com/tool).", tool_call_id="1")
        ]
    }
    result = middleware.after_agent(state, {})

    assert result["citations"] == ["https://example.com/tool"]
    assert "[citation:1](https://example.com/tool)" in result["messages"][0].content


def test_non_url_file_ids(middleware):
    """Test support for non-URL fileIds like doc-12345."""
    state = {
        "messages": [
            AIMessage(content="Internal doc [citation](doc-12345). External [citation](https://example.com).")
        ]
    }
    result = middleware.after_agent(state, {})

    assert result["citations"] == ["doc-12345", "https://example.com"]
    assert "[citation:1](doc-12345)" in result["messages"][0].content
    assert "[citation:2](https://example.com)" in result["messages"][0].content


def test_empty_state(middleware):
    """Test handling of empty state."""
    state = {"messages": []}
    result = middleware.after_agent(state, {})
    assert result == {}


def test_no_citations_in_messages(middleware):
    """Test messages without citations."""
    state = {
        "messages": [
            AIMessage(content="No citations here.")
        ]
    }
    result = middleware.after_agent(state, {})
    assert result == {}


def test_structured_content_citations(middleware):
    """Test citation extraction from structured AIMessage content."""
    state = {
        "messages": [
            AIMessage(content=[
                {"type": "text", "text": "First claim [citation](https://example.com/a)."},
                {"type": "text", "text": "Second claim [citation](https://example.com/b)."}
            ])
        ]
    }
    result = middleware.after_agent(state, {})

    assert result["citations"] == ["https://example.com/a", "https://example.com/b"]
    updated_content = result["messages"][0].content
    assert updated_content[0]["text"] == "First claim [citation:1](https://example.com/a)."
    assert updated_content[1]["text"] == "Second claim [citation:2](https://example.com/b)."


def test_structured_content_with_non_text_blocks(middleware):
    """Test structured content with mixed block types."""
    state = {
        "messages": [
            AIMessage(content=[
                {"type": "text", "text": "Text with [citation](https://example.com)."},
                {"type": "image", "source": "data:image/png;base64,..."}
            ])
        ]
    }
    result = middleware.after_agent(state, {})

    assert result["citations"] == ["https://example.com"]
    updated_content = result["messages"][0].content
    assert updated_content[0]["text"] == "Text with [citation:1](https://example.com)."
    assert updated_content[1]["type"] == "image"


def test_existing_citation_only(middleware):
    """Test when message only contains existing citations (no new ones)."""
    state = {
        "citations": ["https://example.com/report"],
        "messages": [
            AIMessage(content="数据显示[citation](https://example.com/report)。")
        ]
    }
    result = middleware.after_agent(state, {})

    # Should still update messages with numbers
    assert "messages" in result
    assert "[citation:1](https://example.com/report)" in result["messages"][0].content


def test_update_output_files_with_citations(middleware):
    """Test that output files are updated with numbered citations."""
    from unittest.mock import MagicMock, patch

    mock_sandbox = MagicMock()
    mock_sandbox.list_dir.return_value = [{"type": "file", "name": "article.md"}]
    mock_sandbox.read_file.return_value = "Content with [citation](file-123) and [citation](file-456)."
    mock_sandbox.write_file = MagicMock()

    mock_provider = MagicMock()
    mock_provider.get.return_value = mock_sandbox

    with patch('deerflow.agents.middlewares.citation_middleware.get_sandbox_provider', return_value=mock_provider):
        state = {
            "sandbox": {"sandbox_id": "test-sandbox"},
            "citations": [],
            "messages": [
                AIMessage(
                    content="I wrote the file with [citation](file-123) and [citation](file-456).",
                    tool_calls=[{
                        "id": "call_123",
                        "name": "write_file",
                        "args": {"path": "/mnt/user-data/outputs/article.md", "content": "..."}
                    }]
                )
            ]
        }

        middleware.after_agent(state, {})

        mock_sandbox.list_dir.assert_called_once_with("/mnt/user-data/outputs/")
        mock_sandbox.read_file.assert_called_once_with("/mnt/user-data/outputs/article.md")
        mock_sandbox.write_file.assert_called_once()

        written_content = mock_sandbox.write_file.call_args[0][1]
        assert "[citation:1](file-123)" in written_content
        assert "[citation:2](file-456)" in written_content
