"""Export API endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Session, Message
from app.services.pdf_export import generate_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["export"])


class ExportRequest(BaseModel):
    session_ids: list[str]


@router.post("/export/pdf")
async def export_sessions_pdf(
    body: ExportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Export one or more sessions as a combined PDF."""
    if not body.session_ids:
        raise HTTPException(status_code=400, detail="No session IDs provided")

    if len(body.session_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 sessions per export")

    sessions_data: list[dict] = []

    for sid in body.session_ids:
        # Fetch session
        result = await db.execute(select(Session).where(Session.id == sid))
        session = result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {sid} not found")

        # Fetch messages in order
        msg_result = await db.execute(
            select(Message)
            .where(Message.session_id == sid)
            .order_by(Message.sequence)
        )
        messages = msg_result.scalars().all()

        sessions_data.append({
            "source": session.source,
            "display": session.display,
            "project": session.project,
            "cwd": session.cwd,
            "model": session.model,
            "created_at": session.created_at.isoformat() if session.created_at else "",
            "message_count": session.message_count,
            "messages": [
                {
                    "type": m.type,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat() if m.timestamp else "",
                }
                for m in messages
            ],
        })

    logger.info(f"Generating PDF for {len(sessions_data)} session(s)")
    pdf_bytes = generate_pdf(sessions_data)

    # Build filename
    if len(sessions_data) == 1:
        title = (sessions_data[0].get("display") or "session")[:40]
        # Sanitize for filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in title).strip()
        filename = f"{safe_title}.pdf"
    else:
        filename = f"sessions_export_{len(sessions_data)}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
