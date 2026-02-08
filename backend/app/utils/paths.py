"""Path encoding/decoding utilities."""
import re
from pathlib import Path


def decode_project_path(encoded: str) -> str:
    """
    Decode a project path from Claude's encoding format.

    Example: '-Users-kerrj-Documents-Development-Researcher' -> '/Users/kerrj/Documents/Development/Researcher'

    Args:
        encoded: Encoded project path string

    Returns:
        Decoded absolute path string
    """
    if not encoded:
        return ""

    # Remove leading dash and replace remaining dashes with slashes
    if encoded.startswith("-"):
        encoded = encoded[1:]

    decoded = encoded.replace("-", "/")

    # Ensure it starts with /
    if not decoded.startswith("/"):
        decoded = "/" + decoded

    return decoded


def encode_project_path(path: str) -> str:
    """
    Encode a project path to Claude's format.

    Example: '/Users/kerrj/Documents/Development/Researcher' -> '-Users-kerrj-Documents-Development-Researcher'

    Args:
        path: Absolute path string

    Returns:
        Encoded path string
    """
    if not path:
        return ""

    # Remove leading slash and replace remaining slashes with dashes
    if path.startswith("/"):
        path = path[1:]

    return "-" + path.replace("/", "-")


def get_project_from_path(file_path: Path, cwd: str | None = None) -> str | None:
    """
    Extract project path from a session file path.

    Prefers `cwd` (the actual working directory from the session) over
    decoding the directory name, since the directory-name encoding is lossy
    (dashes in project names become slashes).

    Args:
        file_path: Path to session file
        cwd: Working directory from the session data (preferred source)

    Returns:
        Project path or None
    """
    if cwd:
        return cwd

    parts = file_path.parts

    # Fallback: decode from Claude project directory name
    try:
        projects_idx = parts.index("projects")
        if projects_idx + 1 < len(parts):
            encoded_project = parts[projects_idx + 1]
            return decode_project_path(encoded_project)
    except (ValueError, IndexError):
        pass

    return None


def get_session_id_from_path(file_path: Path) -> str | None:
    """
    Extract session ID from a session file path.

    Args:
        file_path: Path to session file

    Returns:
        Session UUID or None
    """
    # Session ID is typically the filename without extension
    stem = file_path.stem

    # Validate it looks like a UUID
    if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', stem):
        return stem

    return None
