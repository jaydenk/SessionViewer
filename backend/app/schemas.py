"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from pydantic import BaseModel, Field


# Session schemas
class SessionBase(BaseModel):
    """Base session fields."""
    source: str
    project: str | None = None
    cwd: str | None = None
    model: str | None = None
    display: str | None = None


class SessionCreate(SessionBase):
    """Schema for creating a session."""
    id: str
    created_at: datetime
    updated_at: datetime
    file_path: str


class SessionListItem(SessionBase):
    """Schema for session list items."""
    id: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    subagent_count: int
    has_tool_results: bool

    class Config:
        from_attributes = True


class SessionDetail(SessionListItem):
    """Schema for detailed session view."""
    file_path: str
    indexed_at: datetime

    class Config:
        from_attributes = True


class SessionsResponse(BaseModel):
    """Schema for paginated session list response."""
    sessions: list[SessionListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# Message schemas
class MessageBase(BaseModel):
    """Base message fields."""
    type: str
    content: str
    timestamp: datetime


class MessageCreate(MessageBase):
    """Schema for creating a message."""
    session_id: str
    sequence: int
    parent_uuid: str | None = None
    content_preview: str | None = None
    agent_id: str | None = None
    model: str | None = None
    usage_input_tokens: int | None = None
    usage_output_tokens: int | None = None


class MessageResponse(MessageBase):
    """Schema for message response."""
    id: str
    session_id: str
    sequence: int
    parent_uuid: str | None = None
    content_preview: str | None = None
    agent_id: str | None = None
    model: str | None = None
    usage_input_tokens: int | None = None
    usage_output_tokens: int | None = None

    class Config:
        from_attributes = True


# Subagent schemas
class SubagentBase(BaseModel):
    """Base subagent fields."""
    agent_id: str
    message_count: int
    first_message: str | None = None


class SubagentCreate(SubagentBase):
    """Schema for creating a subagent."""
    session_id: str
    file_path: str | None = None


class SubagentResponse(SubagentBase):
    """Schema for subagent response."""
    id: str
    session_id: str
    file_path: str | None = None

    class Config:
        from_attributes = True


# Tool result schemas
class ToolResultBase(BaseModel):
    """Base tool result fields."""
    tool_use_id: str
    content_preview: str | None = None


class ToolResultCreate(ToolResultBase):
    """Schema for creating a tool result."""
    session_id: str
    content: str | None = None
    file_path: str | None = None


class ToolResultResponse(ToolResultBase):
    """Schema for tool result response."""
    id: str
    session_id: str
    content: str | None = None
    file_path: str | None = None

    class Config:
        from_attributes = True


# Associated file schemas
class AssociatedFileBase(BaseModel):
    """Base associated file fields."""
    file_type: str
    file_path: str


class AssociatedFileCreate(AssociatedFileBase):
    """Schema for creating an associated file."""
    session_id: str
    content: str | None = None


class AssociatedFileResponse(AssociatedFileBase):
    """Schema for associated file response."""
    id: str
    session_id: str
    content: str | None = None

    class Config:
        from_attributes = True


# Project schemas
class ProjectInfo(BaseModel):
    """Schema for project info with last activity date."""
    project: str
    last_activity: datetime


# Filter schemas
class SessionFilters(BaseModel):
    """Schema for session filtering."""
    source: str | None = None  # 'claude' or 'codex'
    project: str | None = None
    search: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=100)


# Index status schemas
class IndexStatus(BaseModel):
    """Schema for indexing status."""
    is_indexing: bool
    last_indexed: datetime | None = None
    total_sessions: int
    claude_sessions: int
    codex_sessions: int
