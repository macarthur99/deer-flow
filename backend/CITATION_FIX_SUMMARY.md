# Citation Numbering Fix Summary

## Problem
Users reported that citations in generated articles appeared as `[citation](url)` without numbering, instead of the expected `[citation:1](url)` format.

## Root Cause
The `CitationMiddleware` was using the `after_model` hook, which runs after each individual model invocation. At that point:
- AIMessage.content is typically empty (length 0) when the model makes tool calls
- The final user-facing response with citations hasn't been generated yet
- The middleware couldn't find any citations to process

## Solution
Changed `CitationMiddleware` from `after_model` to `after_agent` hook:
- `after_agent` runs after the entire agent execution completes (including all tool calls)
- At this point, the final AIMessage with citations is present in the message list
- The middleware can now successfully extract and number all citations

## Changes Made
1. **citation_middleware.py**: Changed `after_model` → `after_agent` (line 29)
2. **test_citation_middleware.py**: Updated all test calls to use `after_agent`
3. Added enhanced logging to show raw content preview for debugging

## Test Results
All 11 unit tests pass:
- ✅ Extract unnumbered citations
- ✅ Backward compatibility with numbered format
- ✅ Deduplication across messages
- ✅ Renumbering with existing citations
- ✅ Tool message citations
- ✅ Non-URL file IDs
- ✅ Empty state handling
- ✅ No citations in messages
- ✅ Structured content citations
- ✅ Structured content with non-text blocks
- ✅ Existing citation only

## Expected Behavior After Fix
When the agent generates responses with `[citation](url)`, the middleware will automatically convert them to `[citation:1](url)`, `[citation:2](url)`, etc., with consistent numbering across the entire conversation thread.
