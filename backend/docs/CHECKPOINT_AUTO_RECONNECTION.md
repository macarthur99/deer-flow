# PostgreSQL Checkpoint Auto-Reconnection

## Overview

DeerFlow automatically retries checkpoint operations when PostgreSQL connections are lost, ensuring conversation state remains accessible even during transient database issues.

## How It Works

When using PostgreSQL as the checkpoint backend, all checkpoint operations are automatically wrapped with retry logic:

- **Retry attempts**: 3 times
- **Backoff strategy**: Exponential (1s, 2s, 4s)
- **Retryable errors**: Connection failures, transaction errors
- **Logging**: Only logs final failure or successful recovery

## Configuration

### Basic Setup

```yaml
checkpointer:
  type: postgres
  connection_string: postgresql://user:password@localhost:5432/deerflow
```

### Production Setup (Recommended)

Tune connection pool parameters for better resilience:

```yaml
checkpointer:
  type: postgres
  connection_string: postgresql://user:pass@host/db?min_size=5&max_size=20&timeout=10&reconnect_timeout=60
```

**Parameters**:
- `min_size=5` - Maintain 5 connections (default: 4)
- `max_size=20` - Allow pool growth (default: unlimited)
- `timeout=10` - Wait 10s for connection (default: 30s)
- `reconnect_timeout=60` - Retry failed connections for 60s (default: 300s)

## Behavior

### Success Path
```
Operation → Success (no retry, zero overhead)
```

### Transient Failure
```
Operation → Fail (connection lost)
  ↓ wait 1s
Retry 1 → Fail
  ↓ wait 2s
Retry 2 → Success ✓
  ↓ log recovery
Return result
```

### Permanent Failure
```
Operation → Fail
  ↓ wait 1s
Retry 1 → Fail
  ↓ wait 2s
Retry 2 → Fail
  ↓ wait 4s
Retry 3 → Fail
  ↓ log error
Raise exception
```

## Testing

Simulate connection loss to verify auto-reconnection:

1. Start DeerFlow with PostgreSQL checkpointer
2. Create a thread and send messages
3. Stop PostgreSQL: `docker stop postgres`
4. Attempt checkpoint operation (will retry)
5. Restart PostgreSQL: `docker start postgres`
6. Operation succeeds after reconnection

## Implementation

The retry logic is implemented in `ResilientCheckpointer` which wraps the underlying `AsyncPostgresSaver`:

- **File**: `packages/harness/deerflow/agents/checkpointer/resilient_checkpointer.py`
- **Integration**: `packages/harness/deerflow/agents/checkpointer/async_provider.py`
- **Tests**: `tests/test_checkpointer_retry.py`

## Limitations

- Only applies to PostgreSQL backend (sqlite and memory backends don't need it)
- Maximum 3 retry attempts (hardcoded)
- Only retries connection-related errors (not application errors)
