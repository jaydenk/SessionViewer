"""Parser for Claude Code JSONL session files."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.utils.jsonl import read_jsonl, create_content_preview, extract_text_from_content, strip_xml_tags, is_system_message

logger = logging.getLogger(__name__)


async def parse_claude_session(file_path: Path) -> dict[str, Any]:
    """
    Parse a Claude Code session JSONL file.

    Args:
        file_path: Path to the session JSONL file

    Returns:
        Dictionary with session metadata and messages
    """
    messages = []
    session_meta = {
        "id": file_path.stem,
        "source": "claude",
        "cwd": None,
        "model": None,
        "created_at": None,
        "updated_at": None,
        "file_path": str(file_path),
    }

    first_user_message = None
    sequence = 0

    try:
        async for entry in read_jsonl(file_path):
            entry_type = entry.get("type")
            timestamp_str = entry.get("timestamp")
            timestamp = None

            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    timestamp = datetime.utcnow()

            # Update session metadata
            if not session_meta["created_at"] and timestamp:
                session_meta["created_at"] = timestamp
            if timestamp:
                session_meta["updated_at"] = timestamp

            if "cwd" in entry and not session_meta["cwd"]:
                session_meta["cwd"] = entry["cwd"]

            # Parse messages (skip progress entries — they are hook_progress,
            # bash_progress, etc. with no conversation content)
            if entry_type == "user":
                message_content = entry.get("message", {})
                content_json = json.dumps(message_content)

                # Extract first user message for display
                if not first_user_message:
                    text = extract_text_from_content(message_content)
                    cleaned = strip_xml_tags(text)
                    # Skip plan content and system messages
                    if (cleaned
                            and not cleaned.startswith("Implement the following plan:")
                            and not is_system_message(text)):
                        first_user_message = cleaned[:200]

                messages.append({
                    "type": "user",
                    "content": content_json,
                    "content_preview": create_content_preview(content_json),
                    "timestamp": timestamp or datetime.utcnow(),
                    "sequence": sequence,
                    "uuid": entry.get("uuid"),
                    "parent_uuid": entry.get("parentUuid"),
                })
                sequence += 1

            elif entry_type == "assistant":
                message_content = entry.get("message", {})
                content_json = json.dumps(message_content)

                # Extract model info
                if not session_meta["model"] and "model" in message_content:
                    session_meta["model"] = message_content["model"]

                # Extract usage info
                usage = message_content.get("usage", {})
                input_tokens = usage.get("input_tokens")
                output_tokens = usage.get("output_tokens")

                messages.append({
                    "type": "assistant",
                    "content": content_json,
                    "content_preview": create_content_preview(content_json),
                    "timestamp": timestamp or datetime.utcnow(),
                    "sequence": sequence,
                    "uuid": entry.get("uuid"),
                    "parent_uuid": entry.get("parentUuid"),
                    "model": message_content.get("model"),
                    "usage_input_tokens": input_tokens,
                    "usage_output_tokens": output_tokens,
                })
                sequence += 1

    except Exception as e:
        logger.error(f"[Claude Parser] Failed to parse {file_path}: {e}")
        raise

    # Set display text
    session_meta["display"] = first_user_message or "No user message"
    session_meta["message_count"] = len(messages)

    # Skip sessions with no actual messages (only file-history-snapshot entries)
    if len(messages) == 0:
        return None

    return {
        "session": session_meta,
        "messages": messages,
    }


async def find_claude_subagents(session_id: str, project_dir: Path) -> list[Path]:
    """
    Find subagent JSONL files for a Claude session.

    Args:
        session_id: Session UUID
        project_dir: Project directory path

    Returns:
        List of subagent file paths
    """
    subagent_dir = project_dir / session_id / "subagents"

    if not subagent_dir.exists() or not subagent_dir.is_dir():
        return []

    return list(subagent_dir.glob("*.jsonl"))


async def find_claude_tool_results(session_id: str, project_dir: Path) -> list[Path]:
    """
    Find tool result files for a Claude session.

    Args:
        session_id: Session UUID
        project_dir: Project directory path

    Returns:
        List of tool result file paths
    """
    tool_results_dir = project_dir / session_id / "tool-results"

    if not tool_results_dir.exists() or not tool_results_dir.is_dir():
        return []

    return list(tool_results_dir.glob("*"))
