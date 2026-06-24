from __future__ import annotations

import hashlib
import json
import shutil
import uuid
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .browser import EdgeAccountBrowser
from .migration import backup_legacy_file, load_legacy_douyin_cookies
from .models import AccountProfile, AccountStatus, Platform
from .providers import provider_for
from .providers.base import AccountIdentityError
from .store import AccountStore


class AccountServiceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class AccountService:
    def __init__(self, project_root: Path, browser: Any | None = None):
        self.project_root = Path(project_root).resolve()
        self.store = AccountStore(self.project_root)
        self.browser = browser or EdgeAccountBrowser()
        self.candidates_dir = self.store.accounts_dir / "candidates"
        self.candidates_dir.mkdir(parents=True, exist_ok=True)

    def list_accounts(self, platform: Platform | None = None) -> list[AccountProfile]:
        return self.store.list(platform)

    def current_account(self, platform: Platform) -> AccountProfile | None:
        return self.store.current(platform)

    def start_login(self, platform: Platform, timeout_seconds: int = 600) -> dict[str, Any]:
        candidate_id = uuid.uuid4().hex
        profile_dir = self.store.profile_dir(platform, f"pending-{candidate_id}")
        try:
            identity = self.browser.login(
                profile_dir,
                provider_for(platform),
                timeout_seconds=timeout_seconds,
            )
        except Exception:
            shutil.rmtree(profile_dir, ignore_errors=True)
            raise
        payload = {
            "candidate_id": candidate_id,
            **identity.to_dict(),
            "profile_dir": self.store.relative_profile_dir(profile_dir),
            "created_at": _now(),
        }
        self._write_candidate(candidate_id, payload)
        return payload

    def confirm_login(self, candidate_id: str, make_current: bool = True) -> AccountProfile:
        payload = self._read_candidate(candidate_id)
        platform = Platform(payload["platform"])
        account_id = _account_id(platform, str(payload["platform_user_id"]))
        source_profile = self.store.resolve_profile_dir(payload["profile_dir"])
        target_profile = self.store.profile_dir(platform, account_id)
        if source_profile.resolve() != target_profile.resolve():
            if target_profile.exists():
                shutil.rmtree(target_profile)
            target_profile.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_profile), str(target_profile))
        account = AccountProfile(
            id=account_id,
            platform=platform,
            display_name=str(payload["display_name"]),
            platform_user_id=str(payload["platform_user_id"]),
            profile_dir=self.store.relative_profile_dir(target_profile),
            status=AccountStatus.ACTIVE,
            last_verified_at=_now(),
        )
        stored = self.store.save_account(account, make_current=make_current)
        self.candidate_path(candidate_id).unlink(missing_ok=True)
        return stored

    def cancel_login(self, candidate_id: str) -> None:
        payload = self._read_candidate(candidate_id)
        profile = self.store.resolve_profile_dir(payload["profile_dir"])
        shutil.rmtree(profile, ignore_errors=True)
        self.candidate_path(candidate_id).unlink(missing_ok=True)

    def verify_account(self, account_id: str) -> AccountProfile:
        account = self._require_account(account_id)
        profile_dir = self.store.resolve_profile_dir(account.profile_dir)
        try:
            identity = self.browser.verify(profile_dir, provider_for(account.platform))
            updated = replace(
                account,
                display_name=identity.display_name,
                platform_user_id=identity.platform_user_id,
                status=AccountStatus.ACTIVE,
                last_verified_at=_now(),
                error="",
            )
        except AccountIdentityError as exc:
            updated = replace(account, status=AccountStatus.EXPIRED, error=str(exc))
        return self.store.save_account(updated, make_current=account.is_current)

    def relogin_account(self, account_id: str, timeout_seconds: int = 600) -> dict[str, Any]:
        account = self._require_account(account_id)
        candidate = self.start_login(account.platform, timeout_seconds=timeout_seconds)
        candidate["replaces_account_id"] = account.id
        self._write_candidate(candidate["candidate_id"], candidate)
        return candidate

    def switch_account(self, platform: Platform, account_id: str) -> AccountProfile:
        try:
            return self.store.set_current(platform, account_id)
        except KeyError as exc:
            raise AccountServiceError(
                "account_not_found",
                f"没有找到 {platform.value} 账号: {account_id}",
            ) from exc

    def delete_account(self, account_id: str) -> None:
        try:
            self.store.delete(account_id)
        except KeyError as exc:
            raise AccountServiceError("account_not_found", f"没有找到账号: {account_id}") from exc

    def migrate_legacy_douyin(
        self,
        source: Path,
        fallback_name: str = "",
        fallback_user_id: str = "",
    ) -> dict[str, Any]:
        cookie_source = Path(source)
        cookies = load_legacy_douyin_cookies(cookie_source)
        candidate_id = uuid.uuid4().hex
        profile_dir = self.store.profile_dir(Platform.DOUYIN, f"pending-{candidate_id}")
        try:
            self.browser.import_cookies(profile_dir, cookies)
            identity = self.browser.verify(profile_dir, provider_for(Platform.DOUYIN))
            display_name = identity.display_name
            user_id = identity.platform_user_id
            source_url = identity.source_url
        except AccountIdentityError:
            if not fallback_name or not fallback_user_id:
                shutil.rmtree(profile_dir, ignore_errors=True)
                raise
            display_name = fallback_name
            user_id = fallback_user_id
            source_url = provider_for(Platform.DOUYIN).identity_url
        except Exception:
            shutil.rmtree(profile_dir, ignore_errors=True)
            raise
        backup_legacy_file(cookie_source, self.store.accounts_dir / "legacy-backups")
        payload = {
            "candidate_id": candidate_id,
            "platform": Platform.DOUYIN.value,
            "display_name": display_name,
            "platform_user_id": user_id,
            "source_url": source_url,
            "profile_dir": self.store.relative_profile_dir(profile_dir),
            "created_at": _now(),
            "migrated_from": cookie_source.name,
        }
        self._write_candidate(candidate_id, payload)
        return payload

    def auto_migrate_legacy_douyin(self) -> AccountProfile | None:
        if self.store.list(Platform.DOUYIN):
            return None
        marker = self.store.accounts_dir / "legacy-migration.json"
        if marker.exists():
            return None
        source = next(
            (
                path
                for path in (
                    self.project_root / ".cookies.json",
                    self.project_root / "douyin-config.yml",
                )
                if path.exists()
            ),
            None,
        )
        if source is None:
            return None
        try:
            candidate = self.migrate_legacy_douyin(source)
            account = self.confirm_login(candidate["candidate_id"], make_current=True)
            self._write_json(
                marker,
                {
                    "status": "complete",
                    "account_id": account.id,
                    "source": source.name,
                    "updated_at": _now(),
                },
            )
            return account
        except Exception as exc:
            self._write_json(
                marker,
                {
                    "status": "failed",
                    "source": source.name,
                    "error": str(exc),
                    "updated_at": _now(),
                },
            )
            return None

    def candidate_path(self, candidate_id: str) -> Path:
        return self.candidates_dir / f"{_safe_candidate_id(candidate_id)}.json"

    def candidate_profile_dir(self, candidate_id: str) -> Path:
        payload = self._read_candidate(candidate_id)
        return self.store.resolve_profile_dir(payload["profile_dir"])

    def _require_account(self, account_id: str) -> AccountProfile:
        account = self.store.get(account_id)
        if account is None:
            raise AccountServiceError("account_not_found", f"没有找到账号: {account_id}")
        return account

    def _write_candidate(self, candidate_id: str, payload: dict[str, Any]) -> None:
        self._write_json(self.candidate_path(candidate_id), payload)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)

    def _read_candidate(self, candidate_id: str) -> dict[str, Any]:
        path = self.candidate_path(candidate_id)
        if not path.exists():
            raise AccountServiceError("candidate_not_found", f"登录候选已失效: {candidate_id}")
        return json.loads(path.read_text(encoding="utf-8"))


def account_to_dict(account: AccountProfile) -> dict[str, Any]:
    return {**account.to_dict(), "is_current": account.is_current}


def _account_id(platform: Platform, platform_user_id: str) -> str:
    digest = hashlib.sha256(f"{platform.value}:{platform_user_id}".encode("utf-8")).hexdigest()[:16]
    return f"{platform.value}-{digest}"


def _safe_candidate_id(value: str) -> str:
    if not value or any(character not in "0123456789abcdef" for character in value.lower()):
        raise AccountServiceError("invalid_candidate_id", "登录候选 ID 无效。")
    return value.lower()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
