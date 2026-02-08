"""Database configuration and connection management."""
import logging
import time

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text, event
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# SQLite optimizations for concurrency
SQLITE_PRAGMAS = [
    "PRAGMA journal_mode=WAL",      # Write-Ahead Logging for better concurrency
    "PRAGMA busy_timeout=5000",     # Wait 5s for locks instead of failing immediately
    "PRAGMA synchronous=NORMAL",    # Good balance of safety and speed
    "PRAGMA foreign_keys=ON",       # Enforce foreign key constraints
]

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,  # Check connections before use
    connect_args={"timeout": 30},  # Connection timeout
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Apply pragmas on connection
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Apply SQLite pragmas on connection."""
    cursor = dbapi_connection.cursor()
    for pragma in SQLITE_PRAGMAS:
        cursor.execute(pragma)
    cursor.close()


# Log slow queries
@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Track query start time."""
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries."""
    start_time = conn.info["query_start_time"].pop()
    duration_ms = (time.perf_counter() - start_time) * 1000
    if duration_ms > 500:  # Log queries over 500ms
        logger.warning(f"[DB] Slow query ({duration_ms:.0f}ms): {statement[:100]}")


async def get_db():
    """Dependency for getting database sessions."""
    async with async_session() as session:
        yield session


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("[DB] Database initialized")


async def ping_db():
    """Check database connection."""
    async with async_session() as session:
        await session.execute(text("SELECT 1"))
