from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile


BACKUP_FILE_NAMES = (
    "config.toml",
    "links.txt",
    "feeds.txt",
    "douyin-config.yml",
    ".cookies.json",
)
BACKUP_DIRECTORIES = ("data", "accounts")
SKIPPED_ACCOUNT_PARTS = {
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "GraphiteDawnCache",
    "GrShaderCache",
    "ShaderCache",
    "Crashpad",
    "ScriptCache",
    "Safe Browsing Network",
    "SmartScreen",
    "component_crx_cache",
    "cache",
}
SKIPPED_ACCOUNT_FILES = {
    "Login Data",
    "Login Data-journal",
    "Login Data For Account",
    "Login Data For Account-journal",
}


@dataclass(frozen=True)
class BackupResult:
    backup_path: Path
    included: list[str]


@dataclass(frozen=True)
class RestoreResult:
    backup_path: Path
    restored: list[str]


def create_project_backup(config_path: Path, output_dir: Path | None = None) -> BackupResult:
    project_root = config_path.resolve().parent
    target_dir = output_dir.resolve() if output_dir else project_root / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = target_dir / f"obsidian-ingest-backup-{timestamp}.zip"
    if backup_path.exists():
        backup_path = target_dir / f"obsidian-ingest-backup-{timestamp}-{datetime.now().microsecond}.zip"

    included: list[str] = []
    with ZipFile(backup_path, "w", compression=ZIP_DEFLATED) as archive:
        for path in _iter_backup_paths(project_root):
            relative = path.relative_to(project_root).as_posix()
            archive.write(path, relative)
            included.append(relative)

    return BackupResult(backup_path=backup_path, included=included)


def restore_project_backup(config_path: Path, backup_path: Path) -> RestoreResult:
    project_root = config_path.resolve().parent
    backup_path = backup_path.resolve()
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    restored: list[str] = []
    with ZipFile(backup_path, "r") as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            member = _safe_member_path(info.filename)
            if member is None:
                continue
            target = project_root / Path(*member.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info.filename))
            restored.append(member.as_posix())

    return RestoreResult(backup_path=backup_path, restored=restored)


def _iter_backup_paths(project_root: Path) -> list[Path]:
    paths: list[Path] = []
    for name in BACKUP_FILE_NAMES:
        path = project_root / name
        if path.is_file():
            paths.append(path)
    for directory_name in BACKUP_DIRECTORIES:
        directory = project_root / directory_name
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if path.is_file() and _include_backup_path(project_root, path):
                paths.append(path)
    return paths


def _include_backup_path(project_root: Path, path: Path) -> bool:
    relative = path.relative_to(project_root)
    if relative.parts and relative.parts[0] == "accounts":
        if any(part in SKIPPED_ACCOUNT_PARTS for part in relative.parts):
            return False
        if path.name in SKIPPED_ACCOUNT_FILES:
            return False
        if path.name.startswith("CrashpadMetrics"):
            return False
    return True


def _safe_member_path(name: str) -> PurePosixPath | None:
    member = PurePosixPath(name)
    if member.is_absolute() or ".." in member.parts:
        return None
    if not member.parts:
        return None
    top_level = member.parts[0]
    if top_level not in {*BACKUP_FILE_NAMES, *BACKUP_DIRECTORIES}:
        return None
    return member
