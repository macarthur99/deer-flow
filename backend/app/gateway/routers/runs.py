import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from deerflow.client import DeerFlowClient

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/threads", tags=["runs"])


class ThreadSearchRequest(BaseModel):
    metadata: dict[str, Any] | None = None
    values: dict[str, Any] | None = None
    ids: list[str] | None = None
    status: str | None = None
    limit: int = 10
    offset: int = 0
    sort_by: str = "created_at"
    sort_order: str = "desc"
    select: list[str] | None = None
    extract: dict[str, str] | None = None


class RunStreamRequest(BaseModel):
    input: dict[str, Any]
    config: dict[str, Any] | None = None
    stream_mode: list[str] = ["values", "messages-tuple"]


class ThreadHistoryResponse(BaseModel):
    thread_id: str
    messages: list[dict[str, Any]]
    title: str | None = None


@router.post("/{thread_id}/runs/stream")
async def stream_run(thread_id: str, request: Request, body: RunStreamRequest):
    """Stream conversation with LangGraph-compatible SSE format."""
    checkpointer = getattr(request.app.state, "checkpointer", None)

    messages = body.input.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="No messages in input")

    user_message = messages[-1].get("content", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="Empty message content")

    client = DeerFlowClient(checkpointer=checkpointer)

    async def event_generator():
        try:
            for event in client.stream(user_message, thread_id=thread_id):
                yield f"event: {event.type}\n"
                yield f"data: {json.dumps(event.data)}\n\n"
        except Exception as e:
            logger.exception("Stream error for thread %s", thread_id)
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.get("/{thread_id}/history")
async def get_thread_history(thread_id: str, request: Request):
    """Get conversation history from checkpoint."""
    checkpointer = getattr(request.app.state, "checkpointer", None)
    if not checkpointer:
        raise HTTPException(status_code=503, detail="Checkpointer not available")

    config = {"configurable": {"thread_id": thread_id}}
    checkpoint = checkpointer.get(config)

    if not checkpoint:
        raise HTTPException(status_code=404, detail="Thread not found")

    values = checkpoint.get("channel_values", {})
    messages = values.get("messages", [])
    title = values.get("title")

    from deerflow.client import DeerFlowClient
    serialized = [DeerFlowClient._serialize_message(msg) for msg in messages]

    return ThreadHistoryResponse(thread_id=thread_id, messages=serialized, title=title)


@router.post("/search")
async def search_threads(request: Request, body: ThreadSearchRequest):
    """Search threads with filtering, sorting, and extraction."""
    checkpointer = getattr(request.app.state, "checkpointer", None)
    if not checkpointer:
        raise HTTPException(status_code=503, detail="Checkpointer not available")

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ImportError:
        raise HTTPException(status_code=501, detail="PostgreSQL checkpointer not installed")

    if not isinstance(checkpointer, AsyncPostgresSaver):
        raise HTTPException(status_code=501, detail="Search only supported with PostgreSQL checkpointer")

    # Build SQL query
    query = """
        SELECT DISTINCT ON (c.thread_id)
            c.thread_id,
            c.checkpoint,
            c.type,
            c.metadata
        FROM checkpoints c
        WHERE c.checkpoint_ns = ''
    """
    params = []

    if body.ids:
        query += f" AND c.thread_id = ANY($${len(params) + 1})"
        params.append(body.ids)

    if body.metadata:
        query += f" AND c.metadata @> $${len(params) + 1}::jsonb"
        params.append(json.dumps(body.metadata))

    query += " ORDER BY c.thread_id, c.checkpoint_id DESC"

    # Apply sorting
    sort_field = "created_at" if body.sort_by == "created_at" else "updated_at"
    sort_order = "DESC" if body.sort_order == "desc" else "ASC"

    # Wrap in subquery for final sorting and pagination
    query = f"""
        SELECT * FROM ({query}) sub
        ORDER BY (sub.metadata->>'{sort_field}') {sort_order}
        LIMIT $${len(params) + 1} OFFSET $${len(params) + 2}
    """
    params.extend([body.limit, body.offset])

    # Execute query
    with checkpointer.conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    # Process results
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    serde = JsonPlusSerializer()
    results = []

    for row in rows:
        thread_id, checkpoint_bytes, type_field, metadata = row

        # Deserialize checkpoint
        checkpoint_data = serde.loads_typed((type_field, checkpoint_bytes))
        channel_values = checkpoint_data.get("channel_values", {})

        # Apply values filter
        if body.values:
            match = all(channel_values.get(k) == v for k, v in body.values.items())
            if not match:
                continue

        # Build result
        result = {
            "thread_id": thread_id,
            "created_at": metadata.get("created_at"),
            "updated_at": metadata.get("updated_at"),
            "metadata": metadata,
            "status": "idle",
        }

        # Apply select filter
        if body.select:
            result = {k: v for k, v in result.items() if k in body.select}

        # Apply extract
        if body.extract:
            extracted = {}
            for key, path in list(body.extract.items())[:10]:  # Max 10 paths
                extracted[key] = _extract_value({"values": channel_values}, path)
            result["extracted"] = extracted

        results.append(result)

    return results


def _extract_value(data: dict, path: str) -> Any:
    """Extract nested value from data using dot notation and array indices."""
    try:
        parts = path.replace("[", ".").replace("]", "").split(".")
        result = data
        for part in parts:
            if not part:
                continue
            if part.lstrip("-").isdigit():
                result = result[int(part)]
            else:
                result = result.get(part) if isinstance(result, dict) else None
            if result is None:
                return None
        return result
    except (KeyError, IndexError, TypeError, AttributeError):
        return None
