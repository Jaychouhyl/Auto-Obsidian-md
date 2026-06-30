from __future__ import annotations

import json
import platform
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from .config import load_config
from .doctor import run_doctor
from .json_output import status_payload
from .queue_store import QueueStore


REDACTED_KEYS = (
    "api_key",
    "rest_api_key",
    "notion_token",
    "password",
    "secret",
    "token",
    "cookie",
)


@dataclass(frozen=True)
class DiagnosticPackageResult:
    package_path: Path
    included: list[str]


def create_diagnostic_package(config_path: Path, output_dir: Path | None = None) -> DiagnosticPackageResult:
    config = load_config(config_path)
    project_root = config.config_path.resolve().parent
    target_dir = output_dir.resolve() if output_dir else project_root / "logs"
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    package_path = target_dir / f"obsidian-ingest-diagnostics-{timestamp}.zip"

    store = QueueStore(config.paths.queue_db)
    doctor_checks = run_doctor(config)
    included: list[str] = []

    with ZipFile(package_path, "w", compression=ZIP_DEFLATED) as archive:
        _write_json(
            archive,
            "diagnostic-manifest.json",
            {
                "app": "Auto Obsidian MD",
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "privacy": "Local diagnostic package. It redacts common secrets and does not include account browser profiles.",
                "machine": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "python": platform.python_version(),
                },
            },
            included,
        )
        _write_json(
            archive,
            "status.json",
            status_payload(config, store.count_by_status()),
            included,
        )
        _write_json(
            archive,
            "doctor.json",
            {
                "ok": all(check.ok for check in doctor_checks),
                "checks": [
                    {
                        "name": check.name,
                        "ok": check.ok,
                        "detail": check.detail,
                    }
                    for check in doctor_checks
                ],
            },
            included,
        )
        _write_json(
            archive,
            "queue-summary.json",
            {
                "counts": store.count_by_status(),
                "recent_failed": [
                    {
                        "id": item.id,
                        "platform": item.platform,
                        "content_type": item.content_type,
                        "title": item.title,
                        "error": item.error,
                        "updated_at": item.updated_at,
                    }
                    for item in store.list_recent(limit=20, status="failed")
                ],
            },
            included,
        )
        if config.config_path.is_file():
            _write_text(archive, "config.redacted.toml", _redact_text(config.config_path.read_text(encoding="utf-8")), included)
        _write_source_summary(archive, project_root, included)
        _write_recent_logs(archive, project_root / "logs", included)

    return DiagnosticPackageResult(package_path=package_path, included=included)


def _write_json(archive: ZipFile, name: str, payload: object, included: list[str]) -> None:
    archive.writestr(name, json.dumps(payload, ensure_ascii=False, indent=2))
    included.append(name)


def _write_text(archive: ZipFile, name: str, text: str, included: list[str]) -> None:
    archive.writestr(name, text)
    included.append(name)


def _write_source_summary(archive: ZipFile, project_root: Path, included: list[str]) -> None:
    payload = {}
    for filename in ("links.txt", "feeds.txt"):
        path = project_root / filename
        if not path.is_file():
            payload[filename] = {"exists": False, "non_empty_lines": 0}
            continue
        lines = [line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()]
        payload[filename] = {
            "exists": True,
            "non_empty_lines": len([line for line in lines if line and not line.startswith("#")]),
        }
    _write_json(archive, "source-files-summary.json", payload, included)


def _write_recent_logs(archive: ZipFile, logs_dir: Path, included: list[str]) -> None:
    if not logs_dir.is_dir():
        return
    files = sorted(
        [path for path in logs_dir.iterdir() if path.is_file() and path.suffix.lower() in {".log", ".txt", ".json"}],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )[:10]
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        _write_text(archive, f"logs/{path.name}", _redact_text(text[-120_000:]), included)


def _redact_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip().lower()
        if any(key in stripped for key in REDACTED_KEYS) and "=" in line:
            key, _ = line.split("=", 1)
            lines.append(f"{key}= \"<redacted>\"")
        elif any(key in stripped for key in REDACTED_KEYS) and ":" in line:
            lines.append(re.sub(r'(:\s*)"[^"]*"', r'\1"<redacted>"', line, count=1))
        else:
            lines.append(line)
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")
