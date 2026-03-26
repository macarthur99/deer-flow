"""Combined LangGraph + Gateway server entry point.

LangGraph runs as a standalone ASGI app, Gateway runs as a separate FastAPI app.
They are combined via Starlette's Mount so that each service lives under its
own dedicated path prefix.

Route layout:
  /ReportCenterService/rest/langgraph/threads, /runs, /assistants, ...
                                      →  LangGraph routes (mounted at prefix)
  /ReportCenterService/rest/gateway/api/models, /api/mcp, ...
                                      →  Gateway routes   (mounted at prefix)
  /ReportCenterService/rest/gateway/health, /docs, /redoc, ...
                                      →  Gateway routes   (mounted at prefix)
"""

import json
import logging
import os
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# 1. Configure logging BEFORE importing LangGraph modules.
#    LangGraph loggers are created at module import time, so configuration
#    must happen before any langgraph imports.
# ---------------------------------------------------------------------------
from deerflow.config.logging_config import configure_all_logging

configure_all_logging(
    root_level=logging.INFO,
    langgraph_level=logging.INFO,
    deerflow_level=logging.INFO,
    gateway_level=logging.INFO,
    log_dir="/work/logs/ReportCenterService",
    langgraph_file_output=True,
    deerflow_file_output=True,
    gateway_file_output=True,
    rotation_type="size",
    max_bytes=10 * 1024 * 1024,  # 10 MB
    backup_count=10,
    console_output=True,
)

# ---------------------------------------------------------------------------
# 2. Load env from the project root directory.
# ---------------------------------------------------------------------------
_this_dir = os.path.dirname(os.path.abspath(__file__))
_backend_dir = os.path.dirname(_this_dir)
_project_root = os.path.dirname(_backend_dir)
_env_file = os.path.join(_project_root, "env")

if os.path.exists(_env_file):
    try:
        from dotenv import dotenv_values  # type: ignore[import-untyped]

        for _k, _v in dotenv_values(_env_file).items():
            if _k not in os.environ and _v is not None:
                os.environ[_k] = _v
    except ImportError:
        pass

# ---------------------------------------------------------------------------
# 2. LangGraph environment variables (mirrors `langgraph dev --allow-blocking
#    --no-reload`).  Use setdefault so that any value already set in the
#    environment (e.g. from a real .env file or the shell) is preserved.
#
#    NOTE: LANGGRAPH_HTTP is intentionally NOT set here.  When LANGGRAPH_HTTP
#    is absent, langgraph_api.server builds its own standalone Starlette app
#    (routes at /threads, /runs, …) rather than injecting routes into the
#    Gateway FastAPI app.  We then combine the two apps ourselves using
#    Starlette's Mount so that only the LangGraph routes get the prefix.
# ---------------------------------------------------------------------------

# Graph definitions from langgraph_kk.json
os.environ.setdefault(
    "LANGSERVE_GRAPHS",
    json.dumps({"lead_agent": "deerflow.agents:make_lead_agent"}),
)

os.environ.setdefault(
     "LANGGRAPH_CHECKPOINTER",
     json.dumps({"path": "deerflow/agents/checkpointer/async_provider.py:make_checkpointer"}),
 )


# In-memory storage — same defaults as `langgraph dev`
# os.environ.setdefault("MIGRATIONS_PATH", "__inmem")
# os.environ.setdefault("DATABASE_URI","__inmem")
os.environ.setdefault("DATABASE_URI", "sqlite://cloud-model/aiwriting/checkpoints/checkpoints.db")
os.environ.setdefault("REDIS_URI", "fake")

# os.environ.setdefault("BG_JOB_ISOLATED_LOOPS","true")
os.environ.setdefault("N_JOBS_PER_WORKER", "4")
os.environ.setdefault("LANGGRAPH_RUNTIME_EDITION", "inmem")
os.environ.setdefault("LANGGRAPH_DISABLE_FILE_PERSISTENCE", "false")

# Allow blocking IO (equivalent to `--allow-blocking`)
os.environ.setdefault("LANGGRAPH_ALLOW_BLOCKING", "true")

# Miscellaneous LangGraph settings
os.environ.setdefault("LANGSMITH_LANGGRAPH_API_VARIANT", "local_dev")
os.environ.setdefault("ALLOW_PRIVATE_NETWORK", "true")
os.environ.setdefault("LANGGRAPH_UI_BUNDLER", "true")

# ---------------------------------------------------------------------------
# 3. Import both apps AFTER all env vars are in place.
#    langgraph_api.server builds the standalone LangGraph ASGI app at
#    module-level, so env vars must be set first.
# ---------------------------------------------------------------------------
from langgraph_api.server import app as _langgraph_app  # noqa: E402
from app.gateway.app import app as _gateway_app  # noqa: E402
from starlette.applications import Starlette  # noqa: E402
from starlette.routing import Mount  # noqa: E402

# NOTE: Custom MySQL checkpointer is no longer passed to create_agent() because
# LangGraph Server (inmem edition) ignores it and it caused TypeError on graph
# introspection.  Conversation history is persisted to TiDB via AuditMiddleware.
# The database engine / conversation_messages table are initialised by the
# Gateway lifespan (src/gateway/app.py).

# ---------------------------------------------------------------------------
# 4. Path prefixes for each service.
# ---------------------------------------------------------------------------
LANGGRAPH_PREFIX = "/ReportCenterService/rest/langgraph"
GATEWAY_PREFIX = "/ReportCenterService/rest/gateway"

# ---------------------------------------------------------------------------
# 5. Combined lifespan: start Gateway first, then LangGraph (reverse on
#    shutdown).  Starlette's Mount does not automatically propagate lifespan
#    events to sub-apps, so we manage them explicitly here.
# ---------------------------------------------------------------------------


@asynccontextmanager
async def _combined_lifespan(app):
    async with _gateway_app.router.lifespan_context(_gateway_app):
        async with _langgraph_app.router.lifespan_context(_langgraph_app):
            yield


# ---------------------------------------------------------------------------
# 6. Build the final combined ASGI app.
#    Mount strips the prefix before forwarding to _langgraph_app, so
#    LangGraph's internal routing still sees /threads, /runs, etc.
#    The loopback transport configured by langgraph_api.server also
#    bypasses the Mount and calls _langgraph_app directly, so in-process
#    SDK calls are unaffected by the prefix.
# ---------------------------------------------------------------------------
app = Starlette(
    routes=[
        Mount(LANGGRAPH_PREFIX, app=_langgraph_app),
        Mount(GATEWAY_PREFIX, app=_gateway_app),
    ],
    lifespan=_combined_lifespan,
)

__all__ = ["app"]
