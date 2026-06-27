from __future__ import annotations

from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

from .accounts.models import Platform
from .accounts.runtime import current_account_cookie_file, current_account_cookies
from .collectors.douyin import copy_config_with_account
from .acquire import AcquisitionRequest, acquire_source
from .config import AppConfig
from .markdown import NotePayload, render_markdown_note
from .obsidian_writer import (
    CsvIndexWriter,
    HtmlDirectoryWriter,
    LocalVaultWriter,
    MultiWriter,
    NotionDatabaseWriter,
    ObsidianRestWriter,
)
from .queue_store import QueueItem, QueueStore
from .summarize import summarize_transcript
from .transcribe import transcribe_source


@dataclass(frozen=True)
class PipelineResult:
    item_id: int
    status: str
    note_path: str | None
    error: str | None = None


def run_pending(config: AppConfig, limit: int = 1) -> list[PipelineResult]:
    store = QueueStore(config.paths.queue_db)
    results: list[PipelineResult] = []
    for item in store.list_pending(limit=limit):
        results.append(process_item(config, store, item))
    return results


def process_item(config: AppConfig, store: QueueStore, item: QueueItem) -> PipelineResult:
    try:
        store.mark_processing(item.id)
        item_cache = config.paths.cache_dir / f"item-{item.id}"
        with ExitStack() as stack:
            cookie_path = None
            douyin_config = config.tools.douyin_config
            if item.platform == Platform.DOUYIN.value:
                _, cookies = current_account_cookies(config, Platform.DOUYIN, required=True)
                temporary_config = item_cache / ".douyin-config.yml"
                copy_config_with_account(
                    Path(config.tools.douyin_config),
                    temporary_config,
                    cookies=cookies,
                )
                stack.callback(temporary_config.unlink, missing_ok=True)
                douyin_config = str(temporary_config)
            elif item.platform in {
                Platform.YOUTUBE.value,
                Platform.BILIBILI.value,
                Platform.TIKTOK.value,
            }:
                cookie_path = stack.enter_context(
                    current_account_cookie_file(
                        config,
                        Platform(item.platform),
                        required=False,
                    )
                )
            acquired = acquire_source(
                AcquisitionRequest(item.url, item.platform, item_cache, item.title),
                yt_dlp_cmd=config.tools.yt_dlp,
                douyin_cmd=config.tools.douyin_downloader,
                douyin_config=douyin_config,
                cookies_file=cookie_path,
                dry_run_missing_tools=True,
            )
        transcription = transcribe_source(
            acquired.media_path,
            acquired.transcript_hint,
            engine="whisper",
            whisper_cmd=config.tools.whisper,
            funasr_cmd=config.tools.funasr,
            dry_run_missing_tools=True,
        )
        summary = summarize_transcript(
            build_summary_input(item, transcription),
            enabled=config.llm.enabled,
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            model=config.llm.model,
            language=config.llm.language,
            allowed_folders=config.routing.allowed_folders if config.routing.enabled else None,
            fallback_folder=config.routing.fallback_folder or config.obsidian.folder,
        )
        target_folder = summary.folder if config.routing.enabled and summary.folder else config.obsidian.folder
        payload = NotePayload(
            summary=summary.summary,
            key_points=summary.key_points,
            action_items=summary.action_items,
            transcript=transcription.text,
            source_notes=acquired.notes + transcription.notes + [f"自动分类: {target_folder}"] + summary.notes,
            routed_folder=target_folder,
            tags=summary.tags,
            incomplete=_note_incomplete(acquired, transcription),
        )
        note = render_markdown_note(item, payload)
        writer = build_writer(config)
        result = writer.write_note(item.title or f"{item.platform}-{item.id}", note, folder=target_folder)
        store.mark_done(item.id, result.relative_path)
        return PipelineResult(item.id, "done", result.relative_path)
    except Exception as exc:
        store.mark_failed(item.id, str(exc))
        return PipelineResult(item.id, "failed", None, str(exc))


def build_summary_input(item: QueueItem, transcription) -> str:
    parts: list[str] = []
    if item.title:
        parts.append(f"标题：{item.title}")
    text = str(transcription.text or "").strip()
    if text:
        parts.append(f"转写/正文：\n{text}")
    return "\n\n".join(parts) or str(item.url)


def _note_incomplete(acquired, transcription) -> bool:
    """笔记是否为占位/降级稿：缺下载或转写工具、下载失败等导致没有真实内容。"""
    if acquired.status in {"metadata_only", "failed"}:
        return True
    if acquired.media_path is not None and transcription.engine in {"hint", "none"}:
        return True
    if transcription.engine == "none" or not transcription.text.strip():
        return True
    return False


def build_writer(config: AppConfig):
    formats = set(config.outputs.formats)
    if config.obsidian.mode == "rest":
        primary = ObsidianRestWriter(config.obsidian.rest_base_url, config.obsidian.rest_api_key, config.obsidian.folder)
    else:
        primary = LocalVaultWriter(config.obsidian.vault_path, config.obsidian.folder)

    secondary = []
    if "html" in formats:
        secondary.append(HtmlDirectoryWriter(config.outputs.html_dir))
    if "csv" in formats:
        secondary.append(CsvIndexWriter(config.outputs.csv_path))
    if "notion" in formats:
        secondary.append(
            NotionDatabaseWriter(
                config.outputs.notion_token,
                config.outputs.notion_database_id,
                config.outputs.notion_title_property,
                config.outputs.notion_api_base,
            )
        )
    return MultiWriter(primary, secondary) if secondary else primary
