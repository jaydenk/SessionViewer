"""File system scanning for session files."""
import logging
from pathlib import Path
from typing import Iterator

logger = logging.getLogger(__name__)


def scan_claude_sessions(claude_dir: Path) -> Iterator[Path]:
    """
    Scan Claude projects directory for session files.

    Args:
        claude_dir: Path to ~/.claude directory

    Yields:
        Paths to session JSONL files
    """
    projects_dir = claude_dir / "projects"

    if not projects_dir.exists():
        logger.warning(f"[Scanner] Claude projects directory not found: {projects_dir}")
        return

    logger.info(f"[Scanner] Scanning Claude sessions in {projects_dir}")

    # Find all .jsonl files in projects/*/
    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Skip special directories
        if project_dir.name.startswith("."):
            continue

        # Find session files (exclude subagents and tool-results subdirs)
        for jsonl_file in project_dir.glob("*.jsonl"):
            if jsonl_file.is_file():
                yield jsonl_file


def scan_codex_sessions(codex_dir: Path) -> Iterator[Path]:
    """
    Scan Codex sessions directory for session files.

    Args:
        codex_dir: Path to ~/.codex directory

    Yields:
        Paths to session JSONL files
    """
    sessions_dir = codex_dir / "sessions"

    if not sessions_dir.exists():
        logger.warning(f"[Scanner] Codex sessions directory not found: {sessions_dir}")
        return

    logger.info(f"[Scanner] Scanning Codex sessions in {sessions_dir}")

    # Find all .jsonl files in sessions/YYYY/MM/DD/
    for year_dir in sessions_dir.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue

        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue

            for day_dir in month_dir.iterdir():
                if not day_dir.is_dir() or not day_dir.name.isdigit():
                    continue

                # Find session files
                for jsonl_file in day_dir.glob("*.jsonl"):
                    if jsonl_file.is_file():
                        yield jsonl_file


def find_associated_files(
    session_id: str,
    claude_dir: Path,
) -> dict[str, Path]:
    """
    Find associated files for a session (TODO, plan, debug logs, artifacts).

    Args:
        session_id: Session UUID
        claude_dir: Path to ~/.claude directory

    Returns:
        Dictionary with file types/names and paths
    """
    files = {}

    # Check TODO file
    todo_path = claude_dir / "todos" / f"{session_id}.md"
    if todo_path.exists():
        files["todo"] = todo_path

    # Check plan file
    plan_path = claude_dir / "plans" / f"{session_id}.md"
    if plan_path.exists():
        files["plan"] = plan_path

    # Check debug logs
    debug_path = claude_dir / "debug" / f"{session_id}.log"
    if debug_path.exists():
        files["debug"] = debug_path

    # Find session directory and scan for markdown/text artifacts
    # Session could be in any project directory
    projects_dir = claude_dir / "projects"
    if projects_dir.exists():
        for project_dir in projects_dir.iterdir():
            if not project_dir.is_dir():
                continue

            session_dir = project_dir / session_id
            if session_dir.exists() and session_dir.is_dir():
                # Find markdown and text files in session directory
                for file_path in session_dir.iterdir():
                    if not file_path.is_file():
                        continue

                    # Skip the main session file
                    if file_path.suffix == ".jsonl" and file_path.stem == session_id:
                        continue

                    # Include markdown, text, and other common document types
                    if file_path.suffix in [".md", ".txt", ".log", ".json"]:
                        # Use filename as key for artifacts
                        file_key = f"artifact_{file_path.name}"
                        files[file_key] = file_path

                # Also check subdirectories for interesting files
                for subdir in ["output", "artifacts", "docs"]:
                    subdir_path = session_dir / subdir
                    if subdir_path.exists() and subdir_path.is_dir():
                        for file_path in subdir_path.rglob("*"):
                            if file_path.is_file() and file_path.suffix in [".md", ".txt", ".log", ".json"]:
                                # Include subdirectory in key
                                rel_path = file_path.relative_to(session_dir)
                                file_key = f"artifact_{rel_path.as_posix().replace('/', '_')}"
                                files[file_key] = file_path

    return files
