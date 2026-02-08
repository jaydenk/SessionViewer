"""Main FastAPI application."""
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func

from app.database import init_db, ping_db, async_session
from app.config import settings
from app.routers import sessions, messages, subagents, index
from app.models import Session
from app.services.indexer import index_all_sessions

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    start_time = time.monotonic()
    logger.info("[App] Starting Session Viewer API")

    # Create data directory
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # Initialize database
    await init_db()

    # Check if database is empty and trigger initial indexing
    async with async_session() as db:
        result = await db.execute(select(func.count()).select_from(Session))
        count = result.scalar() or 0

        if count == 0:
            logger.info("[App] Database is empty, starting initial indexing...")
            await index_all_sessions(db, force=False)

    elapsed_ms = int((time.monotonic() - start_time) * 1000)
    logger.info(f"[App] Startup complete ({elapsed_ms}ms)")

    yield

    logger.info("[App] Shutting down Session Viewer API")


app = FastAPI(
    title="Session Viewer API",
    description="API for viewing Claude Code and Codex AI assistant sessions",
    version="1.0.0",
    lifespan=lifespan,
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request, call_next):
    """Log all HTTP requests with timing."""
    request_id = uuid.uuid4().hex[:8]
    start = time.perf_counter()

    # Log incoming request
    content_length = request.headers.get("content-length", "0")
    logger.info(
        f"[REQUEST] {request_id} --> {request.method} {request.url.path} (body={content_length}b)"
    )

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = int((time.perf_counter() - start) * 1000)
        logger.exception(
            f"[REQUEST] {request_id} <-- {request.method} {request.url.path} EXCEPTION in {duration_ms}ms"
        )
        raise

    duration_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        f"[REQUEST] {request_id} <-- {response.status_code} {request.method} {request.url.path} ({duration_ms}ms)"
    )

    return response


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(sessions.router, prefix=settings.api_prefix)
app.include_router(messages.router, prefix=settings.api_prefix)
app.include_router(subagents.router, prefix=settings.api_prefix)
app.include_router(index.router, prefix=settings.api_prefix)


# Health check endpoint
@app.get(f"{settings.api_prefix}/healthz")
async def healthz():
    """Health check endpoint."""
    try:
        await ping_db()
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"[Health] Database check failed: {e}")
        return {"status": "error", "message": str(e)}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Session Viewer API",
        "version": "1.0.0",
        "docs": "/docs",
    }
