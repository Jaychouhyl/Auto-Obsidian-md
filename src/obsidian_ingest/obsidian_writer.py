from __future__ import annotations

import csv
import html
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class WriteResult:
    relative_path: str
    extra_paths: list[str] | None = None


class LocalVaultWriter:
    def __init__(self, vault_path: Path, folder: str = "Inbox/Learning Inbox"):
        self.vault_path = Path(vault_path)
        self.folder = _normalize_folder(folder)

    def write_note(self, title: str, content: str, folder: str | None = None) -> WriteResult:
        target_folder = _normalize_folder(folder) if folder is not None else self.folder
        relative = _join_relative(target_folder, make_safe_filename(title) + ".md")
        target = self.vault_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target = _unique_path(target)
            relative = target.relative_to(self.vault_path).as_posix()
        target.write_text(content, encoding="utf-8")
        return WriteResult(relative)


class ObsidianRestWriter:
    def __init__(self, base_url: str, api_key: str, folder: str = "Inbox/Learning Inbox"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.folder = _normalize_folder(folder)

    def write_note(self, title: str, content: str, folder: str | None = None) -> WriteResult:
        target_folder = _normalize_folder(folder) if folder is not None else self.folder
        relative = _join_relative(target_folder, make_safe_filename(title) + ".md")
        encoded_path = urllib.parse.quote(relative, safe="/")
        request = urllib.request.Request(
            f"{self.base_url}/vault/{encoded_path}",
            data=content.encode("utf-8"),
            method="PUT",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "text/markdown",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
        return WriteResult(relative)


class HtmlDirectoryWriter:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)

    def write_note(self, title: str, content: str, folder: str | None = None) -> WriteResult:
        target_folder = _normalize_folder(folder or "")
        relative = _join_relative(target_folder, make_safe_filename(title) + ".html")
        target = self.output_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target = _unique_path(target)
            relative = target.relative_to(self.output_dir).as_posix()
        target.write_text(_render_html_document(title, content), encoding="utf-8")
        return WriteResult(relative)


class CsvIndexWriter:
    def __init__(self, csv_path: Path):
        self.csv_path = Path(csv_path)

    def write_note(self, title: str, content: str, folder: str | None = None) -> WriteResult:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        exists = self.csv_path.is_file()
        with self.csv_path.open("a", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["created_at", "title", "folder", "filename", "excerpt"],
            )
            if not exists:
                writer.writeheader()
            writer.writerow(
                {
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "title": title,
                    "folder": _normalize_folder(folder or ""),
                    "filename": make_safe_filename(title) + ".md",
                    "excerpt": _plain_excerpt(content),
                }
            )
        return WriteResult(str(self.csv_path))


class NotionDatabaseWriter:
    def __init__(
        self,
        token: str,
        database_id: str,
        title_property: str = "Name",
        api_base: str = "https://api.notion.com/v1",
    ):
        self.token = token.strip()
        self.database_id = database_id.strip()
        self.title_property = title_property.strip() or "Name"
        self.api_base = api_base.rstrip("/")

    def write_note(self, title: str, content: str, folder: str | None = None) -> WriteResult:
        if not self.token or not self.database_id:
            raise ValueError("Notion output requires notion_token and notion_database_id")
        properties: dict[str, object] = {
            self.title_property: {"title": [{"text": {"content": title[:2000]}}]},
        }
        if folder:
            properties["Folder"] = {"rich_text": [{"text": {"content": _normalize_folder(folder)[:2000]}}]}
        payload = {
            "parent": {"database_id": self.database_id},
            "properties": properties,
            "children": _notion_blocks(content),
        }
        request = urllib.request.Request(
            f"{self.api_base}/pages",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8") or "{}")
        page_id = str(data.get("id", "")).strip() or self.database_id
        return WriteResult(f"notion://{page_id}")


class MultiWriter:
    def __init__(self, primary, secondary: list[object]):
        self.primary = primary
        self.secondary = secondary

    def write_note(self, title: str, content: str, folder: str | None = None) -> WriteResult:
        primary_result = self.primary.write_note(title, content, folder=folder)
        extra_paths: list[str] = list(primary_result.extra_paths or [])
        for writer in self.secondary:
            result = writer.write_note(title, content, folder=folder)
            extra_paths.append(result.relative_path)
            extra_paths.extend(result.extra_paths or [])
        return WriteResult(primary_result.relative_path, extra_paths=extra_paths)


def make_safe_filename(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", title.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-")
    return cleaned or "Untitled"


def _normalize_folder(folder: str) -> str:
    return folder.strip().replace("\\", "/").strip("/")


def _join_relative(folder: str, filename: str) -> str:
    return f"{folder}/{filename}" if folder else filename


def _unique_path(path: Path) -> Path:
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2
    while True:
        candidate = parent / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def _render_html_document(title: str, markdown_text: str) -> str:
    body = _markdown_to_html(markdown_text)
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; color: #17202a; background: #f6f7f9; }}
    main {{ max-width: 860px; margin: 0 auto; padding: 48px 24px 72px; background: #fff; min-height: 100vh; }}
    h1, h2, h3 {{ color: #101418; line-height: 1.25; }}
    p, li {{ line-height: 1.75; }}
    pre {{ overflow-x: auto; padding: 14px; background: #111827; color: #f9fafb; border-radius: 8px; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Consolas, monospace; }}
    hr {{ border: 0; border-top: 1px solid #dde2e8; margin: 28px 0; }}
  </style>
</head>
<body><main>{body}</main></body>
</html>
"""


def _markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    in_list = False
    in_pre = False
    pre_lines: list[str] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{html.escape(' '.join(paragraph))}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.rstrip()
        if line.startswith("```"):
            if in_pre:
                output.append(f"<pre><code>{html.escape(chr(10).join(pre_lines))}</code></pre>")
                pre_lines.clear()
                in_pre = False
            else:
                flush_paragraph()
                close_list()
                in_pre = True
            continue
        if in_pre:
            pre_lines.append(line)
            continue
        if not line.strip():
            flush_paragraph()
            close_list()
            continue
        if line == "---":
            flush_paragraph()
            close_list()
            output.append("<hr>")
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            close_list()
            level = len(heading.group(1))
            output.append(f"<h{level}>{html.escape(heading.group(2))}</h{level}>")
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        if bullet:
            flush_paragraph()
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{html.escape(bullet.group(1))}</li>")
            continue
        paragraph.append(line.strip())
    flush_paragraph()
    close_list()
    if in_pre:
        output.append(f"<pre><code>{html.escape(chr(10).join(pre_lines))}</code></pre>")
    return "\n".join(output)


def _plain_excerpt(content: str, limit: int = 240) -> str:
    text = re.sub(r"```.*?```", " ", content, flags=re.S)
    text = re.sub(r"[#>*_`\\[\\]-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _notion_blocks(markdown_text: str) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line or line == "---" or line.startswith("```"):
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            level = min(len(heading.group(1)), 3)
            blocks.append(
                {
                    "object": "block",
                    "type": f"heading_{level}",
                    f"heading_{level}": {"rich_text": [{"type": "text", "text": {"content": heading.group(2)[:2000]}}]},
                }
            )
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", line)
        if bullet:
            blocks.append(
                {
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {"rich_text": [{"type": "text", "text": {"content": bullet.group(1)[:2000]}}]},
                }
            )
            continue
        blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": [{"type": "text", "text": {"content": line[:2000]}}]},
            }
        )
        if len(blocks) >= 80:
            break
    return blocks or [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "Imported note"}}]},
        }
    ]
