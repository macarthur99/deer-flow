"""Unified server that mounts both Gateway and LangGraph applications."""

import os
from pathlib import Path

# Set required LangGraph environment variables BEFORE any imports
os.environ.setdefault("LANGGRAPH_RUNTIME_EDITION", "inmem")
os.environ.setdefault("DATABASE_URI", f"sqlite:///{Path.cwd() / '.langgraph_api' / 'langgraph.db'}")
os.environ.setdefault("REDIS_URI", "")
#os.environ.setdefault("LANGGRAPH_CONFIG", str(Path.cwd() / "langgraph.json"))

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.gateway.app import app as gateway_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create main application
app = FastAPI(
    title="DeerFlow Unified Server",
    description="Unified server hosting both Gateway API and LangGraph Server",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Gateway routers
for route in gateway_app.routes:
    app.routes.append(route)

# Mount LangGraph at /langgraph
try:
    from langgraph_api.server import app as langgraph_app
    app.mount("/langgraph", langgraph_app)
    logger.info("LangGraph application mounted at /langgraph")
except ImportError as e:
    logger.error(f"Failed to import LangGraph application: {e}")
    raise


@app.get("/")
async def root():
    """Root health check endpoint."""
    return {
        "status": "ok",
        "service": "deerflow-unified",
        "endpoints": {
            "gateway_api": "/api/*",
            "langgraph_api": "/langgraph/*",
            "gateway_health": "/health",
            "langgraph_health": "/langgraph/ok",
        },
    }
