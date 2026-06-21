from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from obsidian_ingest.collectors.inbox import SUPPORTED_INBOX_EXTENSIONS
from obsidian_ingest.config import AppConfig
from obsidian_ingest.queue_store import QueueStore


@dataclass(frozen=True)
class DirectoryCollectionResult:
    directory: Path
    queued: int
    files: list[str]


def scan_directory_files(directory: Path) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        (
            item
            for item in directory.rglob("*")
            if item.is_file() and item.suffix.lower() in SUPPORTED_INBOX_EXTENSIONS
        ),
        key=lambda path: str(path).lower(),
    )


def collect_directory(config: AppConfig, directory: Path) -> DirectoryCollectionResult:
    files = scan_directory_files(directory)
    store = QueueStore(config.paths.queue_db)
    queued_files: list[str] = []
    for path in files:
        store.enqueue(
            str(path),
            title=path.stem,
            metadata={"collector": "directory", "source_directory": str(directory)},
        )
        queued_files.append(str(path))
    return DirectoryCollectionResult(directory=directory, queued=len(queued_files), files=queued_files)
