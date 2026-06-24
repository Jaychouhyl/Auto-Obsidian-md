from __future__ import annotations

import json
import os
import shutil
import threading
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import AccountProfile, Platform


class AccountStore:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root).resolve()
        self.accounts_dir = self.project_root / "accounts"
        self.profiles_dir = self.accounts_dir / "profiles"
        self.metadata_path = self.accounts_dir / "accounts.json"
        self._lock = threading.RLock()
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_metadata()

    def list(self, platform: Platform | None = None) -> list[AccountProfile]:
        with self._lock:
            data = self._read()
            current = data["current"]
            result = []
            for raw in data["accounts"]:
                account = AccountProfile.from_dict(raw)
                if platform is not None and account.platform != platform:
                    continue
                result.append(account.with_current(current.get(account.platform.value) == account.id))
            return result

    def get(self, account_id: str) -> AccountProfile | None:
        return next((account for account in self.list() if account.id == account_id), None)

    def current(self, platform: Platform) -> AccountProfile | None:
        return next((account for account in self.list(platform) if account.is_current), None)

    def save_account(self, account: AccountProfile, make_current: bool = False) -> AccountProfile:
        with self._lock:
            data = self._read()
            now = _now()
            existing = next((item for item in data["accounts"] if item.get("id") == account.id), None)
            created_at = str(existing.get("created_at", "")) if existing else account.created_at
            stored = replace(
                account,
                profile_dir=self._validated_relative_profile(account.profile_dir),
                created_at=created_at or now,
                updated_at=now,
                is_current=False,
            )
            data["accounts"] = [item for item in data["accounts"] if item.get("id") != account.id]
            data["accounts"].append(stored.to_dict())
            if make_current or not data["current"].get(account.platform.value):
                data["current"][account.platform.value] = account.id
            self._write(data)
            return self.get(account.id) or stored

    def set_current(self, platform: Platform, account_id: str) -> AccountProfile:
        with self._lock:
            account = self.get(account_id)
            if account is None or account.platform != platform:
                raise KeyError(f"account not found for {platform.value}: {account_id}")
            data = self._read()
            data["current"][platform.value] = account_id
            self._write(data)
            return self.get(account_id) or account.with_current(True)

    def delete(self, account_id: str, remove_profile: bool = True) -> None:
        with self._lock:
            account = self.get(account_id)
            if account is None:
                raise KeyError(f"account not found: {account_id}")
            data = self._read()
            data["accounts"] = [item for item in data["accounts"] if item.get("id") != account_id]
            if data["current"].get(account.platform.value) == account_id:
                replacement = next(
                    (
                        item["id"]
                        for item in data["accounts"]
                        if item.get("platform") == account.platform.value
                    ),
                    None,
                )
                if replacement:
                    data["current"][account.platform.value] = replacement
                else:
                    data["current"].pop(account.platform.value, None)
            self._write(data)
            if remove_profile:
                profile = self.resolve_profile_dir(account.profile_dir)
                if profile.exists():
                    shutil.rmtree(profile)

    def profile_dir(self, platform: Platform, account_id: str) -> Path:
        safe_id = _safe_segment(account_id)
        result = self.profiles_dir / platform.value / safe_id
        result.mkdir(parents=True, exist_ok=True)
        return result

    def relative_profile_dir(self, profile_dir: Path) -> str:
        resolved = Path(profile_dir).resolve()
        try:
            return resolved.relative_to(self.accounts_dir.resolve()).as_posix()
        except ValueError as exc:
            raise ValueError("profile directory must be inside the accounts directory") from exc

    def resolve_profile_dir(self, relative_path: str) -> Path:
        clean = self._validated_relative_profile(relative_path)
        resolved = (self.accounts_dir / clean).resolve()
        if self.accounts_dir.resolve() not in resolved.parents:
            raise ValueError("profile directory escapes the accounts directory")
        return resolved

    def _validated_relative_profile(self, value: str) -> str:
        path = Path(str(value).replace("\\", "/"))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("profile directory must be a safe relative path")
        clean = path.as_posix().strip("/")
        if not clean.startswith("profiles/"):
            raise ValueError("profile directory must be under profiles/")
        return clean

    def _ensure_metadata(self) -> None:
        if not self.metadata_path.exists():
            self._write(_empty_data())
            return
        try:
            self._read()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            backup = self.accounts_dir / f"accounts.corrupt-{stamp}.json"
            os.replace(self.metadata_path, backup)
            self._write(_empty_data())

    def _read(self) -> dict[str, Any]:
        data = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        if data.get("version") != 1:
            raise ValueError("unsupported account metadata version")
        if not isinstance(data.get("accounts"), list) or not isinstance(data.get("current"), dict):
            raise ValueError("invalid account metadata")
        return data

    def _write(self, data: dict[str, Any]) -> None:
        self.accounts_dir.mkdir(parents=True, exist_ok=True)
        temporary = self.metadata_path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.metadata_path)


def _empty_data() -> dict[str, Any]:
    return {"version": 1, "accounts": [], "current": {}}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _safe_segment(value: str) -> str:
    safe = "".join(character if character.isalnum() or character in "-_." else "-" for character in value.strip())
    safe = safe.strip("-.")
    if not safe:
        raise ValueError("account id is empty")
    return safe[:120]
