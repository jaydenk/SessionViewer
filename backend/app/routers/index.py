"""Indexing API endpoints."""
import asyncio
import logging

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Session
from app.schemas import IndexStatus
from app.services.indexer import index_all_sessions, is_indexing, get_last_indexed

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/index", tags=["index"])


@router.get("/status", response_model=IndexStatus)
async def get_index_status(
    db: AsyncSession = Depends(get_db),
):
    """
    Get current indexing status and statistics.
    """
    # Get counts
    total_query = select(func.count()).select_from(Session)
    claude_query = select(func.count()).select_from(Session).where(Session.source == "claude")
    codex_query = select(func.count()).select_from(Session).where(Session.source == "codex")

    total_result = await db.execute(total_query)
    claude_result = await db.execute(claude_query)
    codex_result = await db.execute(codex_query)

    total = total_result.scalar() or 0
    claude = claude_result.scalar() or 0
    codex = codex_result.scalar() or 0

    return IndexStatus(
        is_indexing=await is_indexing(),
        last_indexed=await get_last_indexed(),
        total_sessions=total,
        claude_sessions=claude,
        codex_sessions=codex,
    )


@router.post("/refresh")
async def refresh_index(
    background_tasks: BackgroundTasks,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a background re-index of all sessions.

    Args:
        force: If True, re-index all sessions even if already indexed
    """
    if await is_indexing():
        return {"status": "already_running"}

    # Run indexing in background
    background_tasks.add_task(index_all_sessions, db, force)

    return {"status": "started"}
