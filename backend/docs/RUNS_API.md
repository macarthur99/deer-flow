# Runs API - REST Conversation Interface

## Overview

The Runs API provides a REST interface for direct conversation with the DeerFlow agent, compatible with LangGraph's streaming format. It uses SQLite checkpointer for persistent state across multiple conversation turns.

## Endpoints

### POST /api/threads/{thread_id}/runs/stream

Stream a conversation turn with Server-Sent Events (SSE).

**Request:**
```json
{
  "input": {
    "messages": [
      {"role": "human", "content": "Hello, what's 2+2?"}
    ]
  },
  "config": {
    "recursion_limit": 100
  },
  "stream_mode": ["values", "messages-tuple"]
}
```

**Response:** SSE stream
```
event: messages-tuple
data: {"type": "ai", "content": "2+2 equals 4.", "id": "msg_123"}

event: values
data: {"title": "Math Question", "messages": [...], "artifacts": []}

event: end
data: {"usage": {"input_tokens": 50, "output_tokens": 20, "total_tokens": 70}}
```

### GET /api/threads/{thread_id}/history

Retrieve conversation history from checkpoint storage.

**Response:**
```json
{
  "thread_id": "abc123",
  "title": "Math Question",
  "messages": [
    {"type": "human", "content": "Hello, what's 2+2?", "id": "msg_1"},
    {"type": "ai", "content": "2+2 equals 4.", "id": "msg_2"}
  ]
}
```

## Implementation Details

### Architecture

- **Router**: `app/gateway/routers/runs.py`
- **Client**: Uses `DeerFlowClient` from `deerflow/client.py`
- **Checkpointer**: Initialized in Gateway lifespan, shared across requests
- **State Persistence**: SQLite checkpoint stores conversation state

### Key Features

1. **Stateful Conversations**: Multi-turn conversations preserved via checkpointer
2. **SSE Streaming**: Real-time event streaming compatible with LangGraph format
3. **History Access**: Query past conversations from checkpoint storage
4. **Minimal Implementation**: Reuses existing `DeerFlowClient.stream()` method

## Testing

Run tests:
```bash
PYTHONPATH=. uv run pytest tests/test_runs_api.py -v
```

Manual testing:
```bash
# Stream conversation
curl -N -X POST http://localhost:8001/api/threads/test-thread/runs/stream \
  -H "Content-Type: application/json" \
  -d '{
    "input": {"messages": [{"role": "human", "content": "Hello"}]},
    "stream_mode": ["values", "messages-tuple"]
  }'

# Get history
curl http://localhost:8001/api/threads/test-thread/history
```

## Configuration

No additional configuration required. The API uses:
- Existing `config.yaml` for model and tool settings
- Existing checkpointer configuration from `deerflow.agents.checkpointer`
- Gateway runs on port 8001 (configurable via `gateway.port` in config)

## Error Handling

- `400` - Invalid request (missing messages, empty content)
- `404` - Thread not found in checkpoint
- `503` - Checkpointer not available
- `500` - Internal server error during streaming
