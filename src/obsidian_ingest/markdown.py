from __future__ import annotations

import re
from dataclasses import dataclass, field

from .queue_store import QueueItem


@dataclass(frozen=True)
class NotePayload:
    summary: str
    key_points: list[str] = field(default_factory=list)
    action_items: list[str] = field(default_factory=list)
    transcript: str = ""
    source_notes: list[str] = field(default_factory=list)
    routed_folder: str = ""
    tags: list[str] = field(default_factory=list)


def render_markdown_note(item: QueueItem, payload: NotePayload) -> str:
    title = item.title or _title_from_url(item.url)
    lines = [
        "---",
        f"source: {item.platform}",
        f"content_type: {item.content_type}",
        f"url: {item.url}",
        f"created: {item.created_at}",
        "status: inbox",
        "tags:",
        *[f"  - {tag}" for tag in _note_tags(payload.tags)],
        f"folder: {_yaml_string(payload.routed_folder)}",
        "---",
        "",
        f"# {title}",
        "",
        "## 一句话总结",
        payload.summary.strip() or "待补充摘要。",
        "",
        "## 核心知识点",
    ]
    lines.extend(_bullet_lines(payload.key_points, fallback="待补充知识点。"))
    lines.extend(["", "## 可执行清单"])
    lines.extend(_bullet_lines(payload.action_items, fallback="待补充行动项。"))

    if payload.source_notes:
        lines.extend(["", "## 处理备注"])
        lines.extend(_bullet_lines(payload.source_notes))

    lines.extend(["", "## 原始转写", ""])
    lines.append("```text")
    lines.append(payload.transcript.strip() or "暂无转写。")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def _bullet_lines(values: list[str], fallback: str | None = None) -> list[str]:
    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned and fallback:
        cleaned = [fallback]
    return [f"- {value}" for value in cleaned]


def _title_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1] or "Untitled"


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _note_tags(tags: list[str]) -> list[str]:
    result: list[str] = []
    for value in ["auto-ingest", *tags]:
        tag = _clean_tag(value)
        if tag and tag not in result:
            result.append(tag)
    return result


def _clean_tag(value: str) -> str:
    text = str(value).strip().lstrip("#").strip()
    text = re.sub(r"\s+", "-", text)
    if not text or text.isdigit():
        return ""
    return text
