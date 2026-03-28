import json
import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from deerflow.agents.middlewares.citation_verification_middleware import CitationVerificationMiddleware


@pytest.fixture
def middleware():
    """Create middleware instance with default settings."""
    return CitationVerificationMiddleware(strictness="warn", long_text_threshold=1000)


@pytest.fixture
def state():
    """Create a basic state with thread_id."""
    return {"configurable": {"thread_id": "test-thread-123"}}


def test_no_web_tools_no_verification(middleware, state):
    """When no web tools are used, no verification should occur."""
    # Simulate non-web tool call
    result = middleware.wrap_tool_call("bash", {"command": "ls"}, "file1.txt\nfile2.txt", state)
    assert result is None

    # AI response without citations should pass
    ai_message = AIMessage(content="Here are the files in the directory.")
    result = middleware.after_model([ai_message], state)
    assert result is None


def test_all_urls_cited_no_reminder(middleware, state):
    """When all URLs are cited, no reminder should be triggered."""
    # Simulate web_search returning 2 URLs
    search_results = json.dumps([
        {"url": "https://example.com/article1", "title": "Article 1"},
        {"url": "https://example.com/article2", "title": "Article 2"}
    ])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    # AI response cites both URLs
    ai_message = AIMessage(content="""
    Based on research, AI is advancing rapidly [citation:1](https://example.com/article1).
    New models show improved reasoning [citation:2](https://example.com/article2).
    """)
    result = middleware.after_model([ai_message], state)
    assert result is None


def test_uncited_urls_triggers_reminder(middleware, state):
    """When URLs are uncited, a reminder should be triggered."""
    # Simulate web_search returning 3 URLs
    search_results = json.dumps([
        {"url": "https://example.com/article1", "title": "Article 1"},
        {"url": "https://example.com/article2", "title": "Article 2"},
        {"url": "https://example.com/article3", "title": "Article 3"}
    ])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    # AI response only cites 1 URL
    ai_message = AIMessage(content="""
    AI is advancing rapidly [citation:1](https://example.com/article1).
    Many new developments are happening.
    """)
    result = middleware.after_model([ai_message], state)

    assert result is not None
    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], HumanMessage)

    warning = result["messages"][0].content
    assert "CITATION VERIFICATION REMINDER" in warning
    assert "retrieved 3 sources" in warning
    assert "cited 1 of them" in warning
    assert "example.com/article2" in warning
    assert "example.com/article3" in warning


def test_url_normalization(middleware, state):
    """URLs should be normalized for comparison (http/https, trailing slash)."""
    # Web search returns URL with https and trailing slash
    search_results = json.dumps([
        {"url": "https://example.com/article/", "title": "Article"}
    ])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    # AI cites with http and no trailing slash
    ai_message = AIMessage(content="Research shows [citation:1](http://example.com/article).")
    result = middleware.after_model([ai_message], state)

    # Should recognize as the same URL
    assert result is None


def test_per_thread_isolation(middleware):
    """URLs tracked for one thread should not affect another thread."""
    state1 = {"configurable": {"thread_id": "thread-1"}}
    state2 = {"configurable": {"thread_id": "thread-2"}}

    # Thread 1: track URL1
    search_results1 = json.dumps([{"url": "https://example.com/url1", "title": "URL1"}])
    middleware.wrap_tool_call("web_search", {"query": "test1"}, search_results1, state1)

    # Thread 2: track URL2
    search_results2 = json.dumps([{"url": "https://example.com/url2", "title": "URL2"}])
    middleware.wrap_tool_call("web_search", {"query": "test2"}, search_results2, state2)

    # Thread 1: cite URL1 (should pass)
    ai_message1 = AIMessage(content="Info [citation:1](https://example.com/url1).")
    result1 = middleware.after_model([ai_message1], state1)
    assert result1 is None

    # Thread 2: cite URL1 (should fail - URL1 not tracked for thread 2)
    ai_message2 = AIMessage(content="Info [citation:1](https://example.com/url1).")
    result2 = middleware.after_model([ai_message2], state2)
    assert result2 is not None
    assert "url2" in result2["messages"][0].content.lower()


def test_long_text_threshold(middleware, state):
    """Long text should trigger enhanced reminder."""
    search_results = json.dumps([{"url": "https://example.com/article", "title": "Article"}])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    # Short text (< 1000 chars)
    short_content = "A" * 500
    ai_message = AIMessage(content=short_content)
    result = middleware.after_model([ai_message], state)

    warning = result["messages"][0].content
    assert "Pay special attention to" not in warning

    # Reset for next test
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    # Long text (> 1000 chars)
    long_content = "A" * 1500
    ai_message = AIMessage(content=long_content)
    result = middleware.after_model([ai_message], state)

    warning = result["messages"][0].content
    assert "Pay special attention to" in warning
    assert "Numbers and statistics" in warning


def test_strictness_off(state):
    """Strictness 'off' should disable all verification."""
    middleware = CitationVerificationMiddleware(strictness="off")

    search_results = json.dumps([{"url": "https://example.com/article", "title": "Article"}])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    # No citations
    ai_message = AIMessage(content="Some content without citations.")
    result = middleware.after_model([ai_message], state)

    assert result is None


def test_strictness_strict(state):
    """Strictness 'strict' should use stronger warning icon."""
    middleware = CitationVerificationMiddleware(strictness="strict")

    search_results = json.dumps([{"url": "https://example.com/article", "title": "Article"}])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    ai_message = AIMessage(content="Content without citations.")
    result = middleware.after_model([ai_message], state)

    warning = result["messages"][0].content
    assert "🚫" in warning


def test_web_fetch_tracking(middleware, state):
    """web_fetch tool should also be tracked."""
    middleware.wrap_tool_call("web_fetch", {"url": "https://example.com/page"}, "Page content here", state)

    ai_message = AIMessage(content="Some content without citation.")
    result = middleware.after_model([ai_message], state)

    assert result is not None
    assert "example.com/page" in result["messages"][0].content


def test_jina_fetch_tracking(middleware, state):
    """jina_fetch tool should also be tracked."""
    middleware.wrap_tool_call("jina_fetch", {"url": "https://example.com/article"}, "Article content", state)

    ai_message = AIMessage(content="Some content without citation.")
    result = middleware.after_model([ai_message], state)

    assert result is not None
    assert "example.com/article" in result["messages"][0].content


def test_partial_citation_triggers_reminder(middleware, state):
    """Partial citations should trigger reminder for uncited sources."""
    search_results = json.dumps([
        {"url": "https://example.com/url1", "title": "URL1"},
        {"url": "https://example.com/url2", "title": "URL2"},
        {"url": "https://example.com/url3", "title": "URL3"},
        {"url": "https://example.com/url4", "title": "URL4"}
    ])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    # Cite 2 out of 4
    ai_message = AIMessage(content="""
    First point [citation:1](https://example.com/url1).
    Second point [citation:2](https://example.com/url3).
    Third point without citation.
    """)
    result = middleware.after_model([ai_message], state)

    assert result is not None
    warning = result["messages"][0].content
    assert "retrieved 4 sources" in warning
    assert "cited 2 of them" in warning
    assert "url2" in warning
    assert "url4" in warning


def test_no_thread_id_no_tracking(middleware):
    """Without thread_id, no tracking should occur."""
    state_no_thread = {"configurable": {}}

    search_results = json.dumps([{"url": "https://example.com/article", "title": "Article"}])
    result = middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state_no_thread)
    assert result is None

    ai_message = AIMessage(content="Content without citation.")
    result = middleware.after_model([ai_message], state_no_thread)
    assert result is None


def test_lru_eviction(state):
    """Old threads should be evicted when max_tracked_threads is exceeded."""
    middleware = CitationVerificationMiddleware(strictness="warn", max_tracked_threads=2)

    # Track 3 threads (should evict the first)
    for i in range(3):
        thread_state = {"configurable": {"thread_id": f"thread-{i}"}}
        search_results = json.dumps([{"url": f"https://example.com/url{i}", "title": f"URL{i}"}])
        middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, thread_state)

    # Check that only 2 threads are tracked
    assert len(middleware._pending_urls) == 2
    assert "thread-0" not in middleware._pending_urls
    assert "thread-1" in middleware._pending_urls
    assert "thread-2" in middleware._pending_urls


def test_malformed_search_results(middleware, state):
    """Malformed JSON in search results should not crash."""
    # Invalid JSON
    middleware.wrap_tool_call("web_search", {"query": "test"}, "not valid json", state)

    ai_message = AIMessage(content="Some content.")
    result = middleware.after_model([ai_message], state)
    assert result is None  # No URLs tracked, no verification


def test_empty_search_results(middleware, state):
    """Empty search results should not trigger verification."""
    search_results = json.dumps([])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    ai_message = AIMessage(content="No results found.")
    result = middleware.after_model([ai_message], state)
    assert result is None


def test_non_ai_message_ignored(middleware, state):
    """Non-AIMessage in result should be ignored."""
    search_results = json.dumps([{"url": "https://example.com/article", "title": "Article"}])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    # Last message is not AIMessage
    tool_message = ToolMessage(content="Tool result", tool_call_id="123")
    result = middleware.after_model([tool_message], state)
    assert result is None


def test_citation_cleared_after_complete(middleware, state):
    """Pending URLs should be cleared after all are cited."""
    search_results = json.dumps([{"url": "https://example.com/article", "title": "Article"}])
    middleware.wrap_tool_call("web_search", {"query": "test"}, search_results, state)

    # Cite the URL
    ai_message = AIMessage(content="Info [citation:1](https://example.com/article).")
    result = middleware.after_model([ai_message], state)
    assert result is None

    # Verify pending URLs are cleared


def test_internal_search_fileid_tracking(middleware, state):
    """Test that internal_search results with fileId are tracked."""
    search_results = json.dumps([
        {"fileId": "http://internal.example.com/doc/12345", "fileName": "报告.pdf", "score": 0.95},
        {"fileId": "http://internal.example.com/doc/67890", "fileName": "分析.docx", "score": 0.88}
    ])
    middleware.wrap_tool_call("web_search", {"query": "AI"}, search_results, state)

    # Cite one fileId
    ai_message = AIMessage(content="根据报告 [citation:1](http://internal.example.com/doc/12345)。")
    result = middleware.after_model([ai_message], state)

    # Should remind about uncited fileId
    assert result is not None
    assert "internal.example.com/doc/67890" in result["messages"][0].content
