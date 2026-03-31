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
        """Extract fileIds from AI and Tool messages, deduplicate, and assign numbers."""
        messages = state.get("messages", [])
        if not messages:
            return {}

        existing_citations = state.get("citations", [])
        new_file_ids = []
        citations_to_update = []  # [(msg_index, file_id)]

        # Extract from all AIMessages and ToolMessages
        for i, msg in enumerate(messages):
            if isinstance(msg, (AIMessage, ToolMessage)) and isinstance(msg.content, str):
                # Match both [citation](fileId) and [citation:N](fileId) for backward compatibility
                matches = re.findall(r'\[citation(?::\d+)?\]\(([^\)]+)\)', msg.content)
                for file_id in matches:
                    citations_to_update.append((i, file_id))
                    if file_id not in existing_citations and file_id not in new_file_ids:
                        new_file_ids.append(file_id)

        # Build global fileId to index mapping
        all_citations = existing_citations + new_file_ids
        file_id_to_index = {file_id: i + 1 for i, file_id in enumerate(all_citations)}

        # Update all citations with numbers
        updated_messages = None
        if citations_to_update:
            updated_messages = list(messages)
            for msg_idx, file_id in citations_to_update:
                num = file_id_to_index[file_id]
                msg = updated_messages[msg_idx]
                # Replace both numbered and unnumbered formats
                pattern = rf'\[citation(?::\d+)?\]\({re.escape(file_id)}\)'
                replacement = f'[citation:{num}]({file_id})'
                new_content = re.sub(pattern, replacement, msg.content)
                updated_messages[msg_idx] = msg.model_copy(update={"content": new_content})

        result = {}
        if new_file_ids:
            result["citations"] = new_file_ids
        if updated_messages:
            result["messages"] = updated_messages
        return result
