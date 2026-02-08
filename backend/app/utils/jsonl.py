"""JSONL file utilities."""
import json
import logging
import re
from pathlib import Path
from typing import AsyncIterator, Any

import aiofiles

logger = logging.getLogger(__name__)


async def read_jsonl(file_path: Path) -> AsyncIterator[dict[str, Any]]:
    """
    Async generator to read JSONL file line by line.

    Args:
        file_path: Path to JSONL file

    Yields:
        Parsed JSON objects
    """
    try:
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            line_num = 0
            async for line in f:
                line_num += 1
                line = line.strip()
                if not line:
                    continue

                try:
                    yield json.loads(line)
                except json.JSONDecodeError as e:
                    logger.warning(f"[JSONL] Failed to parse line {line_num} in {file_path}: {e}")
                    continue
    except Exception as e:
        logger.error(f"[JSONL] Failed to read {file_path}: {e}")
        raise


_XML_TAG_RE = re.compile(r'<[^>]+>')
_SYSTEM_PREFIXES = (
    '<local-command-',
    '<command-name>',
    '<environment_context>',
    '<cwd>',
    '<system-reminder>',
    '# AGENTS.md instructions',
)


def strip_xml_tags(text: str) -> str:
    """Strip XML/HTML-style tags from text."""
    return _XML_TAG_RE.sub('', text).strip()


def is_system_message(text: str) -> bool:
    """Check if text looks like a system/environment message that should be skipped."""
    stripped = text.strip()
    return any(stripped.startswith(prefix) for prefix in _SYSTEM_PREFIXES)


def create_content_preview(content: str | dict, max_length: int = 200) -> str:
    """
    Create a preview of content (first N characters).

    Args:
        content: Content string or dict
        max_length: Maximum preview length

    Returns:
        Preview string
    """
    if isinstance(content, dict):
        content = json.dumps(content)

    if len(content) <= max_length:
        return content

    return content[:max_length] + "..."


def extract_text_from_content(content: dict | str) -> str:
    """
    Extract plain text from content for preview/search.

    Args:
        content: Content dict or string

    Returns:
        Extracted text string
    """
    if isinstance(content, str):
        return content

    if not isinstance(content, dict):
        return str(content)

    # Handle Claude message format
    if "content" in content:
        content_list = content["content"]
        if isinstance(content_list, list):
            text_parts = []
            for item in content_list:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
        elif isinstance(content_list, str):
            return content_list

    # Fallback: convert to JSON string
    return json.dumps(content)
