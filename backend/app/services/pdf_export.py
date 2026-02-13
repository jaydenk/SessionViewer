"""PDF export service — renders sessions as HTML then converts to PDF via WeasyPrint."""

import json
import logging
from datetime import datetime, timezone

import markdown
from jinja2 import Template
from weasyprint import HTML

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Content block parsing (mirrors frontend parseContentBlocks)
# ---------------------------------------------------------------------------

def parse_content_blocks(content_str: str) -> list[dict]:
    """Parse a message content JSON string into typed content blocks."""
    if not content_str:
        return []

    # Try parsing as JSON
    try:
        content = json.loads(content_str)
    except (json.JSONDecodeError, TypeError):
        text = str(content_str).strip()
        return [{"type": "text", "text": text}] if text else []

    if isinstance(content, str):
        return [{"type": "text", "text": content}] if content.strip() else []

    if not content:
        return []

    blocks: list[dict] = []

    # Get the content array
    items: list = []
    if isinstance(content, dict):
        inner = content.get("content")
        if isinstance(inner, list):
            items = inner
        elif isinstance(inner, str):
            text = inner.strip()
            if text:
                blocks.append({"type": "text", "text": text})
            return blocks

        # Top-level Codex function_call
        if content.get("type") == "function_call":
            args = content.get("arguments", "")
            if not isinstance(args, str):
                args = json.dumps(args, indent=2)
            blocks.append({
                "type": "function_call",
                "name": content.get("name") or content.get("call_id") or "function",
                "input": args,
            })
            return blocks

        # Top-level Codex function_call_output
        if content.get("type") == "function_call_output":
            blocks.append({
                "type": "function_call_output",
                "output": content.get("output") or json.dumps(content, indent=2),
            })
            return blocks
    elif isinstance(content, list):
        items = content

    if not items and not blocks:
        s = json.dumps(content, indent=2)
        if s not in ("{}", "[]"):
            blocks.append({"type": "unknown", "text": s})
        return blocks

    for item in items:
        if not isinstance(item, dict):
            continue

        item_type = item.get("type", "")

        if item_type in ("text", "input_text", "output_text"):
            text = (item.get("text") or "").strip()
            if text:
                blocks.append({"type": "text", "text": text})

        elif item_type == "thinking":
            text = (item.get("thinking") or "").strip()
            if text:
                blocks.append({"type": "thinking", "text": text})

        elif item_type == "reasoning":
            summaries = item.get("summary", [])
            if summaries:
                text = "\n".join(s.get("text", "") for s in summaries).strip()
                if text:
                    blocks.append({"type": "reasoning", "text": text})

        elif item_type == "tool_use":
            inp = item.get("input", "")
            if not isinstance(inp, str):
                inp = json.dumps(inp, indent=2)
            blocks.append({
                "type": "tool_use",
                "name": item.get("name") or "tool",
                "input": inp,
            })

        elif item_type == "tool_result":
            c = item.get("content", "")
            if isinstance(c, str):
                output = c
            elif isinstance(c, list):
                output = "\n".join(
                    x.get("text", json.dumps(x)) if isinstance(x, dict) else str(x)
                    for x in c
                )
            else:
                output = json.dumps(c, indent=2)
            blocks.append({"type": "tool_result", "output": output})

        else:
            text = (item.get("text") or "").strip()
            if text:
                blocks.append({"type": "text", "text": text})

    return blocks


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

_md = markdown.Markdown(extensions=["fenced_code", "tables", "nl2br"])


def render_md(text: str) -> str:
    """Render markdown text to HTML."""
    _md.reset()
    return _md.convert(text)


# ---------------------------------------------------------------------------
# Date formatting
# ---------------------------------------------------------------------------

def format_date(dt_str: str | None) -> str:
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return dt_str or ""


# ---------------------------------------------------------------------------
# Jinja2 HTML template
# ---------------------------------------------------------------------------

HTML_TEMPLATE = Template(r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @page {
    size: A4;
    margin: 1.5cm 2cm;
  }
  body {
    font-family: "Liberation Sans", "Helvetica Neue", Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #1a1a1a;
  }
  .session-break {
    page-break-before: always;
  }

  /* Session header */
  .session-header {
    border-bottom: 2px solid #6b21a8;
    padding-bottom: 12px;
    margin-bottom: 24px;
  }
  .session-header h1 {
    font-size: 18pt;
    margin: 0 0 8px;
    color: #1e1e1e;
  }
  .session-meta {
    font-size: 9pt;
    color: #555;
    line-height: 1.8;
  }
  .session-meta strong {
    color: #333;
  }
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 9pt;
    font-weight: 600;
    color: white;
    margin-bottom: 8px;
  }
  .badge-claude { background-color: #7c3aed; }
  .badge-codex  { background-color: #2563eb; }

  /* Messages */
  .message-group {
    margin-bottom: 16px;
    padding: 12px 16px;
    border-radius: 8px;
    page-break-inside: avoid;
  }
  .message-user {
    background-color: #f0f4ff;
    border-left: 4px solid #3b82f6;
  }
  .message-assistant {
    background-color: #fafafa;
    border-left: 4px solid #7c3aed;
  }
  .message-role {
    font-weight: 700;
    font-size: 10pt;
    margin-bottom: 6px;
    color: #333;
  }
  .message-time {
    font-size: 8pt;
    color: #888;
    float: right;
  }

  /* Content blocks */
  .block-thinking, .block-reasoning {
    background-color: #fef3c7;
    border: 1px solid #fbbf24;
    border-radius: 6px;
    padding: 8px 12px;
    margin: 8px 0;
    font-size: 9.5pt;
  }
  .block-reasoning {
    background-color: #f3e8ff;
    border-color: #c084fc;
  }
  .block-label {
    font-weight: 700;
    font-size: 9pt;
    margin-bottom: 4px;
    color: #666;
  }
  .block-tool-use {
    background-color: #ecfdf5;
    border: 1px solid #6ee7b7;
    border-radius: 6px;
    padding: 8px 12px;
    margin: 8px 0;
  }
  .block-tool-result {
    background-color: #f3f4f6;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    padding: 8px 12px;
    margin: 8px 0;
  }
  .block-tool-name {
    font-weight: 700;
    font-size: 9pt;
    color: #065f46;
    margin-bottom: 4px;
  }

  pre {
    background-color: #f1f1f1;
    padding: 8px;
    border-radius: 4px;
    font-size: 8.5pt;
    white-space: pre-wrap;
    word-break: break-all;
    overflow: hidden;
  }
  code {
    background-color: #e5e7eb;
    padding: 1px 4px;
    border-radius: 3px;
    font-size: 9.5pt;
  }
  pre code {
    background: none;
    padding: 0;
  }

  /* Markdown prose */
  .prose h1 { font-size: 16pt; margin: 12px 0 6px; }
  .prose h2 { font-size: 14pt; margin: 10px 0 4px; }
  .prose h3 { font-size: 12pt; margin: 8px 0 4px; }
  .prose p  { margin: 4px 0; }
  .prose ul, .prose ol { margin: 4px 0; padding-left: 24px; }
  .prose li { margin: 2px 0; }
  .prose table { border-collapse: collapse; margin: 8px 0; width: 100%; }
  .prose th, .prose td { border: 1px solid #d1d5db; padding: 4px 8px; font-size: 9.5pt; }
  .prose th { background: #f3f4f6; }
  .prose blockquote { border-left: 3px solid #d1d5db; margin: 8px 0; padding-left: 12px; color: #555; }

  .truncated {
    font-style: italic;
    color: #888;
    font-size: 9pt;
  }
</style>
</head>
<body>
{% for sess in sessions %}
{% if not loop.first %}<div class="session-break"></div>{% endif %}

<div class="session-header">
  <span class="badge {{ 'badge-claude' if sess.source == 'claude' else 'badge-codex' }}">
    {{ sess.source }}
  </span>
  <h1>{{ sess.display or 'Untitled Session' }}</h1>
  <div class="session-meta">
    {% if sess.project %}<div><strong>Project:</strong> {{ sess.project }}</div>{% endif %}
    {% if sess.cwd %}<div><strong>Working Directory:</strong> {{ sess.cwd }}</div>{% endif %}
    {% if sess.model %}<div><strong>Model:</strong> {{ sess.model }}</div>{% endif %}
    <div><strong>Created:</strong> {{ sess.created_at_fmt }}</div>
    <div><strong>Messages:</strong> {{ sess.message_count }}</div>
  </div>
</div>

{% for group in sess.message_groups %}
<div class="message-group {{ 'message-user' if group.type == 'user' else 'message-assistant' }}">
  <div class="message-role">
    <span class="message-time">{{ group.timestamp_fmt }}</span>
    {{ 'User' if group.type == 'user' else 'Assistant' }}
  </div>
  {% for block in group.blocks %}
    {% if block.type == 'text' %}
      <div class="prose">{{ block.html }}</div>
    {% elif block.type == 'thinking' %}
      <div class="block-thinking">
        <div class="block-label">Thinking</div>
        <pre>{{ block.text[:3000] }}{% if block.text|length > 3000 %}<span class="truncated">... (truncated)</span>{% endif %}</pre>
      </div>
    {% elif block.type == 'reasoning' %}
      <div class="block-reasoning">
        <div class="block-label">Reasoning</div>
        <pre>{{ block.text[:3000] }}{% if block.text|length > 3000 %}<span class="truncated">... (truncated)</span>{% endif %}</pre>
      </div>
    {% elif block.type in ('tool_use', 'function_call') %}
      <div class="block-tool-use">
        <div class="block-tool-name">Tool: {{ block.name }}</div>
        <pre>{{ block.input[:2000] }}{% if block.input|length > 2000 %}<span class="truncated">... (truncated)</span>{% endif %}</pre>
      </div>
    {% elif block.type in ('tool_result', 'function_call_output') %}
      <div class="block-tool-result">
        <div class="block-label">Tool Result</div>
        <pre>{{ block.output[:2000] }}{% if block.output|length > 2000 %}<span class="truncated">... (truncated)</span>{% endif %}</pre>
      </div>
    {% else %}
      <pre>{{ block.text or '' }}</pre>
    {% endif %}
  {% endfor %}
</div>
{% endfor %}
{% endfor %}
</body>
</html>
""")


# ---------------------------------------------------------------------------
# PDF generation
# ---------------------------------------------------------------------------

def _group_messages(messages: list[dict]) -> list[dict]:
    """Group consecutive messages of the same type, mirroring frontend groupMessages."""
    groups: list[dict] = []
    current_type: str | None = None
    current_msgs: list[dict] = []

    for msg in messages:
        msg_type = msg.get("type", "")
        if msg_type != current_type:
            if current_msgs:
                groups.append({
                    "type": current_type,
                    "messages": current_msgs,
                    "timestamp": current_msgs[0].get("timestamp", ""),
                })
            current_msgs = [msg]
            current_type = msg_type
        else:
            current_msgs.append(msg)

    if current_msgs:
        groups.append({
            "type": current_type,
            "messages": current_msgs,
            "timestamp": current_msgs[0].get("timestamp", ""),
        })

    return groups


def generate_pdf(sessions_data: list[dict]) -> bytes:
    """Generate a PDF from a list of session dicts.

    Each dict should have keys: source, display, project, cwd, model,
    created_at, message_count, messages (list of message dicts with
    type, content, timestamp).
    """
    template_sessions = []

    for sess in sessions_data:
        messages = sess.get("messages", [])

        # Parse content blocks for each message, filter empty
        parsed_messages = []
        for msg in messages:
            blocks = parse_content_blocks(msg.get("content", ""))
            if blocks:
                parsed_messages.append({**msg, "_blocks": blocks})

        # Group messages
        groups = _group_messages(parsed_messages)

        # Build template-ready groups
        template_groups = []
        for group in groups:
            all_blocks = []
            for msg in group["messages"]:
                for block in msg.get("_blocks", []):
                    # Render markdown for text blocks
                    if block["type"] == "text":
                        block = {**block, "html": render_md(block["text"])}
                    all_blocks.append(block)

            template_groups.append({
                "type": group["type"],
                "timestamp_fmt": format_date(group["timestamp"]),
                "blocks": all_blocks,
            })

        template_sessions.append({
            "source": sess.get("source", ""),
            "display": sess.get("display", ""),
            "project": sess.get("project", ""),
            "cwd": sess.get("cwd", ""),
            "model": sess.get("model", ""),
            "created_at_fmt": format_date(sess.get("created_at", "")),
            "message_count": sess.get("message_count", 0),
            "message_groups": template_groups,
        })

    html_str = HTML_TEMPLATE.render(sessions=template_sessions)
    pdf_bytes = HTML(string=html_str).write_pdf()
    return pdf_bytes
