from __future__ import annotations

from dataclasses import dataclass

from .acquire import AcquisitionRequest, acquire_source
from .config import AppConfig
from .markdown import NotePayload, render_markdown_note
from .obsidian_writer import LocalVaultWriter, ObsidianRestWriter
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
        acquired = acquire_source(
            AcquisitionRequest(item.url, item.platform, item_cache, item.title),
            yt_dlp_cmd=config.tools.yt_dlp,
            douyin_cmd=config.tools.douyin_downloader,
            douyin_config=config.tools.douyin_config,
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
            transcription.text,
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
        )
        note = render_markdown_note(item, payload)
        writer = build_writer(config)
        result = writer.write_note(item.title or f"{item.platform}-{item.id}", note, folder=target_folder)
        store.mark_done(item.id, result.relative_path)
        return PipelineResult(item.id, "done", result.relative_path)
    except Exception as exc:
        store.mark_failed(item.id, str(exc))
        return PipelineResult(item.id, "failed", None, str(exc))


def build_writer(config: AppConfig):
    if config.obsidian.mode == "rest":
        return ObsidianRestWriter(config.obsidian.rest_base_url, config.obsidian.rest_api_key, config.obsidian.folder)
    return LocalVaultWriter(config.obsidian.vault_path, config.obsidian.folder)
