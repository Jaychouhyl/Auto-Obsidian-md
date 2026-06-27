from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import AppConfig
from .queue_store import QueueItem


def queue_item_to_dict(item: QueueItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "url": item.url,
        "title": item.title,
        "platform": item.platform,
        "content_type": item.content_type,
        "status": item.status,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "metadata": item.metadata,
        "note_path": item.note_path,
        "error": item.error,
    }


def status_payload(config: AppConfig, queue_counts: dict[str, int]) -> dict[str, Any]:
    return {
        "paths": {
            "project_root": str(config.config_path.parent),
            "queue_db": str(config.paths.queue_db),
            "cache_dir": str(config.paths.cache_dir),
            "obsidian_vault": str(config.obsidian.vault_path),
            "obsidian_folder": config.obsidian.folder,
        },
        "queue": queue_counts,
        "routing": {
            "enabled": config.routing.enabled,
            "fallback_folder": config.routing.fallback_folder,
            "allowed_folders": config.routing.allowed_folders,
        },
        "obsidian": {
            "mode": config.obsidian.mode,
            "rest_base_url": config.obsidian.rest_base_url,
            "rest_api_key_configured": bool(config.obsidian.rest_api_key),
        },
        "tools": {
            "yt_dlp": config.tools.yt_dlp,
            "ffmpeg": config.tools.ffmpeg,
            "douyin_downloader": config.tools.douyin_downloader,
            "douyin_config": config.tools.douyin_config,
            "whisper": config.tools.whisper,
            "funasr": config.tools.funasr,
        },
        "llm": {
            "enabled": config.llm.enabled,
            "provider": config.llm.provider,
            "base_url": config.llm.base_url,
            "model": config.llm.model,
            "language": config.llm.language,
            "api_key_configured": bool(config.llm.api_key),
        },
        "outputs": {
            "formats": config.outputs.formats,
            "html_dir": str(config.outputs.html_dir),
            "csv_path": str(config.outputs.csv_path),
            "notion_configured": bool(config.outputs.notion_token and config.outputs.notion_database_id),
            "notion_database_id_configured": bool(config.outputs.notion_database_id),
            "notion_token_configured": bool(config.outputs.notion_token),
            "notion_title_property": config.outputs.notion_title_property,
            "notion_api_base": config.outputs.notion_api_base,
        },
    }


def file_count(path: Path, suffixes: set[str]) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file() and item.suffix.lower() in suffixes)
