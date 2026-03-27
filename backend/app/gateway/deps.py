"""Centralized accessors for singleton objects stored on ``app.state``.

All reads **and writes** to the four singletons on ``app.state`` should go
through this module so the coupling is in one place.

* **Initializers** (used by ``app.py`` at startup): create the singleton and
  attach it to ``app.state``.
* **Getters** (used by routers): raise 503 when a required dependency is
  missing, except ``get_store`` which returns ``None``.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request

from deerflow.agents.runs import RunManager
from deerflow.agents.stream_bridge import StreamBridge


# ---------------------------------------------------------------------------
# Initializers – called once during app startup
# ---------------------------------------------------------------------------


async def init_stream_bridge(app: FastAPI) -> None:
    """Create the :class:`StreamBridge` and store it on ``app.state``."""
    from deerflow.agents.stream_bridge import make_stream_bridge

    bridge_cm = make_stream_bridge()
    bridge = await bridge_cm.__aenter__()
    app.state.stream_bridge = bridge


async def init_checkpointer(app: FastAPI) -> None:
    """Create the async checkpointer and store it on ``app.state``."""
    from deerflow.agents.checkpointer.async_provider import make_checkpointer

    ckpt_cm = make_checkpointer()
    checkpointer = await ckpt_cm.__aenter__()
    app.state.checkpointer = checkpointer


def init_run_manager(app: FastAPI) -> None:
    """Create a :class:`RunManager` and store it on ``app.state``."""
    app.state.run_manager = RunManager()


def init_store(app: FastAPI) -> None:
    """Initialize the store slot on ``app.state`` (currently ``None``)."""
    app.state.store = None


# ---------------------------------------------------------------------------
# Getters – called by routers per-request
# ---------------------------------------------------------------------------


def get_stream_bridge(request: Request) -> StreamBridge:
    """Return the global :class:`StreamBridge`, or 503."""
    bridge = getattr(request.app.state, "stream_bridge", None)
    if bridge is None:
        raise HTTPException(status_code=503, detail="Stream bridge not available")
    return bridge


def get_run_manager(request: Request) -> RunManager:
    """Return the global :class:`RunManager`, or 503."""
    mgr = getattr(request.app.state, "run_manager", None)
    if mgr is None:
        raise HTTPException(status_code=503, detail="Run manager not available")
    return mgr


def get_checkpointer(request: Request):
    """Return the global checkpointer, or 503."""
    cp = getattr(request.app.state, "checkpointer", None)
    if cp is None:
        raise HTTPException(status_code=503, detail="Checkpointer not available")
    return cp


def get_store(request: Request):
    """Return the global store (may be ``None`` if not configured)."""
    return getattr(request.app.state, "store", None)
