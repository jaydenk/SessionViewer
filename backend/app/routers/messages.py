"""Message API endpoints."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Message, Session
from app.schemas import MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["messages"])


@router.get("/{session_id}/messages", response_model=list[MessageResponse])
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all messages for a session, ordered by sequence.
    """
    # Verify session exists
    session_query = select(Session).where(Session.id == session_id)
    session_result = await db.execute(session_query)
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages
    query = select(Message).where(Message.session_id == session_id).order_by(Message.sequence)
    result = await db.execute(query)
    messages = result.scalars().all()

    return [MessageResponse.model_validate(m) for m in messages]


@router.get("/{session_id}/messages/{message_id}", response_model=MessageResponse)
async def get_message(
    session_id: str,
    message_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific message by ID.
    """
    query = select(Message).where(
        Message.id == message_id,
        Message.session_id == session_id,
    )
    result = await db.execute(query)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    return MessageResponse.model_validate(message)
