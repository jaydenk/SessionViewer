"""Application configuration."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Paths (default to Docker paths, override with environment)
    data_dir: Path = Path("./data")
    claude_dir: Path = Path("/mnt/claude")
    codex_dir: Path = Path("/mnt/codex")

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/sessions.db"

    # Indexing
    reindex_interval_minutes: int = 30  # 0 = disabled

    # Logging
    log_level: str = "INFO"

    # API
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

# When running locally (not Docker), use home directory paths if the
# Docker mount paths don't exist
if not settings.claude_dir.exists():
    home_claude = Path.home() / ".claude"
    if home_claude.exists():
        settings.claude_dir = home_claude

if not settings.codex_dir.exists():
    home_codex = Path.home() / ".codex"
    if home_codex.exists():
        settings.codex_dir = home_codex
