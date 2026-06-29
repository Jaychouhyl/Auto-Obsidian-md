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
    incomplete: bool = False
    active_template: str = "study_note"
    include_transcript: bool = True
    include_source_notes: bool = True
    attribution_name: str = "小黄狗"
    custom_structure: str = ""


def render_markdown_note(item: QueueItem, payload: NotePayload) -> str:
    title = item.title or _title_from_url(item.url)
    lines = [
        "---",
        f"source: {item.platform}",
        f"content_type: {item.content_type}",
        f"url: {item.url}",
        f"created: {item.created_at}",
        f"status: {'incomplete' if payload.incomplete else 'inbox'}",
        "tags:",
        *[f"  - {tag}" for tag in _note_tags(payload.tags, payload.incomplete)],
        f"folder: {_yaml_string(payload.routed_folder)}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    custom_body = _render_custom_structure(item, payload, title)
    if custom_body:
        lines.extend(custom_body)
    else:
        lines.extend(_default_body(payload))
    lines.extend(
        [
            "",
            "---",
            "",
            "> 自动化写的",
            f"> 署名：{payload.attribution_name.strip() or '小黄狗'}",
            "",
        ]
    )
    return "\n".join(lines)


def _default_body(payload: NotePayload) -> list[str]:
    labels = _section_labels(payload.active_template)
    lines = [
        labels["summary"],
        payload.summary.strip() or "待补充摘要。",
        "",
        labels["points"],
    ]
    lines.extend(_bullet_lines(payload.key_points, fallback="待补充知识点。"))
    lines.extend(["", labels["actions"]])
    lines.extend(_bullet_lines(payload.action_items, fallback="待补充行动项。"))

    if payload.include_source_notes and payload.source_notes:
        lines.extend(["", "## 处理备注"])
        lines.extend(_bullet_lines(payload.source_notes))

    if payload.include_transcript:
        lines.extend(["", "## 原始转写", ""])
        lines.append("```text")
        lines.append(payload.transcript.strip() or "暂无转写。")
        lines.append("```")
    return lines


def _render_custom_structure(item: QueueItem, payload: NotePayload, title: str) -> list[str]:
    template = payload.custom_structure.strip()
    if not template:
        return []
    replacements = {
        "title": title,
        "url": item.url,
        "summary": payload.summary.strip() or "待补充摘要。",
        "key_points": "\n".join(_bullet_lines(payload.key_points, fallback="待补充知识点。")),
        "action_items": "\n".join(_bullet_lines(payload.action_items, fallback="待补充行动项。")),
        "source_notes": "\n".join(_bullet_lines(payload.source_notes)) if payload.include_source_notes else "",
        "transcript": payload.transcript.strip() if payload.include_transcript else "",
    }
    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    lines = [line.rstrip() for line in rendered.splitlines()]
    while lines and not lines[-1].strip():
        lines.pop()
    return lines or []


def _bullet_lines(values: list[str], fallback: str | None = None) -> list[str]:
    cleaned = [value.strip() for value in values if value.strip()]
    if not cleaned and fallback:
        cleaned = [fallback]
    return [f"- {value}" for value in cleaned]


def _section_labels(template: str) -> dict[str, str]:
    templates = {
        "review_card": {
            "summary": "## 记忆线索",
            "points": "## 需要掌握",
            "actions": "## 复习任务",
        },
        "research_note": {
            "summary": "## 研究问题",
            "points": "## 方法与证据",
            "actions": "## 后续验证",
        },
        "action_note": {
            "summary": "## 目标",
            "points": "## 判断依据",
            "actions": "## 下一步行动",
        },
    }
    return templates.get(
        template.strip().lower(),
        {
            "summary": "## 一句话总结",
            "points": "## 核心知识点",
            "actions": "## 可执行清单",
        },
    )


def _title_from_url(url: str) -> str:
    return url.rstrip("/").split("/")[-1] or "Untitled"


def _yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _note_tags(tags: list[str], incomplete: bool = False) -> list[str]:
    seed = ["auto-ingest"]
    if incomplete:
        seed.append("待补来源")
    result: list[str] = []
    for value in [*seed, *tags]:
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
