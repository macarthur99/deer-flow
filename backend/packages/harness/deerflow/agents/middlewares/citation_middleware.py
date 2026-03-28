import re
from typing import Any

from langchain.agents.middleware import Middleware
from langchain_core.messages import AIMessage


class CitationMiddleware(Middleware):
    """Extract and manage citations from AI messages."""

    def before_model(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        """Inject citation list into system prompt."""
        citations = state.get("citations", [])
        if not citations:
            return {}

        # Build citation reference list
        citation_list = "\n".join([f"[{i+1}] {url}" for i, url in enumerate(citations)])
        citation_prompt = f"\n\n<available_citations>\nYou have access to these citations. Use [citation:N](URL) format:\n{citation_list}\n</available_citations>"

        messages = state.get("messages", [])
        if messages and hasattr(messages[0], "content"):
            # Append to system message
            messages[0].content += citation_prompt

        return {}

    def after_model(self, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        """Extract URLs from AI message and add to state.citations."""
        messages = state.get("messages", [])
        if not messages:
            return {}

        last_message = messages[-1]
        if not isinstance(last_message, AIMessage):
            return {}

        content = last_message.content
        if not isinstance(content, str):
            return {}

        # Extract URLs from markdown links [text](url) and plain URLs
        urls = set()

        # Match markdown links
        markdown_links = re.findall(r'\[(?:citation:)?\d*[^\]]*\]\((https?://[^\)]+)\)', content)
        urls.update(markdown_links)

        # Match plain URLs
        plain_urls = re.findall(r'https?://[^\s\)]+', content)
        urls.update(plain_urls)

        existing_citations = state.get("citations", [])
        new_urls = [url for url in urls if url not in existing_citations]

        return {"citations": new_urls} if new_urls else {}
