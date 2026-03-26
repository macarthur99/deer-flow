"""Thread management router.

Handles thread creation with user binding, listing, and deletion.
The actual LangGraph thread is created by proxying to the LangGraph internal
HTTP API; the Gateway then records the thread_id → user_id mapping in TiDB.

Request body convention (company-standard format):
    {
        "generalArgument": {"userId": 12},
        "jsonArg": { ... extra fields passed to LangGraph ... }
    }
"""

import logging
import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/threads", tags=["threads"])
logger = logging.getLogger(__name__)

# LangGraph Server is co-located; use the loopback address.
# Override with LANGGRAPH_INTERNAL_URL env var if needed.
_LANGGRAPH_URL = os.getenv("LANGGRAPH_INTERNAL_URL", "http://127.0.0.1:8001/ReportCenterService/rest/langgraph")


# ---------------------------------------------------------------------------
# Shared request schema
# ---------------------------------------------------------------------------


class GeneralArgument(BaseModel):
    userId: int


class BaseRequest(BaseModel):
    generalArgument: GeneralArgument
    jsonArg: dict = {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_engine():
    from deerflow.database.connection import get_async_engine

    return get_async_engine()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("")
async def create_thread(body: BaseRequest) -> dict:
    """Create a new LangGraph thread and bind it to the requesting user.

    Body:
        { "generalArgument": {"userId": 12}, "jsonArg": {} }

    Returns:
        LangGraph thread creation response (directly from LangGraph API)
    """
    user_id = body.generalArgument.userId

    # Proxy to LangGraph to create the thread with metadata
    try:
        # Prepare request body with metadata containing user_id
        request_body = body.jsonArg or {}
        request_body["metadata"] = {"user_id": str(user_id)}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{_LANGGRAPH_URL}/threads", json=request_body)
            resp.raise_for_status()
            lg_data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.error("LangGraph thread creation failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"LangGraph error: {exc.response.text}")
    except Exception as exc:
        logger.error("Failed to reach LangGraph: %s", exc)
        raise HTTPException(status_code=502, detail="LangGraph service unavailable")

    thread_id: str = lg_data.get("thread_id") or lg_data.get("id", "")
    if not thread_id:
        raise HTTPException(status_code=502, detail="LangGraph did not return a thread_id")

    # Persist thread → user binding
    engine = _get_engine()
    if engine is not None:
        from deerflow.database.thread_user import bind_thread_user

        await bind_thread_user(engine, thread_id, str(user_id))

    # Return the direct response from LangGraph API
    return lg_data


@router.get("")
async def list_threads(user_id: int) -> dict:
    """List all threads owned by a user.

    Query parameter:
        user_id=12

    Returns:
        { "threads": ["thread_id_1", ...] }
    """
    engine = _get_engine()
    if engine is None:
        return {"threads": []}

    from deerflow.database.thread_user import list_threads_for_user

    threads = await list_threads_for_user(engine, str(user_id))
    return {"threads": threads}


@router.post("/delete")
async def delete_thread(body: BaseRequest) -> dict:
    """Delete a thread (checks ownership, then removes from LangGraph + TiDB).

    Body:
        {
          "generalArgument": {"userId": 12234},
          "jsonArg": {"threadId": "xxx"}
        }
    """
    user_id = body.generalArgument.userId

    # 提取 threadId 并验证
    thread_id = body.jsonArg.get("threadId")
    if not thread_id:
        raise HTTPException(status_code=400, detail="Missing required field: jsonArg.threadId")

    # Best-effort deletion from LangGraph
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(f"{_LANGGRAPH_URL}/threads/{thread_id}")
            if resp.status_code not in (200, 204, 404):
                logger.warning("LangGraph DELETE /threads/%s returned %s", thread_id, resp.status_code)
    except Exception as exc:
        logger.warning("Could not delete thread from LangGraph: %s", exc)

    # Remove binding from TiDB
    engine = _get_engine()
    if engine is not None:
        from deerflow.database.thread_user import delete_thread_user

        await delete_thread_user(engine, thread_id)

    return {"success": True, "thread_id": thread_id}
