from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import AppConfig


@dataclass(frozen=True)
class KnowledgeMaintenanceResult:
    total_notes: int
    files: list[str]
    duplicates: int
    backlink_suggestions: int


@dataclass(frozen=True)
class VaultNote:
    path: Path
    relative_path: str
    title: str
    folder: str
    url: str
    modified: datetime
    text: str


def build_knowledge_maintenance(config: AppConfig, write: bool = False) -> KnowledgeMaintenanceResult:
    notes = scan_vault_notes(config.obsidian.vault_path)
    duplicates = find_duplicate_sources(notes)
    suggestions = suggest_backlinks(notes)
    reports = {
        "入库总览.md": render_index(notes),
        "每周入库报告.md": render_weekly_report(notes),
        "重复内容检查.md": render_duplicate_report(duplicates),
        "双链建议.md": render_backlink_report(suggestions),
    }
    written: list[str] = []
    if write:
        target = config.obsidian.vault_path / "Obsidian Ingest Pipeline"
        target.mkdir(parents=True, exist_ok=True)
        for filename, body in reports.items():
            path = target / filename
            path.write_text(body, encoding="utf-8")
            written.append(str(path))
    return KnowledgeMaintenanceResult(
        total_notes=len(notes),
        files=written,
        duplicates=sum(len(paths) for paths in duplicates.values()),
        backlink_suggestions=len(suggestions),
    )


def scan_vault_notes(vault_path: Path) -> list[VaultNote]:
    vault = Path(vault_path)
    if not vault.exists():
        return []
    notes: list[VaultNote] = []
    for path in sorted(vault.rglob("*.md")):
        if ".obsidian" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        relative = path.relative_to(vault).as_posix()
        notes.append(
            VaultNote(
                path=path,
                relative_path=relative,
                title=path.stem,
                folder=relative.split("/")[0] if "/" in relative else ".",
                url=_frontmatter_value(text, "url"),
                modified=datetime.fromtimestamp(path.stat().st_mtime, timezone.utc),
                text=text,
            )
        )
    return notes


def find_duplicate_sources(notes: list[VaultNote]) -> dict[str, list[str]]:
    by_url: dict[str, list[str]] = {}
    for note in notes:
        if note.url:
            by_url.setdefault(note.url, []).append(note.relative_path)
    return {url: paths for url, paths in by_url.items() if len(paths) > 1}


def suggest_backlinks(notes: list[VaultNote]) -> list[tuple[str, str]]:
    suggestions: list[tuple[str, str]] = []
    titles = [(note.title, note.relative_path) for note in notes if note.title]
    for note in notes:
        for title, target_path in titles:
            if target_path == note.relative_path:
                continue
            if title in note.text and f"[[{title}]]" not in note.text:
                suggestions.append((note.relative_path, title))
    return suggestions[:200]


def render_index(notes: list[VaultNote]) -> str:
    by_folder: dict[str, int] = {}
    for note in notes:
        by_folder[note.folder] = by_folder.get(note.folder, 0) + 1
    lines = [
        "# Obsidian Ingest 入库总览",
        "",
        f"- 笔记总数：{len(notes)}",
        f"- 更新时间：{_now_cn()}",
        "",
        "## 按目录统计",
        "",
        "| 目录 | 数量 |",
        "| --- | ---: |",
    ]
    for folder, count in sorted(by_folder.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"| {folder} | {count} |")
    lines.extend(["", "## 最近更新", ""])
    for note in sorted(notes, key=lambda item: item.modified, reverse=True)[:20]:
        lines.append(f"- [[{note.title}]] ｜ `{note.relative_path}`")
    lines.append("")
    return "\n".join(lines)


def render_weekly_report(notes: list[VaultNote]) -> str:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent = [note for note in notes if note.modified >= cutoff]
    lines = [
        "# Obsidian Ingest 每周入库报告",
        "",
        f"- 最近 7 天新增或更新：{len(recent)}",
        f"- 更新时间：{_now_cn()}",
        "",
        "## 最近 7 天资料",
        "",
    ]
    if recent:
        for note in sorted(recent, key=lambda item: item.modified, reverse=True)[:50]:
            lines.append(f"- [[{note.title}]] ｜ `{note.relative_path}`")
    else:
        lines.append("- 最近 7 天没有检测到新增或更新的 Markdown。")
    lines.append("")
    return "\n".join(lines)


def render_duplicate_report(duplicates: dict[str, list[str]]) -> str:
    lines = ["# Obsidian Ingest 重复内容检查", "", f"- 重复来源数量：{len(duplicates)}", ""]
    if duplicates:
        for url, paths in sorted(duplicates.items()):
            lines.append(f"## {url}")
            lines.extend(f"- `{path}`" for path in paths)
            lines.append("")
    else:
        lines.append("没有发现基于 `url` frontmatter 的重复来源。")
    lines.append("")
    return "\n".join(lines)


def render_backlink_report(suggestions: list[tuple[str, str]]) -> str:
    lines = ["# Obsidian Ingest 双链建议", "", f"- 建议数量：{len(suggestions)}", ""]
    if suggestions:
        lines.extend("| 笔记 | 建议链接 |")
        lines.extend("| --- | --- |")
        for source, title in suggestions:
            lines.append(f"| `{source}` | [[{title}]] |")
    else:
        lines.append("没有发现明显的未链接标题提及。")
    lines.append("")
    return "\n".join(lines)


def _frontmatter_value(text: str, key: str) -> str:
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    prefix = f"{key}:"
    for line in parts[1].splitlines():
        if line.strip().startswith(prefix):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def _now_cn() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")

