from __future__ import annotations

import html
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from obsidian_ingest.config import AppConfig
from obsidian_ingest.queue_store import QueueStore


@dataclass(frozen=True)
class FeedItem:
    title: str
    url: str
    source_url: str


@dataclass(frozen=True)
class RssCollectionResult:
    feeds_file: Path
    queued: int
    feeds: list[str]
    items: list[str]


def parse_feed_items(xml_text: str, source_url: str, limit: int = 20) -> list[FeedItem]:
    root = ET.fromstring(xml_text)
    items: list[FeedItem] = []

    for item in root.findall(".//item"):
        title = _text(item, "title") or "RSS item"
        link = _text(item, "link")
        if link:
            items.append(FeedItem(title=html.unescape(title.strip()), url=link.strip(), source_url=source_url))
        if len(items) >= limit:
            return items

    for entry in root.findall(".//{*}entry"):
        title = _text(entry, "{*}title") or "Atom entry"
        link = ""
        for link_node in entry.findall("{*}link"):
            href = link_node.attrib.get("href", "").strip()
            if href:
                link = href
                break
        if link:
            items.append(FeedItem(title=html.unescape(title.strip()), url=link, source_url=source_url))
        if len(items) >= limit:
            return items

    return items[:limit]


def collect_rss_feeds(config: AppConfig, feeds_file: Path, limit: int = 20) -> RssCollectionResult:
    feeds = _read_feeds_file(feeds_file)
    store = QueueStore(config.paths.queue_db)
    queued_items: list[str] = []
    for feed in feeds:
        xml_text = read_feed_source(feed)
        for item in parse_feed_items(xml_text, source_url=feed, limit=limit):
            store.enqueue(
                item.url,
                title=item.title,
                metadata={"collector": "rss", "feed_url": item.source_url},
            )
            queued_items.append(item.url)
    return RssCollectionResult(feeds_file=feeds_file, queued=len(queued_items), feeds=feeds, items=queued_items)


def read_feed_source(source: str) -> str:
    source = _clean_feed_line(source)
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https"}:
        request = urllib.request.Request(source, headers={"User-Agent": "obsidian-ingest-pipeline/phase2"})
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8", errors="ignore")
    return Path(source).read_text(encoding="utf-8", errors="ignore")


def _read_feeds_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    feeds: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        feed = _clean_feed_line(line)
        if feed and not feed.startswith("#"):
            feeds.append(feed)
    return feeds


def _clean_feed_line(value: str) -> str:
    return value.strip().lstrip("\ufeff").strip()


def _text(node: ET.Element, tag: str) -> str:
    found = node.find(tag)
    return found.text if found is not None and found.text else ""
