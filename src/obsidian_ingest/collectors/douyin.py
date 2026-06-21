from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from obsidian_ingest.config import AppConfig
from obsidian_ingest.queue_store import QueueStore

DOUYIN_FAVORITES_URL = "https://www.douyin.com/user/self?showTab=favorite_collection"


@dataclass(frozen=True)
class DouyinCollectionResult:
    run_id: str
    download_dir: Path
    queued: int
    files: list[str]
    notes: list[str]


def build_douyin_favorites_url(run_id: str) -> str:
    return f"{DOUYIN_FAVORITES_URL}&obsidian_ingest_run={run_id}"


def copy_config_with_collect_count(source: Path, target: Path, count: int) -> None:
    if count < 1:
        raise ValueError("count must be >= 1")

    text = Path(source).read_text(encoding="utf-8")
    if re.search(r"(?m)^(\s*)collect:\s*\d+\s*$", text):
        text = re.sub(
            r"(?m)^(\s*)collect:\s*\d+\s*$",
            lambda match: f"{match.group(1)}collect: {count}",
            text,
            count=1,
        )
    else:
        text = text.rstrip() + f"\nnumber:\n  collect: {count}\n"

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def discover_douyin_text_exports(download_dir: Path) -> list[Path]:
    if not download_dir.exists():
        return []
    return sorted(download_dir.rglob("*.txt"), key=lambda path: str(path).lower())


def collect_douyin_favorites(config: AppConfig, count: int) -> DouyinCollectionResult:
    if count < 1:
        raise ValueError("count must be >= 1")

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.paths.cache_dir / "douyin-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    base_config = Path(config.tools.douyin_config)
    if not base_config.exists():
        raise FileNotFoundError(f"Douyin config not found: {base_config}")

    run_config = run_dir / "douyin-config.yml"
    copy_config_with_collect_count(base_config, run_config, count)

    command = [
        config.tools.douyin_downloader,
        "-u",
        build_douyin_favorites_url(run_id),
        "-p",
        str(run_dir),
        "-c",
        str(run_config),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "douyin collector failed"
        raise RuntimeError(message)

    store = QueueStore(config.paths.queue_db)
    queued_files: list[str] = []
    for path in discover_douyin_text_exports(run_dir):
        store.enqueue(
            str(path),
            title=path.stem,
            metadata={
                "collector": "douyin_favorites",
                "source_run_id": run_id,
                "source_url": DOUYIN_FAVORITES_URL,
            },
        )
        queued_files.append(str(path))

    return DouyinCollectionResult(
        run_id=run_id,
        download_dir=run_dir,
        queued=len(queued_files),
        files=queued_files,
        notes=[f"Douyin favorites collected with count={count}"],
    )
