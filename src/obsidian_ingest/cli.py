from __future__ import annotations

import argparse
import json
from pathlib import Path

from .collectors.directory import collect_directory
from .collectors.douyin import collect_douyin_favorites
from .collectors.inbox import collect_inbox
from .collectors.platform_lists import collect_platform_list
from .collectors.rss import collect_rss_feeds
from .collectors.webpage import collect_webpage
from .config import DEFAULT_PROJECT_DIR, load_config, write_default_config
from .doctor import format_doctor, run_doctor
from .json_output import queue_item_to_dict, status_payload
from .knowledge import build_knowledge_maintenance
from .pipeline import run_pending
from .queue_store import QueueStore


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return _cmd_init(args)
    if args.command == "add":
        return _cmd_add(args)
    if args.command == "import-links":
        return _cmd_import_links(args)
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "doctor":
        return _cmd_doctor(args)
    if args.command == "status":
        return _cmd_status(args)
    if args.command == "queue":
        return _cmd_queue(args)
    if args.command == "collect-douyin":
        return _cmd_collect_douyin(args)
    if args.command == "scan-inbox":
        return _cmd_scan_inbox(args)
    if args.command == "scan-directory":
        return _cmd_scan_directory(args)
    if args.command == "collect-rss":
        return _cmd_collect_rss(args)
    if args.command == "clip-webpage":
        return _cmd_clip_webpage(args)
    if args.command == "collect-list":
        return _cmd_collect_list(args)
    if args.command == "retry":
        return _cmd_retry(args)
    if args.command == "retry-failed":
        return _cmd_retry_failed(args)
    if args.command == "skip":
        return _cmd_skip(args)
    if args.command == "knowledge-maintenance":
        return _cmd_knowledge_maintenance(args)
    if args.command == "write-launcher":
        return _cmd_write_launcher(args)
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="obsidian-ingest", description="Turn learning sources into Obsidian Markdown notes.")
    parser.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"), help="Path to config.toml")
    subparsers = parser.add_subparsers(dest="command")

    init = subparsers.add_parser("init", help="Create a config file")
    init.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    init.add_argument("--vault", default=str(DEFAULT_PROJECT_DIR / "sample-vault"))

    add = subparsers.add_parser("add", help="Add one source URL or file path")
    add.add_argument("url")
    add.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    add.add_argument("--title")

    import_links = subparsers.add_parser("import-links", help="Import source URLs from a plain text file")
    import_links.add_argument("file")
    import_links.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))

    run = subparsers.add_parser("run", help="Process pending queue items")
    run.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    run.add_argument("--once", action="store_true", help="Process once and exit")
    run.add_argument("--limit", type=int, default=1)

    doctor = subparsers.add_parser("doctor", help="Check config and optional tools")
    doctor.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    doctor.add_argument("--json", action="store_true")

    status = subparsers.add_parser("status", help="Print project status")
    status.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    status.add_argument("--json", action="store_true")

    queue = subparsers.add_parser("queue", help="List queue items")
    queue.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    queue.add_argument("--json", action="store_true")
    queue.add_argument("--limit", type=int, default=50)
    queue.add_argument("--status", default="all", choices=["all", "pending", "processing", "done", "failed", "skipped"])

    collect_douyin = subparsers.add_parser("collect-douyin", help="Collect Douyin favorites into queue")
    collect_douyin.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    collect_douyin.add_argument("--count", type=int, required=True)
    collect_douyin.add_argument("--json", action="store_true")

    scan_inbox = subparsers.add_parser("scan-inbox", help="Scan inbox folder and enqueue files")
    scan_inbox.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    scan_inbox.add_argument("--inbox", default=str(DEFAULT_PROJECT_DIR / "inbox"))
    scan_inbox.add_argument("--json", action="store_true")

    scan_directory = subparsers.add_parser("scan-directory", help="Scan any local directory and enqueue supported files")
    scan_directory.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    scan_directory.add_argument("--dir", required=True)
    scan_directory.add_argument("--json", action="store_true")

    collect_rss = subparsers.add_parser("collect-rss", help="Collect article links from RSS or Atom feeds")
    collect_rss.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    collect_rss.add_argument("--feeds", default=str(DEFAULT_PROJECT_DIR / "feeds.txt"))
    collect_rss.add_argument("--limit", type=int, default=20)
    collect_rss.add_argument("--json", action="store_true")

    clip_webpage = subparsers.add_parser("clip-webpage", help="Clip one webpage into cache and enqueue it")
    clip_webpage.add_argument("url")
    clip_webpage.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    clip_webpage.add_argument("--json", action="store_true")

    collect_list = subparsers.add_parser("collect-list", help="Collect items from a Bilibili/YouTube playlist, channel, or favorite list")
    collect_list.add_argument("url")
    collect_list.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    collect_list.add_argument("--platform", default="auto", choices=["auto", "youtube", "bilibili"])
    collect_list.add_argument("--limit", type=int, default=50)
    collect_list.add_argument("--metadata-file", help="Read yt-dlp JSON from a local file instead of running yt-dlp")
    collect_list.add_argument("--json", action="store_true")

    retry = subparsers.add_parser("retry", help="Retry one queue item by id")
    retry.add_argument("id", type=int)
    retry.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    retry.add_argument("--json", action="store_true")

    retry_failed = subparsers.add_parser("retry-failed", help="Retry failed queue items")
    retry_failed.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    retry_failed.add_argument("--limit", type=int, default=50)
    retry_failed.add_argument("--json", action="store_true")

    skip = subparsers.add_parser("skip", help="Mark one queue item as skipped")
    skip.add_argument("id", type=int)
    skip.add_argument("--reason", default="manual skip")
    skip.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    skip.add_argument("--json", action="store_true")

    knowledge = subparsers.add_parser("knowledge-maintenance", help="Generate vault overview, weekly, duplicate, and backlink reports")
    knowledge.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    knowledge.add_argument("--write", action="store_true")
    knowledge.add_argument("--json", action="store_true")

    launcher = subparsers.add_parser("write-launcher", help="Create a one-click launcher for the Tauri studio")
    launcher.add_argument("--config", default=str(DEFAULT_PROJECT_DIR / "config.toml"))
    launcher.add_argument("--json", action="store_true")
    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    config_path = Path(args.config)
    vault = Path(args.vault)
    vault.mkdir(parents=True, exist_ok=True)
    (config_path.parent / "data").mkdir(parents=True, exist_ok=True)
    (config_path.parent / "cache").mkdir(parents=True, exist_ok=True)
    write_default_config(config_path, vault)
    print(f"Wrote config: {config_path}")
    return 0


def _cmd_add(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    store = QueueStore(config.paths.queue_db)
    item = store.enqueue(args.url, title=args.title)
    print(f"Queued #{item.id}: {item.url}")
    return 0


def _cmd_import_links(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    store = QueueStore(config.paths.queue_db)
    count = 0
    for line in Path(args.file).read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        store.enqueue(value)
        count += 1
    print(f"Imported {count} links")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    results = run_pending(config, limit=args.limit)
    for result in results:
        if result.status == "done":
            print(f"Done #{result.item_id}: {result.note_path}")
        else:
            print(f"Failed #{result.item_id}: {result.error}")
    if not results:
        print("No pending items")
    return 0 if all(result.status == "done" for result in results) else 1


def _cmd_doctor(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    config.paths.cache_dir.mkdir(parents=True, exist_ok=True)
    config.paths.queue_db.parent.mkdir(parents=True, exist_ok=True)
    checks = run_doctor(config)
    if args.json:
        required_checks = {"config", "queue_db_parent", "cache_dir", "obsidian_mode", "obsidian_vault", "llm_api_key", "obsidian_rest_key"}
        payload = {
            "ok": all(check.ok for check in checks if check.name in required_checks),
            "checks": [
                {
                    "name": check.name,
                    "ok": check.ok,
                    "detail": check.detail,
                    "required": check.name in required_checks,
                }
                for check in checks
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(format_doctor(checks))
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    store = QueueStore(config.paths.queue_db)
    payload = status_payload(config, store.count_by_status())
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Project: {payload['paths']['project_root']}")
        print(f"Vault: {payload['paths']['obsidian_vault']}")
        print(f"Queue: {payload['queue']}")
    return 0


def _cmd_queue(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    store = QueueStore(config.paths.queue_db)
    status_filter = None if args.status == "all" else args.status
    items = [queue_item_to_dict(item) for item in store.list_recent(limit=args.limit, status=status_filter)]
    payload = {"items": items, "status": args.status}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for item in items:
            print(f"#{item['id']} [{item['status']}] {item['title'] or item['url']}")
    return 0


def _cmd_collect_douyin(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    try:
        result = collect_douyin_favorites(config, count=args.count)
    except Exception as exc:
        payload = {"status": "failed", "error": str(exc)}
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"Failed: {exc}")
        return 1

    payload = {
        "status": "done",
        "run_id": result.run_id,
        "download_dir": str(result.download_dir),
        "queued": result.queued,
        "files": result.files,
        "notes": result.notes,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Queued {result.queued} Douyin favorite export(s)")
    return 0


def _cmd_scan_inbox(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    result = collect_inbox(config, Path(args.inbox))
    payload = {
        "status": "done",
        "inbox_dir": str(result.inbox_dir),
        "queued": result.queued,
        "files": result.files,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Queued {result.queued} inbox file(s)")
    return 0


def _cmd_scan_directory(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    result = collect_directory(config, Path(args.dir))
    payload = {
        "status": "done",
        "directory": str(result.directory),
        "queued": result.queued,
        "files": result.files,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Queued {result.queued} directory file(s)")
    return 0


def _cmd_collect_rss(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    result = collect_rss_feeds(config, Path(args.feeds), limit=args.limit)
    payload = {
        "status": "done",
        "feeds_file": str(result.feeds_file),
        "queued": result.queued,
        "feeds": result.feeds,
        "items": result.items,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Queued {result.queued} RSS item(s)")
    return 0


def _cmd_clip_webpage(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    result = collect_webpage(config, args.url)
    payload = {
        "status": "done",
        "url": result.url,
        "queued": result.queued,
        "title": result.title,
        "cache_path": str(result.cache_path),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Queued webpage: {result.title}")
    return 0


def _cmd_collect_list(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    result = collect_platform_list(
        config,
        args.url,
        limit=args.limit,
        platform=args.platform,
        metadata_file=Path(args.metadata_file) if args.metadata_file else None,
    )
    payload = {
        "status": "done",
        "source_url": result.source_url,
        "queued": result.queued,
        "items": result.items,
        "used_fallback": result.used_fallback,
        "error": result.error,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Queued {result.queued} platform list item(s)")
    return 0


def _cmd_retry(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    store = QueueStore(config.paths.queue_db)
    item = store.retry_item(args.id)
    payload = {"status": item.status, "id": item.id, "url": item.url}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Retried #{item.id}: {item.url}")
    return 0


def _cmd_retry_failed(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    store = QueueStore(config.paths.queue_db)
    retried = store.retry_failed(limit=args.limit)
    payload = {"status": "done", "retried": retried}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Retried {retried} failed item(s)")
    return 0


def _cmd_skip(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    store = QueueStore(config.paths.queue_db)
    store.mark_skipped(args.id, args.reason)
    item = store.get(args.id)
    payload = {"status": item.status, "id": item.id, "reason": item.error}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Skipped #{item.id}: {item.error}")
    return 0


def _cmd_knowledge_maintenance(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    result = build_knowledge_maintenance(config, write=args.write)
    payload = {
        "status": "done",
        "total_notes": result.total_notes,
        "duplicates": result.duplicates,
        "backlink_suggestions": result.backlink_suggestions,
        "files": result.files,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Knowledge maintenance: {result.total_notes} note(s), {len(result.files)} file(s) written")
    return 0


def _cmd_write_launcher(args: argparse.Namespace) -> int:
    config = load_config(Path(args.config))
    launcher = config.config_path.parent / "启动 Obsidian Ingest Studio.cmd"
    text = """@echo off
setlocal
cd /d "%~dp0desktop"
if exist "D:\\Nodejs\\npm.cmd" (
  "D:\\Nodejs\\npm.cmd" run tauri dev
) else (
  npm run tauri dev
)
pause
"""
    launcher.write_text(text, encoding="utf-8")
    payload = {"status": "done", "launcher": str(launcher)}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Wrote launcher: {launcher}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
