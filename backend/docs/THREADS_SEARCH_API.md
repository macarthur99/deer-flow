# Threads Search API

## Overview

The Threads Search API provides a LangGraph-compatible endpoint for searching and filtering conversation threads stored in PostgreSQL.

## Endpoint

**POST** `/api/threads/search`

## Requirements

- PostgreSQL checkpointer must be configured in `config.yaml`
- Only works with PostgreSQL backend (returns 501 for other checkpointer types)

## Request Format

```json
{
  "metadata": {},           // Optional: Filter by metadata (JSONB contains)
  "values": {},             // Optional: Filter by state values (Python-side)
  "ids": ["id1", "id2"],    // Optional: Filter by thread IDs
  "status": "idle",         // Optional: Filter by status (not implemented)
  "limit": 10,              // Required: Number of results
  "offset": 0,              // Required: Pagination offset
  "sort_by": "created_at",  // Optional: Sort field (created_at/updated_at)
  "sort_order": "desc",     // Optional: Sort order (desc/asc)
  "select": ["thread_id"],  // Optional: Select specific fields
  "extract": {              // Optional: Extract nested data (max 10 paths)
    "last_msg": "values.messages[-1].content"
  }
}
```

## Response Format

```json
[
  {
    "thread_id": "abc123",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "metadata": {},
    "status": "idle",
    "extracted": {
      "last_msg": "..."
    }
  }
]
```

## Features

### Filtering

- **ids**: Uses PostgreSQL `ANY` operator for efficient ID filtering
- **metadata**: Uses JSONB `@>` operator for containment queries
- **values**: Filters on deserialized checkpoint state (slower, post-query)

### Sorting

- Supports sorting by `created_at` or `updated_at`
- Ascending or descending order

### Pagination

- `limit` and `offset` parameters for pagination
- Efficient SQL-level pagination

### Field Selection

- Use `select` to return only specific fields
- Reduces response size for large result sets

### Data Extraction

- Extract nested values using dot notation: `values.title`
- Support for array indexing: `values.messages[-1].content`
- Maximum 10 extraction paths per request
- Returns `null` for invalid paths

## Implementation Details

### SQL Query Strategy

1. Uses `DISTINCT ON (thread_id)` to get latest checkpoint per thread
2. Filters applied at SQL level where possible (ids, metadata)
3. Sorts by checkpoint_id DESC to get latest state
4. Wraps in subquery for final sorting and pagination

### Deserialization

- Uses LangGraph's `JsonPlusSerializer` to deserialize checkpoint data
- Extracts `channel_values` for state access
- Handles both BYTEA and JSON checkpoint formats

### Error Handling

- 503: Checkpointer not available
- 501: PostgreSQL checkpointer not installed or wrong type
- Invalid extract paths return `null` instead of errors

## Example Usage

### Basic Search

```bash
curl -X POST http://localhost:8001/api/threads/search \
  -H "Content-Type: application/json" \
  -d '{"limit": 10, "offset": 0}'
```

### Filter by IDs

```bash
curl -X POST http://localhost:8001/api/threads/search \
  -H "Content-Type: application/json" \
  -d '{"ids": ["thread-1", "thread-2"], "limit": 10}'
```

### Extract Data

```bash
curl -X POST http://localhost:8001/api/threads/search \
  -H "Content-Type: application/json" \
  -d '{
    "limit": 10,
    "extract": {
      "title": "values.title",
      "last_msg": "values.messages[-1].content"
    }
  }'
```

### Pagination

```bash
curl -X POST http://localhost:8001/api/threads/search \
  -H "Content-Type: application/json" \
  -d '{"limit": 20, "offset": 40, "sort_by": "updated_at", "sort_order": "desc"}'
```

## Testing

Run the test suite:

```bash
cd backend
PYTHONPATH=. uv run pytest tests/test_threads_search.py -v
```

Tests cover:
- Value extraction with dot notation and array indices
- Error handling (no checkpointer, wrong type)
- Basic search functionality
- Extract parameter functionality
