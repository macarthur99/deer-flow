# Citation System Simplification - Implementation Summary

## Overview

Successfully simplified the citation system by making CitationMiddleware the single source of truth for citation numbering and deduplication. Agents now emit unnumbered citations `[citation](fileId)` and the middleware handles all numbering automatically.

## Changes Made

### 1. ThreadState Schema (`packages/harness/deerflow/agents/thread_state.py`)
- Added `citations: NotRequired[list[str] | None]` field to properly track citations in state

### 2. CitationMiddleware (`packages/harness/deerflow/agents/middlewares/citation_middleware.py`)
- Updated regex to match both `[citation](fileId)` and `[citation:N](fileId)` (backward compatibility)
- Removed URL-only restriction - now supports any fileId (URLs, doc-12345, internal-report-2024, etc.)
- Simplified extraction logic to handle both AIMessage and ToolMessage in single loop
- Middleware now assigns numbers to all citations based on global deduplication

### 3. Lead Agent Prompt (`packages/harness/deerflow/agents/lead_agent/prompt.py`)
- Removed all numbering instructions from agent
- Changed format from `[citation:[N]](fileId)` to `[citation](fileId)`
- Simplified instructions: agents just emit fileId, middleware handles numbering
- Removed redundant examples and complex numbering rules

### 4. Subagent Prompt (`packages/harness/deerflow/subagents/builtins/general_purpose.py`)
- Updated citation format from `[citation:[N]](fileId)` to `[citation](fileId)`
- Removed numbering instructions

### 5. Unit Tests (`tests/test_citation_middleware.py`)
- Created comprehensive test suite with 9 tests covering:
  - Unnumbered citation extraction
  - Backward compatibility with numbered format
  - Global deduplication across messages
  - Renumbering with existing citations
  - ToolMessage citation handling
  - Non-URL fileId support (doc-12345, etc.)
  - System prompt injection
  - Edge cases (empty state, no citations)

## Test Results

All 9 new tests pass:
```
tests/test_citation_middleware.py::test_extract_unnumbered_citations PASSED
tests/test_citation_middleware.py::test_extract_numbered_citations_backward_compat PASSED
tests/test_citation_middleware.py::test_deduplication_across_messages PASSED
tests/test_citation_middleware.py::test_renumbering_with_existing_citations PASSED
tests/test_citation_middleware.py::test_tool_message_citations PASSED
tests/test_citation_middleware.py::test_non_url_file_ids PASSED
tests/test_citation_middleware.py::test_before_model_injection PASSED
tests/test_citation_middleware.py::test_empty_state PASSED
tests/test_citation_middleware.py::test_no_citations_in_messages PASSED
```

Existing tests remain unaffected (verified with test_memory_updater.py - 29 passed).

## Benefits

1. **Eliminates redundancy**: No duplicate numbering logic between agents and middleware
2. **Clearer separation of concerns**: Agents focus on content, middleware handles citation management
3. **Simpler for agents**: No need to track citation numbers or coordinate with subagents
4. **Backward compatible**: Still processes old `[citation:N](fileId)` format
5. **Flexible fileId support**: Works with URLs, document IDs, or any string identifier

## Migration Notes

- Existing conversations with numbered citations will continue to work
- New conversations will use unnumbered format
- No breaking changes to API or data structures
