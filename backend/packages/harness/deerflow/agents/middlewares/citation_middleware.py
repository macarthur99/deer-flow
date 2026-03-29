import re
from typing import Any

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, ToolMessage


class CitationMiddleware(AgentMiddleware):
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
        """Extract URLs from AI and Tool messages, deduplicate, and renumber citations."""
        messages = state.get("messages", [])
        if not messages:
            return {}

        existing_citations = state.get("citations", [])
        new_urls = []
        tool_citations = []  # [(msg_index, old_num, url)]

        # Extract from all AIMessages
        for msg in messages:
            if isinstance(msg, AIMessage) and isinstance(msg.content, str):
                urls = set()
                markdown_links = re.findall(r'\[(?:citation:)?\d*[^\]]*\]\((https?://[^\)]+)\)', msg.content)
                urls.update(markdown_links)
                plain_urls = re.findall(r'https?://[^\s\)]+', msg.content)
                urls.update(plain_urls)
                for url in urls:
                    if url not in existing_citations and url not in new_urls:
                        new_urls.append(url)

        # Extract from ToolMessages
        for i, msg in enumerate(messages):
            if isinstance(msg, ToolMessage):
                matches = re.findall(r'\[citation:(\d+)\]\((https?://[^\)]+)\)', msg.content)
                for old_num, url in matches:
                    tool_citations.append((i, int(old_num), url))
                    if url not in existing_citations and url not in new_urls:
                        new_urls.append(url)

        # Build global URL to index mapping
        all_citations = existing_citations + new_urls
        url_to_index = {url: i + 1 for i, url in enumerate(all_citations)}

        # Renumber ToolMessages if needed
        updated_messages = None
        if tool_citations:
            updated_messages = list(messages)
            for msg_idx, old_num, url in tool_citations:
                new_num = url_to_index[url]
                if new_num != old_num:
                    msg = updated_messages[msg_idx]
                    pattern = rf'\[citation:{old_num}\]\({re.escape(url)}\)'
                    replacement = f'[citation:{new_num}]({url})'
                    new_content = re.sub(pattern, replacement, msg.content)
                    updated_messages[msg_idx] = msg.model_copy(update={"content": new_content})

        result = {}
        if new_urls:
            result["citations"] = new_urls
        if updated_messages:
            result["messages"] = updated_messages
        return result
