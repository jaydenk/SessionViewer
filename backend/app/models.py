"""SQLAlchemy ORM models for session storage."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def generate_uuid() -> str:
    """Generate a UUID string."""
    return str(uuid.uuid4())


class Session(Base):
    """Main session table - one row per conversation session."""
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)  # 'claude' or 'codex'
    project: Mapped[str | None] = mapped_column(String, nullable=True)  # Decoded project path
    cwd: Mapped[str | None] = mapped_column(Text, nullable=True)  # Working directory
    model: Mapped[str | None] = mapped_column(String, nullable=True)  # Model used
    display: Mapped[str | None] = mapped_column(Text, nullable=True)  # First user message for list view
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subagent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    has_tool_results: Mapped[bool] = mapped_column(Boolean, default=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # Absolute path to source .jsonl
    indexed_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="Message.sequence"
    )
    subagents: Mapped[list["Subagent"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )
    tool_results: Mapped[list["ToolResult"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )
    associated_files: Mapped[list["AssociatedFile"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_sessions_source", "source"),
        Index("idx_sessions_project", "project"),
        Index("idx_sessions_created_at", "created_at"),
        Index("idx_sessions_display", "display"),
    )


class Message(Base):
    """Individual messages within sessions."""
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    parent_uuid: Mapped[str | None] = mapped_column(String, nullable=True)  # Threading support
    type: Mapped[str] = mapped_column(String, nullable=False)  # 'user' or 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Full JSON content
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)  # First 200 chars
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)  # Order within session
    agent_id: Mapped[str | None] = mapped_column(String, nullable=True)  # For subagent messages
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    usage_input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usage_output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_messages_session_sequence", "session_id", "sequence"),
        Index("idx_messages_parent_uuid", "parent_uuid"),
        Index("idx_messages_agent_id", "agent_id"),
    )


class Subagent(Base):
    """Subagent metadata."""
    __tablename__ = "subagents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str] = mapped_column(String, nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    first_message: Mapped[str | None] = mapped_column(Text, nullable=True)  # Preview
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)  # Path to subagent .jsonl

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="subagents")

    __table_args__ = (
        Index("idx_subagents_session", "session_id"),
        Index("idx_subagents_agent_id", "agent_id"),
    )


class ToolResult(Base):
    """Cached tool outputs - loaded on-demand."""
    __tablename__ = "tool_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    tool_use_id: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)  # Cached content
    content_preview: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)  # Path to tool result file

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="tool_results")

    __table_args__ = (
        Index("idx_tool_results_session", "session_id"),
        Index("idx_tool_results_tool_use_id", "tool_use_id"),
    )


class AssociatedFile(Base):
    """Associated files like TODOs, plans, debug logs."""
    __tablename__ = "associated_files"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_uuid)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    file_type: Mapped[str] = mapped_column(String, nullable=False)  # 'todo', 'plan', 'debug'
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationships
    session: Mapped["Session"] = relationship(back_populates="associated_files")

    __table_args__ = (
        Index("idx_associated_files_session", "session_id"),
        Index("idx_associated_files_type", "file_type"),
    )
