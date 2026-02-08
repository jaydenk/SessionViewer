"""Subagent API endpoints."""
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Subagent, Session, Message
from app.schemas import SubagentResponse, MessageResponse
from app.services.claude_parser import parse_claude_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["subagents"])


@router.get("/{session_id}/subagents", response_model=list[SubagentResponse])
async def get_session_subagents(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all subagents for a session.
    """
    # Verify session exists
    session_query = select(Session).where(Session.id == session_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get subagents
    query = select(Subagent).where(Subagent.session_id == session_id)
    result = await db.execute(query)
    subagents = result.scalars().all()

    return [SubagentResponse.model_validate(s) for s in subagents]


@router.get("/{session_id}/subagents/{agent_id}/messages")
async def get_subagent_messages(
    session_id: str,
    agent_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get messages for a specific subagent.
    Lazily loads and parses the subagent file if needed.
    """
    # Get subagent record
    query = select(Subagent).where(
        Subagent.session_id == session_id,
        Subagent.agent_id == agent_id,
    )
    result = await db.execute(query)
    subagent = result.scalar_one_or_none()

    if not subagent:
        raise HTTPException(status_code=404, detail="Subagent not found")

    # Check if we have cached messages
    msg_query = select(Message).where(
        Message.session_id == session_id,
        Message.agent_id == agent_id,
    ).order_by(Message.sequence)
    msg_result = await db.execute(msg_query)
    messages = msg_result.scalars().all()

    if messages:
        return [MessageResponse.model_validate(m) for m in messages]

    # Parse subagent file if we have the path
    if subagent.file_path:
        try:
            from pathlib import Path
            parsed = await parse_claude_session(Path(subagent.file_path))
            if parsed is None:
                return []
            messages_data = parsed["messages"]

            # Cache messages
            for msg_data in messages_data:
                message = Message(
                    session_id=session_id,
                    agent_id=agent_id,
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

            # Update subagent metadata
            subagent.message_count = len(messages_data)
            if messages_data:
                first_msg = messages_data[0]
                content = json.loads(first_msg["content"])
                if "content" in content:
                    text = content.get("content", "")[:200]
                    subagent.first_message = text

            await db.commit()

            # Return cached messages
            msg_result = await db.execute(msg_query)
            messages = msg_result.scalars().all()
            return [MessageResponse.model_validate(m) for m in messages]

        except Exception as e:
            logger.error(f"[Subagents] Failed to parse subagent file {subagent.file_path}: {e}")
            raise HTTPException(status_code=500, detail="Failed to load subagent messages")

    return []
