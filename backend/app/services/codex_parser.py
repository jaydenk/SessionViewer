"""Parser for Codex JSONL session files."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from app.utils.jsonl import read_jsonl, create_content_preview, extract_text_from_content, strip_xml_tags, is_system_message

logger = logging.getLogger(__name__)


async def parse_codex_session(file_path: Path) -> dict[str, Any]:
    """
    Parse a Codex session JSONL file.

    Args:
        file_path: Path to the session JSONL file

    Returns:
        Dictionary with session metadata and messages
    """
    messages = []
    session_meta = {
        "id": None,
        "source": "codex",
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
            payload = entry.get("payload", {})
            timestamp = None

            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    timestamp = datetime.utcnow()

            # Parse session metadata
            if entry_type == "session_meta":
                session_meta["id"] = payload.get("id", file_path.stem)
                session_meta["cwd"] = payload.get("cwd")
                session_meta["project"] = payload.get("cwd")
                session_meta["created_at"] = timestamp
                session_meta["updated_at"] = timestamp

                # Extract model provider — format as "Codex (provider)"
                model_provider = payload.get("model_provider")
                if model_provider:
                    session_meta["model"] = f"Codex ({model_provider})"

            # Parse response items (messages)
            elif entry_type == "response_item":
                message_type = payload.get("type")
                role = payload.get("role")

                if message_type == "message" and role in ("user", "assistant"):
                    content_list = payload.get("content", [])
                    content_json = json.dumps(payload)

                    # Extract text for display
                    text = ""
                    for item in content_list:
                        if isinstance(item, dict):
                            item_type = item.get("type")
                            if item_type in ("input_text", "text", "output_text"):
                                text += item.get("text", "")

                    # Capture first user message
                    if role == "user" and not first_user_message and text.strip():
                        cleaned = strip_xml_tags(text)
                        if cleaned and not is_system_message(text):
                            first_user_message = cleaned[:200]

                    messages.append({
                        "type": role,
                        "content": content_json,
                        "content_preview": create_content_preview(content_json),
                        "timestamp": timestamp or datetime.utcnow(),
                        "sequence": sequence,
                        "uuid": None,
                        "parent_uuid": None,
                    })
                    sequence += 1

                elif message_type == "function_call":
                    content_json = json.dumps(payload)
                    messages.append({
                        "type": "assistant",
                        "content": content_json,
                        "content_preview": create_content_preview(content_json),
                        "timestamp": timestamp or datetime.utcnow(),
                        "sequence": sequence,
                        "uuid": None,
                        "parent_uuid": None,
                    })
                    sequence += 1

                elif message_type == "function_call_output":
                    content_json = json.dumps(payload)
                    messages.append({
                        "type": "tool_result",
                        "content": content_json,
                        "content_preview": create_content_preview(content_json),
                        "timestamp": timestamp or datetime.utcnow(),
                        "sequence": sequence,
                        "uuid": None,
                        "parent_uuid": None,
                    })
                    sequence += 1

            # Update session timestamp
            if timestamp:
                session_meta["updated_at"] = timestamp

    except Exception as e:
        logger.error(f"[Codex Parser] Failed to parse {file_path}: {e}")
        raise

    # Set display text
    session_meta["display"] = first_user_message or "No user message"
    session_meta["message_count"] = len(messages)

    # Fallback session ID if not found
    if not session_meta["id"]:
        session_meta["id"] = file_path.stem

    return {
        "session": session_meta,
        "messages": messages,
    }
