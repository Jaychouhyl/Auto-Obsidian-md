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


DOUYIN_CONTENT_EXTENSIONS = (".txt", ".mp4")


def discover_douyin_exports(download_dir: Path) -> list[Path]:
    """每条视频挑一个内容文件入队：同名的文本(.txt)优先于视频(.mp4)，忽略封面/音乐；同一文件夹内的多条(如 live_1/live_2)各自保留。"""
    if not download_dir.exists():
        return []
    by_stem: dict[Path, Path] = {}
    for path in sorted(download_dir.rglob("*"), key=lambda item: str(item).lower()):
        suffix = path.suffix.lower()
        if suffix not in DOUYIN_CONTENT_EXTENSIONS:
            continue
        key = path.with_suffix("")  # 同名不同扩展(.mp4/.txt)视作同一条视频
        chosen = by_stem.get(key)
        if chosen is None or (chosen.suffix.lower() == ".mp4" and suffix == ".txt"):
            by_stem[key] = path
    return sorted(by_stem.values(), key=lambda item: str(item).lower())


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
    completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "douyin collector failed"
        raise RuntimeError(message)

    store = QueueStore(config.paths.queue_db)
    queued_files: list[str] = []
    for path in discover_douyin_exports(run_dir):
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
