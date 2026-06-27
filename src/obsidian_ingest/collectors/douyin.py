from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from obsidian_ingest.accounts.models import Platform
from obsidian_ingest.accounts.runtime import CookieLoader, current_account_cookies
from obsidian_ingest.config import AppConfig
from obsidian_ingest.queue_store import QueueStore

DOUYIN_FAVORITES_URL = "https://www.douyin.com/user/self?showTab=favorite_collection"
DOUYIN_CONTENT_EXTENSIONS = (".txt", ".md", ".mp4")
DOUYIN_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


@dataclass(frozen=True)
class DouyinCollectionResult:
    run_id: str
    download_dir: Path
    queued: int
    files: list[str]
    notes: list[str]
    requested: int
    returned: int
    attempts: int


def build_douyin_favorites_url(run_id: str) -> str:
    return f"{DOUYIN_FAVORITES_URL}&obsidian_ingest_run={run_id}"


def copy_config_with_collect_count(source: Path, target: Path, count: int) -> None:
    copy_config_with_account(source, target, count=count)


def copy_config_with_account(
    source: Path,
    target: Path,
    count: int | None = None,
    cookies: list[dict[str, object]] | None = None,
) -> None:
    if count is not None and count < 1:
        raise ValueError("count must be >= 1")

    text = Path(source).read_text(encoding="utf-8")
    if count is not None:
        text = _replace_collect_count(text, count)
    if cookies is not None:
        cookie_map = {
            str(cookie.get("name", "")).strip(): str(cookie.get("value", ""))
            for cookie in cookies
            if str(cookie.get("name", "")).strip()
        }
        if not cookie_map:
            raise ValueError("Douyin account has no usable cookies")
        text = _replace_yaml_mapping(text, "cookies", cookie_map)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def _replace_collect_count(text: str, count: int) -> str:
    if count < 1:
        raise ValueError("count must be >= 1")
    if re.search(r"(?m)^(\s*)collect:\s*\d+\s*$", text):
        text = re.sub(
            r"(?m)^(\s*)collect:\s*\d+\s*$",
            lambda match: f"{match.group(1)}collect: {count}",
            text,
            count=1,
        )
    else:
        text = text.rstrip() + f"\nnumber:\n  collect: {count}\n"
    return text


def _replace_yaml_mapping(text: str, key: str, values: dict[str, str]) -> str:
    lines = text.splitlines()
    start = next((index for index, line in enumerate(lines) if re.match(rf"^{re.escape(key)}\s*:\s*$", line)), None)
    replacement = [f"{key}:", *[f"  {name}: {json.dumps(value, ensure_ascii=False)}" for name, value in values.items()]]
    if start is None:
        return text.rstrip() + "\n" + "\n".join(replacement) + "\n"
    end = start + 1
    while end < len(lines) and (not lines[end].strip() or lines[end][0].isspace() or lines[end].lstrip().startswith("#")):
        end += 1
    return "\n".join([*lines[:start], *replacement, *lines[end:]]) + "\n"


def discover_douyin_exports(download_dir: Path) -> list[Path]:
    """Return one processable source per downloaded Douyin item."""
    if not download_dir.exists():
        return []
    _ensure_gallery_markdown_exports(download_dir)
    manifest_order = _manifest_order(download_dir)

    by_stem: dict[Path, Path] = {}
    for path in sorted(download_dir.rglob("*"), key=lambda item: str(item).lower()):
        suffix = path.suffix.lower()
        if suffix not in DOUYIN_CONTENT_EXTENSIONS:
            continue
        key = path.with_suffix("")
        chosen = by_stem.get(key)
        if chosen is None or _export_priority(suffix) < _export_priority(chosen.suffix.lower()):
            by_stem[key] = path
    return sorted(
        by_stem.values(),
        key=lambda item: (
            _export_manifest_index(item, manifest_order),
            str(item).lower(),
        ),
    )


def _export_priority(suffix: str) -> int:
    return {".txt": 0, ".md": 1, ".mp4": 2}.get(suffix.lower(), 9)


def _manifest_order(download_dir: Path) -> dict[Path, int]:
    manifest = download_dir / "download_manifest.jsonl"
    if not manifest.is_file():
        return {}

    order: dict[Path, int] = {}
    for index, line in enumerate(manifest.read_text(encoding="utf-8", errors="ignore").splitlines()):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        file_paths = payload.get("file_paths", [])
        if not isinstance(file_paths, list):
            continue
        for value in file_paths:
            path = (download_dir / str(value)).resolve()
            order.setdefault(path, index)
            order.setdefault(path.parent, index)
    return order


def _export_manifest_index(path: Path, order: dict[Path, int]) -> int:
    resolved = path.resolve()
    return order.get(resolved, order.get(resolved.parent, 999_999))


def _ensure_gallery_markdown_exports(download_dir: Path) -> None:
    for data_path in sorted(download_dir.rglob("*_data.json"), key=lambda item: str(item).lower()):
        parent = data_path.parent
        if _has_primary_text_or_video(parent):
            continue
        target = parent / f"{data_path.name.removesuffix('_data.json')}_gallery.md"
        if target.exists():
            continue
        target.write_text(_render_gallery_markdown(data_path), encoding="utf-8")


def _has_primary_text_or_video(folder: Path) -> bool:
    for path in folder.iterdir():
        if path.is_file() and path.suffix.lower() in {".txt", ".mp4"}:
            return True
    return False


def _render_gallery_markdown(data_path: Path) -> str:
    data = _read_json_object(data_path)
    desc = _as_text(data.get("desc")) or data_path.parent.name
    title = next((line.strip() for line in desc.splitlines() if line.strip()), data_path.parent.name)
    author = _as_text(data.get("author_name")) or "未知"
    date = _as_text(data.get("date")) or "未知"
    aweme_id = _as_text(data.get("aweme_id")) or "未知"
    media_type = _as_text(data.get("media_type")) or "gallery"
    tags = _as_text_list(data.get("tags"))
    images = _gallery_images(data_path.parent)

    lines = [
        f"# {title}",
        "",
        "来源：抖音图文收藏",
        "",
        "## 元信息",
        f"- 作者：{author}",
        f"- 日期：{date}",
        f"- 类型：{media_type}",
        f"- 作品 ID：{aweme_id}",
        f"- 标签：{'、'.join(tags) if tags else '无'}",
        f"- 图片数量：{len(images)}",
        "",
        "## 文案",
        desc.strip(),
    ]
    if images:
        lines.extend(["", "## 图片文件", *[f"- {path.name}" for path in images]])
    return "\n".join(lines).rstrip() + "\n"


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _as_text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _as_text_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _as_text(item))]


def _gallery_images(folder: Path) -> list[Path]:
    images: list[Path] = []
    for path in sorted(folder.iterdir(), key=lambda item: str(item).lower()):
        if not path.is_file() or path.suffix.lower() not in DOUYIN_IMAGE_EXTENSIONS:
            continue
        stem = path.stem.lower()
        if stem.endswith("_cover") or stem.endswith("_avatar"):
            continue
        images.append(path)
    return images


def _export_identity(path: Path) -> str:
    data_path = next(iter(sorted(path.parent.glob("*_data.json"), key=lambda item: str(item).lower())), None)
    if data_path is not None:
        data = _read_json_object(data_path)
        aweme_id = _as_text(data.get("aweme_id"))
        if aweme_id:
            return f"aweme:{aweme_id}"
    return f"file:{path.parent.name}/{path.stem}"


def collect_douyin_favorites(
    config: AppConfig,
    count: int,
    cookie_loader: CookieLoader | None = None,
) -> DouyinCollectionResult:
    if count < 1:
        raise ValueError("count must be >= 1")

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = config.paths.cache_dir / "douyin-runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    base_config = Path(config.tools.douyin_config)
    if not base_config.exists():
        raise FileNotFoundError(f"Douyin config not found: {base_config}")

    account, cookies = current_account_cookies(
        config,
        Platform.DOUYIN,
        required=True,
        cookie_loader=cookie_loader,
    )
    store = QueueStore(config.paths.queue_db)
    queued_files: list[str] = []
    seen_identities: set[str] = set()
    returned_count = 0
    max_attempts = min(3, max(1, (count + 4) // 5))
    attempts_used = 0

    for attempt in range(1, max_attempts + 1):
        attempts_used = attempt
        attempt_dir = run_dir if max_attempts == 1 else run_dir / f"attempt-{attempt}"
        attempt_dir.mkdir(parents=True, exist_ok=True)
        run_config = attempt_dir / ".douyin-config.yml"
        copy_config_with_account(base_config, run_config, count=count, cookies=cookies)

        command = [
            config.tools.douyin_downloader,
            "-u",
            build_douyin_favorites_url(f"{run_id}-{attempt}"),
            "-p",
            str(attempt_dir),
            "-c",
            str(run_config),
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        finally:
            run_config.unlink(missing_ok=True)
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip() or "douyin collector failed"
            raise RuntimeError(message)

        exports = discover_douyin_exports(attempt_dir)
        returned_count += len(exports)
        new_exports: list[Path] = []
        for path in exports:
            identity = _export_identity(path)
            if identity in seen_identities:
                continue
            seen_identities.add(identity)
            new_exports.append(path)
        if not new_exports and attempt > 1:
            break
        for path in new_exports:
            if len(queued_files) >= count:
                break
            identity = _export_identity(path)
            store.enqueue(
                str(path),
                title=path.stem,
                metadata={
                    "collector": "douyin_favorites",
                    "source_run_id": run_id,
                    "source_url": DOUYIN_FAVORITES_URL,
                    "source_identity": identity,
                    "attempt": attempt,
                },
            )
            queued_files.append(str(path))
        if len(queued_files) >= count:
            break

    return DouyinCollectionResult(
        run_id=run_id,
        download_dir=run_dir,
        queued=len(queued_files),
        files=queued_files,
        notes=[
            f"Douyin favorites collected with count={count}",
            f"Account: {account.display_name} ({account.platform_user_id})",
            f"Downloader attempts: {attempts_used}",
            f"Downloader returned exports before de-dupe: {returned_count}",
        ],
        requested=count,
        returned=returned_count,
        attempts=attempts_used,
    )
