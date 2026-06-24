from __future__ import annotations

import json
import subprocess
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from obsidian_ingest.config import AppConfig
from obsidian_ingest.accounts.models import Platform
from obsidian_ingest.accounts.providers.base import AccountIdentityError
from obsidian_ingest.accounts.runtime import CookieLoader, current_account_cookie_file
from obsidian_ingest.accounts.service import AccountServiceError
from obsidian_ingest.queue_store import QueueStore


@dataclass(frozen=True)
class PlatformListItem:
    title: str
    url: str


@dataclass(frozen=True)
class PlatformListResult:
    source_url: str
    queued: int
    items: list[str]
    used_fallback: bool
    error: str | None = None


def parse_yt_dlp_flat_json(json_text: str, source_url: str) -> list[PlatformListItem]:
    data = json.loads(json_text.lstrip("\ufeff"))
    raw_entries = data if isinstance(data, list) else data.get("entries", [])
    if not isinstance(raw_entries, list):
        return []

    items: list[PlatformListItem] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or entry.get("id") or entry.get("url") or "Untitled").strip()
        url = _entry_url(entry, source_url)
        if url:
            items.append(PlatformListItem(title=title, url=url))
    return items


def collect_platform_list(
    config: AppConfig,
    source_url: str,
    limit: int = 50,
    platform: str = "auto",
    metadata_file: Path | None = None,
    cookie_loader: CookieLoader | None = None,
) -> PlatformListResult:
    store = QueueStore(config.paths.queue_db)
    error: str | None = None
    used_fallback = False

    try:
        account_platform = _account_platform(platform, source_url)
        cookie_context = (
            current_account_cookie_file(
                config,
                account_platform,
                required=False,
                cookie_loader=cookie_loader,
            )
            if metadata_file is None and account_platform is not None
            else nullcontext(None)
        )
        with cookie_context as cookie_path:
            json_text = _read_metadata(config, source_url, metadata_file, cookie_path)
        items = parse_yt_dlp_flat_json(json_text, source_url=source_url)[:limit]
    except (AccountServiceError, AccountIdentityError):
        raise
    except Exception as exc:
        items = []
        error = str(exc)

    if not items:
        used_fallback = True
        item = store.enqueue(
            source_url,
            title=f"{platform} 列表入口" if platform != "auto" else "平台列表入口",
            metadata={"collector": "platform_list", "platform_hint": platform, "fallback": True, "error": error},
        )
        return PlatformListResult(source_url=source_url, queued=1, items=[item.url], used_fallback=True, error=error)

    queued_items: list[str] = []
    for item in items:
        queued = store.enqueue(
            item.url,
            title=item.title,
            metadata={"collector": "platform_list", "source_list": source_url, "platform_hint": platform},
        )
        queued_items.append(queued.url)
    return PlatformListResult(source_url=source_url, queued=len(queued_items), items=queued_items, used_fallback=used_fallback, error=error)


def _read_metadata(
    config: AppConfig,
    source_url: str,
    metadata_file: Path | None,
    cookie_path: Path | None = None,
) -> str:
    if metadata_file is not None:
        return Path(metadata_file).read_text(encoding="utf-8")
    command = [config.tools.yt_dlp, "--flat-playlist", "--dump-single-json"]
    if cookie_path is not None:
        command.extend(["--cookies", str(cookie_path)])
    command.append(source_url)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=120,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError((completed.stderr or completed.stdout or "yt-dlp failed").strip())
    return completed.stdout


def _account_platform(platform: str, source_url: str) -> Platform | None:
    if platform != "auto":
        try:
            return Platform(platform)
        except ValueError:
            return None
    host = urlparse(source_url).netloc.lower()
    if "bilibili.com" in host:
        return Platform.BILIBILI
    if "youtube.com" in host or "youtu.be" in host:
        return Platform.YOUTUBE
    if "tiktok.com" in host:
        return Platform.TIKTOK
    return None


def _entry_url(entry: dict[str, object], source_url: str) -> str:
    for key in ("webpage_url", "original_url"):
        value = str(entry.get(key) or "").strip()
        if value.startswith(("http://", "https://")):
            return value

    value = str(entry.get("url") or "").strip()
    if value.startswith(("http://", "https://")):
        return value

    item_id = str(entry.get("id") or value).strip()
    ie_key = str(entry.get("ie_key") or "").lower()
    host = urlparse(source_url).netloc.lower()
    if item_id and (item_id.startswith("BV") or "bili" in ie_key or "bilibili" in host):
        return f"https://www.bilibili.com/video/{item_id}"
    if item_id and ("youtube" in ie_key or "youtube" in host or "youtu.be" in host):
        return f"https://www.youtube.com/watch?v={item_id}"
    return ""
