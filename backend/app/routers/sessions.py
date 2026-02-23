"""Session API endpoints."""
import logging
from datetime import datetime
from math import ceil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Session, AssociatedFile
from app.schemas import SessionsResponse, SessionListItem, SessionDetail, AssociatedFileResponse, ProjectInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionsResponse)
async def list_sessions(
    source: str | None = Query(None, description="Filter by source: 'claude' or 'codex'"),
    project: str | None = Query(None, description="Filter by project path"),
    search: str | None = Query(None, description="Search in display text"),
    date_from: datetime | None = Query(None, description="Filter by start date"),
    date_to: datetime | None = Query(None, description="Filter by end date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    List sessions with filters and pagination.
    """
    # Build query
    query = select(Session)

    # Apply filters
    if source:
        query = query.where(Session.source == source)

    if project:
        query = query.where(Session.project == project)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Session.display.ilike(search_pattern),
                Session.project.ilike(search_pattern),
                Session.cwd.ilike(search_pattern),
            )
        )

    if date_from:
        query = query.where(Session.created_at >= date_from)

    if date_to:
        query = query.where(Session.created_at <= date_to)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(Session.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    # Execute query
    result = await db.execute(query)
    sessions = result.scalars().all()

    return SessionsResponse(
        sessions=[SessionListItem.model_validate(s) for s in sessions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed session information.
    """
    query = select(Session).where(Session.id == session_id)
    result = await db.execute(query)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetail.model_validate(session)


@router.get("/{session_id}/files", response_model=list[AssociatedFileResponse])
async def get_session_files(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get associated files for a session (TODO, plan, debug logs).
    """
    query = select(AssociatedFile).where(AssociatedFile.session_id == session_id)
    result = await db.execute(query)
    files = result.scalars().all()

    return [AssociatedFileResponse.model_validate(f) for f in files]


@router.get("/projects/list", response_model=list[ProjectInfo])
async def list_projects(
    db: AsyncSession = Depends(get_db),
):
    """
    Get list of unique project paths with last activity date.
    """
    query = (
        select(
            Session.project,
            func.max(Session.updated_at).label("last_activity"),
        )
        .where(Session.project.isnot(None))
        .group_by(Session.project)
        .order_by(Session.project)
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        ProjectInfo(project=row.project, last_activity=row.last_activity)
        for row in rows
        if row.project
    ]


@router.get("/projects/{project:path}/files", response_model=list[AssociatedFileResponse])
async def get_project_files(
    project: str,
):
    """
    Get markdown files from the project directory.
    """
    # Ensure path is absolute
    if not project.startswith('/'):
        project = '/' + project

    project_path = Path(project)

    if not project_path.exists() or not project_path.is_dir():
        logger.warning(f"[Project Files] Path not found or not a directory: {project_path}")
        return []

    files = []

    # Directories to skip (dependencies, build outputs, caches, etc.)
    skip_dirs = {
        "node_modules", ".venv", "venv", ".git", "vendor", "__pycache__",
        ".tox", ".mypy_cache", ".pytest_cache", "dist", "build", ".next",
        ".svelte-kit", ".nuxt", "target", ".cargo", "Pods", ".build",
        ".egg-info", ".eggs", "site-packages", ".cache",
    }

    # Filenames to skip (common non-project docs)
    skip_filenames = {"license.md", "licence.md"}

    # Find all .md files recursively, skipping dependency directories
    for md_file in project_path.rglob("*.md"):
        if not md_file.is_file():
            continue

        # Skip files inside dependency/build directories
        if skip_dirs.intersection(md_file.relative_to(project_path).parts):
            continue

        # Skip licence/license files
        if md_file.name.lower() in skip_filenames:
            continue

        try:
            content = md_file.read_text(encoding="utf-8")
            relative_path = md_file.relative_to(project_path)
            files.append(
                AssociatedFileResponse(
                    id=str(md_file),
                    session_id="",  # Not tied to a specific session
                    file_type=f"project_{relative_path}",
                    content=content,
                    file_path=str(md_file),
                )
            )
        except Exception as e:
            logger.warning(f"Failed to read {md_file}: {e}")
            continue

    # Sort by relative path (root files first, then subdirectories)
    files.sort(key=lambda f: (f.file_type.count('/'), f.file_type))

    return files
