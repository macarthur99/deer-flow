import logging
from typing import Annotated
import json

import requests
from langchain.tools import InjectedToolCallId, ToolRuntime, tool
from langchain_core.messages import ToolMessage
from langgraph.types import Command
from langgraph.typing import ContextT

from deerflow.agents.thread_state import ThreadState
from deerflow.config import get_app_config

logger = logging.getLogger(__name__)


@tool("web_search", parse_docstring=True)
def web_search_tool(
    runtime: ToolRuntime[ContextT, ThreadState],
    search_key: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Search internal knowledge base for relevant materials.

    Args:
        search_key: The search keyword or phrase.
    """
    config = get_app_config().get_tool_config("web_search")
    api_url = config.model_extra.get("base_url")
    top_k = config.model_extra.get("top_k", 12)

    login_name = ""
    thread_id = runtime.context.get("thread_id")
    if not thread_id:
        thread_id=1

    payload = {
        "generalArgument": {"userId": -1, "loginName": login_name},
        "jsonArg": {"searchKey": search_key, "topK": top_k,"threadId":thread_id},
    }
    print(f"internal_search - url: {api_url}, params: {payload}")
    try:
        response = requests.post(api_url, json=payload)

        if response.status_code != 200:
            error_msg = f"API returned status {response.status_code}"
            logger.error(f"internal_search error: {error_msg}")
            return Command(update={"messages": [ToolMessage(f"Error: {error_msg}", tool_call_id=tool_call_id)]})

        result = response.json()

        if result.get("code") != 0:
            error_msg = result.get("message", "Unknown error")
            logger.error(f"internal_search error: {error_msg}")
            return Command(update={"messages": [ToolMessage(f"Error: {error_msg}", tool_call_id=tool_call_id)]})

        data = result.get("data", [])
        if not data:
            return Command(update={"messages": [ToolMessage("No results found", tool_call_id=tool_call_id)]})

        search_results = [
            {
                "fileId": item["fileId"],
                "fileName": item.get("fileName"),
                "snippet": item.get("content", ""),
            }
            for item in data if "fileId" in item
        ]

        logger.info(f"[internal_search] Constructed {len(search_results)} search_results")
        json_results = json.dumps(search_results, indent=2, ensure_ascii=False)

        return Command(
            update={
                "messages": [ToolMessage(json_results, tool_call_id=tool_call_id)],
            }
        )

    except Exception as e:
        error_msg = f"Request failed: {str(e)}"
        logger.error(f"internal_search error: {error_msg}")
        return Command(update={"messages": [ToolMessage(f"Error: {error_msg}", tool_call_id=tool_call_id)]})
