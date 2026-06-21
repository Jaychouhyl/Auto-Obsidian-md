from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from obsidian_ingest.config import AppConfig
from obsidian_ingest.queue_store import QueueStore


@dataclass(frozen=True)
class WebpageClip:
    title: str
    text: str
    source_url: str


@dataclass(frozen=True)
class WebpageClipResult:
    url: str
    queued: int
    title: str
    cache_path: Path


class _ReadableHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.body_parts: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        if lowered == "title":
            self._in_title = True
        if lowered in {"p", "br", "div", "section", "article", "main", "li", "h1", "h2", "h3"}:
            self.body_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        if lowered in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if lowered == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title_parts.append(text)
        else:
            self.body_parts.append(text)


def extract_webpage_text(html_text: str, source_url: str) -> WebpageClip:
    parser = _ReadableHtmlParser()
    parser.feed(html_text)
    title = _clean_text(" ".join(parser.title_parts)) or source_url
    text = _clean_text("\n".join(parser.body_parts))
    return WebpageClip(title=title, text=text, source_url=source_url)


def collect_webpage(config: AppConfig, url: str) -> WebpageClipResult:
    html_text = read_webpage_source(url)
    clip = extract_webpage_text(html_text, source_url=url)
    cache_dir = config.paths.cache_dir / "webpages"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / (_safe_filename(clip.title) + ".txt")
    cache_path.write_text(
        f"# {clip.title}\n\nSource: {clip.source_url}\n\n{clip.text}\n",
        encoding="utf-8",
    )
    store = QueueStore(config.paths.queue_db)
    item = store.enqueue(
        str(cache_path),
        title=clip.title,
        metadata={"collector": "webpage", "source_url": url},
    )
    return WebpageClipResult(url=url, queued=1 if item else 0, title=clip.title, cache_path=cache_path)


def read_webpage_source(source: str) -> str:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        request = urllib.request.Request(source, headers={"User-Agent": "obsidian-ingest-pipeline/phase2"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="ignore")
    return Path(source).read_text(encoding="utf-8", errors="ignore")


def _clean_text(value: str) -> str:
    text = unescape(value)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip(" ._")
    return cleaned[:80] or "webpage"
