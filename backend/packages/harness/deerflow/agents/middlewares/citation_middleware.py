import logging
import re
from typing import Any, override

from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.runtime import Runtime

from deerflow.sandbox.sandbox_provider import get_sandbox_provider

logger = logging.getLogger(__name__)


def _normalize_content(content):
    """Extract text from string or structured content."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(parts)
    return str(content)


class CitationMiddleware(AgentMiddleware):
    """Extract and manage citations from AI messages."""

    def _replace_citations(self, content: str, file_id_to_index: dict[str, int]) -> str:
        """Replace [citation](fileId) with [citation:N](fileId)."""
        def replace(match):
            file_id = match.group(1)
            num = file_id_to_index.get(file_id)
            return f'[citation:{num}]({file_id})' if num else match.group(0)
        return re.sub(r'\[citation(?::\d+)?\]\(([^\)]+)\)', replace, content)

    def _process_write_file_citations(self, tool_call_request: ToolCallRequest, runtime: Runtime):
        """Shared logic for processing write_file citations."""
        tool_call = tool_call_request.tool_call
        args = tool_call.get("args", {})
        content = args.get("content", "")

        if not content:
            return None

        state = runtime.state
        existing_citations = state.get("citations", [])

        matches = re.findall(r'\[citation(?::\d+)?\]\(([^\)]+)\)', content)
        new_file_ids = [fid for fid in matches if fid not in existing_citations]

        if new_file_ids:
            all_citations = existing_citations + new_file_ids
            state["citations"] = all_citations

            file_id_to_index = {fid: i + 1 for i, fid in enumerate(all_citations)}
            processed_content = self._replace_citations(content, file_id_to_index)

            args["content"] = processed_content
            tool_call["args"] = args

            logger.info(f"CitationMiddleware: Processed {len(new_file_ids)} new citations in write_file")

    @override
    def wrap_tool_call(self, tool_call_request: ToolCallRequest, runtime: Runtime) -> ToolMessage:
        """Intercept write_file tool calls to process citations in content."""
        tool_call = tool_call_request.tool_call
        tool_name = tool_call.get("name")

        if tool_name == "write_file":
            self._process_write_file_citations(tool_call_request, runtime)

        return tool_call_request.handler(tool_call_request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Any,
    ) -> ToolMessage:
        """Async version: Intercept write_file tool calls to process citations in content."""
        tool_call = request.tool_call
        tool_name = tool_call.get("name")

        if tool_name == "write_file" and request.runtime:
            self._process_write_file_citations(request, request.runtime)

        return await handler(request)

    def _update_output_files(self, state: dict[str, Any], file_id_to_index: dict[str, int]) -> None:
        """Update output files with numbered citations."""
        sandbox_state = state.get("sandbox")
        if not sandbox_state or not sandbox_state.get("sandbox_id"):
            return

        sandbox_id = sandbox_state["sandbox_id"]
        sandbox = get_sandbox_provider().get(sandbox_id)
        if not sandbox:
            return

        # Scan outputs directory for all files
        try:
            output_dir = "/mnt/user-data/outputs/"
            files = sandbox.list_dir(output_dir)

            for file_info in files:
                if file_info.get("type") != "file":
                    continue

                # Only process markdown files
                file_name = file_info.get("name", "")
                if not file_name.endswith(".md"):
                    continue

                file_path = output_dir + file_name
                try:
                    content = sandbox.read_file(file_path)
                    updated = self._replace_citations(content, file_id_to_index)
                    if updated != content:
                        sandbox.write_file(file_path, updated)
                        logger.info(f"Updated citations in {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to update {file_path}: {e}")
        except Exception as e:
            logger.warning(f"Failed to scan output directory: {e}")

    @override
    def after_agent(self, state: dict[str, Any], runtime: Runtime) -> dict[str, Any] | None:
        """Extract fileIds from AI and Tool messages, deduplicate, and assign numbers."""
        messages = state.get("messages", [])
        logger.info(f"CitationMiddleware.after_agent: Processing {len(messages)} messages")

        if not messages:
            return {}

        existing_citations = state.get("citations", [])
        new_file_ids = []
        citations_to_update = []  # [(msg_index, file_id)]

        # Extract from all AIMessages and ToolMessages
        for i, msg in enumerate(messages):
            logger.info(f"Message {i}: type={type(msg).__name__}, content_type={type(msg.content).__name__}")

            if isinstance(msg, (AIMessage, ToolMessage)):
                # Log raw content for debugging
                raw_preview = str(msg.content)[:300] if msg.content else "None"
                logger.info(f"Message {i} raw content preview: {raw_preview}")

                content = _normalize_content(msg.content)
                logger.info(f"Message {i} normalized content length: {len(content) if content else 0}")

                if content:
                    # Match both [citation](fileId) and [citation:N](fileId) for backward compatibility
                    matches = re.findall(r'\[citation(?::\d+)?\]\(([^\)]+)\)', content)
                    logger.info(f"Message {i} found {len(matches)} citation matches: {matches}")

                    for file_id in matches:
                        citations_to_update.append((i, file_id))
                        if file_id not in existing_citations and file_id not in new_file_ids:
                            new_file_ids.append(file_id)

        if new_file_ids:
            logger.info(f"CitationMiddleware: Found new citations: {new_file_ids}")
        else:
            logger.info("CitationMiddleware: No new citations found")

        # Build global fileId to index mapping
        all_citations = existing_citations + new_file_ids
        file_id_to_index = {file_id: i + 1 for i, file_id in enumerate(all_citations)}

        # Update all citations with numbers
        updated_messages = None
        if citations_to_update:
            logger.info(f"CitationMiddleware: Updating {len(citations_to_update)} citation references")
            updated_messages = list(messages)
            for msg_idx, file_id in citations_to_update:
                num = file_id_to_index[file_id]
                msg = updated_messages[msg_idx]
                pattern = rf'\[citation(?::\d+)?\]\({re.escape(file_id)}\)'
                replacement = f'[citation:{num}]({file_id})'

                if isinstance(msg.content, str):
                    new_content = re.sub(pattern, replacement, msg.content)
                    updated_messages[msg_idx] = msg.model_copy(update={"content": new_content})
                elif isinstance(msg.content, list):
                    new_content_list = []
                    for item in msg.content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            new_text = re.sub(pattern, replacement, item.get("text", ""))
                            new_content_list.append({**item, "text": new_text})
                        else:
                            new_content_list.append(item)
                    updated_messages[msg_idx] = msg.model_copy(update={"content": new_content_list})

        result = {}
        if new_file_ids:
            result["citations"] = all_citations
        if updated_messages:
            result["messages"] = updated_messages

        # if file_id_to_index:
        #     self._update_output_files(state, file_id_to_index)

        return result
