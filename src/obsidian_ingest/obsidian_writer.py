from __future__ import annotations

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WriteResult:
    relative_path: str


class LocalVaultWriter:
    def __init__(self, vault_path: Path, folder: str = "Inbox/Learning Inbox"):
        self.vault_path = Path(vault_path)
        self.folder = _normalize_folder(folder)

    def write_note(self, title: str, content: str, folder: str | None = None) -> WriteResult:
        target_folder = _normalize_folder(folder) if folder is not None else self.folder
        relative = _join_relative(target_folder, make_safe_filename(title) + ".md")
        target = self.vault_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target = _unique_path(target)
            relative = target.relative_to(self.vault_path).as_posix()
        target.write_text(content, encoding="utf-8")
        return WriteResult(relative)


class ObsidianRestWriter:
    def __init__(self, base_url: str, api_key: str, folder: str = "Inbox/Learning Inbox"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.folder = _normalize_folder(folder)

    def write_note(self, title: str, content: str, folder: str | None = None) -> WriteResult:
        target_folder = _normalize_folder(folder) if folder is not None else self.folder
        relative = _join_relative(target_folder, make_safe_filename(title) + ".md")
        encoded_path = urllib.parse.quote(relative, safe="/")
        request = urllib.request.Request(
            f"{self.base_url}/vault/{encoded_path}",
            data=content.encode("utf-8"),
            method="PUT",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "text/markdown",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
        return WriteResult(relative)


def make_safe_filename(title: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", title.strip())
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .-")
    return cleaned or "Untitled"


def _normalize_folder(folder: str) -> str:
    return folder.strip().replace("\\", "/").strip("/")


def _join_relative(folder: str, filename: str) -> str:
    return f"{folder}/{filename}" if folder else filename


def _unique_path(path: Path) -> Path:
    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    index = 2
    while True:
        candidate = parent / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1
