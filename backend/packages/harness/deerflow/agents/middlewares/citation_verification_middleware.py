import json
import re
import threading
from collections import OrderedDict
from typing import Any, Awaitable, Callable, Literal
from urllib.parse import urlparse

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Command


class CitationVerificationMiddleware(AgentMiddleware):
    """Middleware to verify citation completeness in AI responses.

    Tracks URLs from web_search/web_fetch tools and verifies they are cited
    in the AI's response using [citation:N](URL) format.
    """

    CITATION_PATTERN = re.compile(r'\[citation:\[\d+\]\]\(([^)]+)\)')

    def __init__(
        self,
        strictness: Literal["off", "warn", "strict"] = "warn",
        long_text_threshold: int = 1000,
        tracked_tools: list[str] | None = None,
        max_tracked_threads: int = 100,
    ):
        super().__init__()
        self.strictness = strictness
        self.long_text_threshold = long_text_threshold
        self.tracked_tools = tracked_tools or ["web_search", "web_fetch", "jina_fetch"]
        self.max_tracked_threads = max_tracked_threads

        # Thread-safe storage: thread_id -> set of URLs
        self._pending_urls: OrderedDict[str, set[str]] = OrderedDict()
        self._lock = threading.Lock()

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison (lowercase, remove trailing slash, unify http/https)."""
        parsed = urlparse(url.lower().strip())
        path = parsed.path.rstrip('/')
        return f"{parsed.netloc}{path}"

    def _extract_urls_from_tool_result(self, tool_name: str, tool_args: dict[str, Any], tool_result: str) -> set[str]:
        """Extract URLs from tool call results."""
        urls = set()

        if tool_name == "web_search":
            try:
                results = json.loads(tool_result)
                if isinstance(results, list):
                    for r in results:
                        if isinstance(r, dict):
                            if "fileId" in r:
                                urls.add(r["fileId"])
                            elif "url" in r:
                                urls.add(r["url"])
            except (json.JSONDecodeError, KeyError):
                pass

        elif tool_name in ("web_fetch", "jina_fetch"):
            if "url" in tool_args:
                urls.add(tool_args["url"])

        return {self._normalize_url(url) for url in urls}

    def _extract_citations_from_content(self, content: str) -> set[str]:
        """Extract cited URLs from AI message content."""
        cited_urls = set(self.CITATION_PATTERN.findall(content))
        return {self._normalize_url(url) for url in cited_urls}

    def _generate_reminder(self, total: int, cited: int, uncited_urls: set[str], is_long_text: bool) -> str:
        """Generate reminder message for uncited sources."""
        icon = "🚫" if self.strictness == "strict" else "⚠️"
        uncited_list = "\n".join(f"  - {url}" for url in sorted(uncited_urls))

        emphasis = ""
        if is_long_text:
            emphasis = "\n\nThis is a long text. Pay special attention to:\n- Numbers and statistics\n- Key facts and findings\n- Important opinions or conclusions"

        return f"""{icon} CITATION VERIFICATION REMINDER

You used web_search/web_fetch and retrieved {total} sources, but only cited {cited} of them.

Uncited sources:
{uncited_list}

Please review your content and add citations for any factual claims, statistics,
or important viewpoints that came from these sources.{emphasis}

Quality over coverage - only cite where appropriate."""

    def wrap_tool_call(self, tool_name: str, tool_args: dict[str, Any], tool_result: str, state: dict[str, Any]) -> str | None:
        """Track URLs from web search/fetch tools."""
        if self.strictness == "off" or tool_name not in self.tracked_tools:
            return None

        thread_id = state.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        urls = self._extract_urls_from_tool_result(tool_name, tool_args, tool_result)
        if not urls:
            return None

        with self._lock:
            if thread_id not in self._pending_urls:
                self._pending_urls[thread_id] = set()
                # LRU eviction
                if len(self._pending_urls) > self.max_tracked_threads:
                    self._pending_urls.popitem(last=False)
            self._pending_urls[thread_id].update(urls)

        return None

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """Async version: Track URLs from web search/fetch tools."""
        result = await handler(request)

        tool_name = request.tool_call.get("name", "")
        if self.strictness == "off" or tool_name not in self.tracked_tools:
            return result

        thread_id = request.state.get("configurable", {}).get("thread_id")
        if not thread_id:
            return result

        tool_args = request.tool_call.get("args", {})
        tool_result = result.content if isinstance(result, ToolMessage) else ""

        urls = self._extract_urls_from_tool_result(tool_name, tool_args, tool_result)
        if urls:
            with self._lock:
                if thread_id not in self._pending_urls:
                    self._pending_urls[thread_id] = set()
                    if len(self._pending_urls) > self.max_tracked_threads:
                        self._pending_urls.popitem(last=False)
                self._pending_urls[thread_id].update(urls)

        return result

    def after_model(self, state: dict[str, Any], runtime) -> dict | None:
        """Verify citations in AI response."""
        if self.strictness == "off":
            return None

        thread_id = state.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        # Get pending URLs for this thread
        with self._lock:
            pending_urls = self._pending_urls.get(thread_id)
            if not pending_urls:
                return None
            pending_urls = pending_urls.copy()

        # Extract AI message content from state
        messages = state.get("messages", [])
        if not messages:
            return None

        last_message = messages[-1]
        if not isinstance(last_message, AIMessage):
            return None

        content = last_message.content
        if not isinstance(content, str):
            return None

        # Extract citations
        cited_urls = self._extract_citations_from_content(content)

        # Check for uncited URLs
        uncited_urls = pending_urls - cited_urls

        if uncited_urls:
            is_long_text = len(content) > self.long_text_threshold
            warning = self._generate_reminder(
                total=len(pending_urls),
                cited=len(cited_urls),
                uncited_urls=uncited_urls,
                is_long_text=is_long_text
            )
            return {"messages": [HumanMessage(content=warning)]}

        # All URLs cited, clear pending
        with self._lock:
            self._pending_urls.pop(thread_id, None)

        return None
