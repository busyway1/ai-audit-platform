"""FastAPI Application Entry Point

This is the main FastAPI application that orchestrates:
1. LangGraph workflow engine initialization with PostgresSaver
2. REST API routes for audit operations
3. SSE streaming for real-time agent messages
4. CORS middleware for frontend integration
5. Lifespan context manager for resource management

Architecture:
- Frontend (React) connects to:
  * REST API: POST /api/projects/start, POST /api/tasks/approve
  * SSE Stream: GET /api/stream/{task_id}
  * Supabase Realtime: Direct Supabase connection for task status updates

- Backend (FastAPI) manages:
  * LangGraph workflow execution (Partner → Manager → Staff agents)
  * PostgresSaver checkpoints for workflow persistence
  * Supabase sync for frontend visibility

Reference: Plan section T3.5, Specification section 8.1-8.3
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
import sys
from typing import AsyncGenerator
from dotenv import load_dotenv

from .db.checkpointer import get_checkpointer, setup_checkpoint_tables

# Load environment variables early
load_dotenv()
from .api import routes, sse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("backend.log")
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager for resource initialization and cleanup.

    Startup:
        1. Initialize PostgresSaver (create checkpoint tables if needed)
        2. Create LangGraph workflow graph (placeholder - will be implemented by Window 2)
        3. Store graph instance in app.state for route access

    Shutdown:
        1. Cleanup graph resources
        2. Close database connections

    Reference: https://fastapi.tiangolo.com/advanced/events/#lifespan
    """
    logger.info("=" * 80)
    logger.info("Starting AI Audit Platform Backend")
    logger.info("=" * 80)

    try:
        # ============================================================================
        # STARTUP: Initialize PostgresSaver
        # ============================================================================
        logger.info("Initializing PostgresSaver checkpointer...")

        # Setup checkpoint tables (idempotent - safe to run multiple times)
        logger.info("Setting up PostgresSaver checkpoint tables...")
        try:
            setup_checkpoint_tables()
            logger.info("✅ PostgresSaver initialized successfully")
        except Exception as e:
            logger.warning(f"⚠️  PostgresSaver initialization failed: {e}")
            logger.warning("    Continuing without checkpointer (E2E test mode or missing DB credentials)")
            logger.warning("    Graph functionality will be disabled.")

        # ============================================================================
        # STARTUP: Create LangGraph Workflow
        # ============================================================================
        # NOTE: We need to keep the checkpointer connection alive during the entire
        # app lifecycle. The graph holds a reference to the checkpointer, so if we
        # close the connection, graph.ainvoke() will fail.

        logger.info("Initializing LangGraph workflow...")

        checkpointer = None
        graph = None

        try:
            # Try to import graph builder (may not exist yet if Window 2 incomplete)
            from .graph.graph import create_parent_graph
            from langgraph.checkpoint.memory import MemorySaver

            # For async graph invocation (ainvoke), we need an async-compatible checkpointer
            # MemorySaver works for both sync and async, and is simpler for ad-hoc chat
            # PostgresSaver requires psycopg async setup which is more complex
            logger.info("Using MemorySaver checkpointer (in-memory, no persistence)")
            checkpointer = MemorySaver()

            graph = create_parent_graph(checkpointer)
            logger.info("✅ LangGraph workflow initialized successfully")

        except ImportError as e:
            logger.warning(
                f"⚠️  LangGraph graph.py not found or incomplete: {e}\n"
                "    This is expected if Window 2 (Backend Core) hasn't created graph.py yet.\n"
                "    Setting app.state.graph = None. REST endpoints will return 500 until graph is ready."
            )
            graph = None

        except Exception as e:
            logger.error(f"❌ Failed to initialize LangGraph workflow: {e}", exc_info=True)
            graph = None

        # Store graph in app.state for access in route handlers
        app.state.graph = graph

        # ============================================================================
        # STARTUP: Log Environment Info
        # ============================================================================
        logger.info("Environment Configuration:")
        logger.info(f"  - SUPABASE_URL: {os.getenv('SUPABASE_URL', 'NOT SET')}")
        logger.info(f"  - SUPABASE_SERVICE_KEY: {'***' if os.getenv('SUPABASE_SERVICE_KEY') else 'NOT SET'}")
        logger.info(f"  - POSTGRES_CONNECTION_STRING: {'***' if os.getenv('POSTGRES_CONNECTION_STRING') else 'NOT SET'}")
        logger.info(f"  - ANTHROPIC_API_KEY: {'***' if os.getenv('ANTHROPIC_API_KEY') else 'NOT SET'}")

        logger.info("=" * 80)
        logger.info("Backend startup complete! Ready to accept requests.")
        logger.info("=" * 80)

        # Yield control to FastAPI (app is now running)
        yield

    except Exception as e:
        logger.error(f"❌ Critical error during startup: {e}", exc_info=True)
        raise

    finally:
        # ============================================================================
        # SHUTDOWN: Cleanup Resources
        # ============================================================================
        logger.info("=" * 80)
        logger.info("Shutting down AI Audit Platform Backend")
        logger.info("=" * 80)

        # Cleanup graph resources if needed
        if hasattr(app.state, 'graph') and app.state.graph:
            logger.info("Cleaning up LangGraph workflow...")
            # MemorySaver doesn't need explicit cleanup

        logger.info("✅ Shutdown complete")


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="AI Audit Platform API",
    description=(
        "Backend API for AI-powered accounting audit platform. "
        "Orchestrates LangGraph multi-agent workflows with Supabase persistence. "
        "Supports real-time streaming via SSE and Supabase Realtime."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc",  # ReDoc at /redoc
)


# ============================================================================
# CORS Middleware
# ============================================================================
# Allow frontend (React) to make cross-origin requests

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server (default)
        "http://localhost:3000",  # Alternative React dev server
        "http://127.0.0.1:5173",  # Alternative localhost format
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)


# ============================================================================
# Route Registration
# ============================================================================

# REST API routes: /api/projects/start, /api/tasks/approve, /api/health
app.include_router(routes.router)

# SSE streaming routes: /api/stream/{task_id}
app.include_router(sse.router, prefix="/api/stream", tags=["sse"])


# ============================================================================
# Root Health Check
# ============================================================================

@app.get("/", tags=["health"])
async def root():
    """Root endpoint - simple health check.

    Returns:
        Basic service information and status

    Usage:
        curl http://localhost:8000/
    """
    return {
        "service": "AI Audit Platform API",
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


# ============================================================================
# Development Helper: Run with uvicorn
# ============================================================================

if __name__ == "__main__":
    """
    Development server entry point.

    Run with:
        python -m src.main

    Or use uvicorn directly:
        uvicorn src.main:app --reload --port 8000

    For production:
        uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
    """
    import uvicorn

    logger.info("Starting development server with uvicorn...")
    uvicorn.run(
        "src.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
