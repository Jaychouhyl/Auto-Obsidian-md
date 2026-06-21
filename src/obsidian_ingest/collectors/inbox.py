from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from obsidian_ingest.config import AppConfig
from obsidian_ingest.queue_store import QueueStore

SUPPORTED_INBOX_EXTENSIONS = {
    ".txt",
    ".md",
    ".srt",
    ".vtt",
    ".pdf",
    ".mp3",
    ".wav",
    ".m4a",
    ".mp4",
    ".mkv",
    ".webm",
    ".mov",
    ".flac",
    ".ogg",
}


@dataclass(frozen=True)
class InboxCollectionResult:
    inbox_dir: Path
    queued: int
    files: list[str]


def scan_inbox_files(inbox_dir: Path) -> list[Path]:
    if not inbox_dir.exists():
        return []
    return sorted(
        (
            item
            for item in inbox_dir.rglob("*")
            if item.is_file() and item.suffix.lower() in SUPPORTED_INBOX_EXTENSIONS
        ),
        key=lambda path: str(path).lower(),
    )


def collect_inbox(config: AppConfig, inbox_dir: Path) -> InboxCollectionResult:
    files = scan_inbox_files(inbox_dir)
    store = QueueStore(config.paths.queue_db)
    queued_files: list[str] = []
    for path in files:
        store.enqueue(
            str(path),
            title=path.stem,
            metadata={"collector": "inbox"},
        )
        queued_files.append(str(path))
    return InboxCollectionResult(inbox_dir=inbox_dir, queued=len(queued_files), files=queued_files)
