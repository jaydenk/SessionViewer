"""Main indexing orchestration service."""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Session, Message, Subagent, AssociatedFile
from app.services.claude_parser import parse_claude_session, find_claude_subagents
from app.services.codex_parser import parse_codex_session
from app.services.file_scanner import scan_claude_sessions, scan_codex_sessions, find_associated_files
from app.utils.paths import get_project_from_path

logger = logging.getLogger(__name__)

# Global indexing state
_is_indexing = False
_last_indexed: datetime | None = None


async def is_indexing() -> bool:
    """Check if indexing is currently in progress."""
    return _is_indexing


async def get_last_indexed() -> datetime | None:
    """Get the last indexed timestamp."""
    return _last_indexed


async def index_all_sessions(db: AsyncSession, force: bool = False) -> dict[str, int]:
    """
    Index all sessions from Claude and Codex directories.

    Args:
        db: Database session
        force: If True, re-index all sessions even if already indexed

    Returns:
        Dictionary with counts
    """
    global _is_indexing, _last_indexed

    if _is_indexing:
        logger.warning("[Indexer] Indexing already in progress")
        return {"status": "already_running"}

    _is_indexing = True
    start_time = datetime.utcnow()

    try:
        logger.info("[Indexer] Starting session indexing")

        counts = {
            "claude_sessions": 0,
            "codex_sessions": 0,
            "total_messages": 0,
            "errors": 0,
        }

        # Index Claude sessions
        logger.info("[Indexer] Indexing Claude sessions...")
        claude_count, claude_messages, claude_errors = await _index_claude_sessions(db, force)
        counts["claude_sessions"] = claude_count
        counts["total_messages"] += claude_messages
        counts["errors"] += claude_errors

        # Index Codex sessions
        logger.info("[Indexer] Indexing Codex sessions...")
        codex_count, codex_messages, codex_errors = await _index_codex_sessions(db, force)
        counts["codex_sessions"] = codex_count
        counts["total_messages"] += codex_messages
        counts["errors"] += codex_errors

        _last_indexed = datetime.utcnow()
        duration = (_last_indexed - start_time).total_seconds()

        logger.info(
            f"[Indexer] Completed in {duration:.1f}s: "
            f"{counts['claude_sessions']} Claude, "
            f"{counts['codex_sessions']} Codex, "
            f"{counts['total_messages']} messages, "
            f"{counts['errors']} errors"
        )

        return counts

    except Exception as e:
        logger.error(f"[Indexer] Failed: {e}", exc_info=True)
        counts["errors"] += 1
        return counts

    finally:
        _is_indexing = False


async def _index_claude_sessions(db: AsyncSession, force: bool) -> tuple[int, int, int]:
    """Index Claude Code sessions."""
    session_count = 0
    message_count = 0
    error_count = 0

    for file_path in scan_claude_sessions(settings.claude_dir):
        try:
            # Check if already indexed
            if not force:
                result = await db.execute(
                    select(Session).where(Session.file_path == str(file_path))
                )
                if result.scalar_one_or_none():
                    continue

            # Parse session
            parsed = await parse_claude_session(file_path)

            # Skip empty sessions (only file-history-snapshot entries)
            if parsed is None:
                continue

            session_data = parsed["session"]
            messages_data = parsed["messages"]

            # Get project from path, preferring cwd from session data
            project = get_project_from_path(file_path, cwd=session_data.get("cwd"))
            if project:
                session_data["project"] = project

            # Create session record
            session = Session(
                id=session_data["id"],
                source=session_data["source"],
                project=session_data.get("project"),
                cwd=session_data.get("cwd"),
                model=session_data.get("model"),
                display=session_data.get("display"),
                created_at=session_data["created_at"] or datetime.utcnow(),
                updated_at=session_data["updated_at"] or datetime.utcnow(),
                message_count=session_data["message_count"],
                subagent_count=0,
                has_tool_results=False,
                file_path=session_data["file_path"],
            )

            db.add(session)

            # Batch insert messages
            for msg_data in messages_data:
                message = Message(
                    session_id=session.id,
                    type=msg_data["type"],
                    content=msg_data["content"],
                    content_preview=msg_data.get("content_preview"),
                    timestamp=msg_data["timestamp"],
                    sequence=msg_data["sequence"],
                    parent_uuid=msg_data.get("parent_uuid"),
                    model=msg_data.get("model"),
                    usage_input_tokens=msg_data.get("usage_input_tokens"),
                    usage_output_tokens=msg_data.get("usage_output_tokens"),
                )
                db.add(message)

            # Find and index subagents
            project_dir = file_path.parent
            subagent_files = await find_claude_subagents(session.id, project_dir)
            for subagent_file in subagent_files:
                agent_id = subagent_file.stem
                subagent = Subagent(
                    session_id=session.id,
                    agent_id=agent_id,
                    file_path=str(subagent_file),
                )
                db.add(subagent)
                session.subagent_count += 1

            # Find and index associated files
            assoc_files = find_associated_files(session.id, settings.claude_dir)
            for file_type, file_path_obj in assoc_files.items():
                if file_path_obj and file_path_obj.exists():
                    try:
                        content = file_path_obj.read_text(encoding="utf-8")
                        assoc_file = AssociatedFile(
                            session_id=session.id,
                            file_type=file_type,
                            content=content,
                            file_path=str(file_path_obj),
                        )
                        db.add(assoc_file)
                    except Exception as e:
                        logger.warning(f"[Indexer] Failed to read {file_path_obj}: {e}")

            await db.commit()

            session_count += 1
            message_count += len(messages_data)

            if session_count % 10 == 0:
                logger.info(f"[Indexer] Indexed {session_count} Claude sessions...")

        except Exception as e:
            logger.error(f"[Indexer] Failed to index Claude session {file_path}: {type(e).__name__}: {e}")
            error_count += 1
            await db.rollback()

    return session_count, message_count, error_count


async def _index_codex_sessions(db: AsyncSession, force: bool) -> tuple[int, int, int]:
    """Index Codex sessions."""
    session_count = 0
    message_count = 0
    error_count = 0

    for file_path in scan_codex_sessions(settings.codex_dir):
        try:
            # Check if already indexed
            if not force:
                result = await db.execute(
                    select(Session).where(Session.file_path == str(file_path))
                )
                if result.scalar_one_or_none():
                    continue

            # Parse session
            parsed = await parse_codex_session(file_path)

            if parsed is None:
                continue

            session_data = parsed["session"]
            messages_data = parsed["messages"]

            # Use filename stem as session ID for Codex (to ensure uniqueness)
            session_id = file_path.stem

            # Create session record
            session = Session(
                id=session_id,
                source=session_data["source"],
                project=session_data.get("project"),
                cwd=session_data.get("cwd"),
                model=session_data.get("model"),
                display=session_data.get("display"),
                created_at=session_data["created_at"] or datetime.utcnow(),
                updated_at=session_data["updated_at"] or datetime.utcnow(),
                message_count=session_data["message_count"],
                subagent_count=0,
                has_tool_results=False,
                file_path=session_data["file_path"],
            )

            db.add(session)

            # Batch insert messages
            for msg_data in messages_data:
                message = Message(
                    session_id=session_id,
                    type=msg_data["type"],
                    content=msg_data["content"],
                    content_preview=msg_data.get("content_preview"),
                    timestamp=msg_data["timestamp"],
                    sequence=msg_data["sequence"],
                    parent_uuid=msg_data.get("parent_uuid"),
                )
                db.add(message)

            await db.commit()

            session_count += 1
            message_count += len(messages_data)

            if session_count % 10 == 0:
                logger.info(f"[Indexer] Indexed {session_count} Codex sessions...")

        except Exception as e:
            logger.error(f"[Indexer] Failed to index Codex session {file_path}: {type(e).__name__}: {e}")
            error_count += 1
            await db.rollback()

    return session_count, message_count, error_count
