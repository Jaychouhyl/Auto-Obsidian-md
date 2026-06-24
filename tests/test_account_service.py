from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.accounts.models import AccountCandidate, AccountStatus, Platform
from obsidian_ingest.accounts.service import AccountService


class FakeBrowser:
    def __init__(self) -> None:
        self.logins: list[tuple[Path, Platform]] = []
        self.imports: list[tuple[Path, list[dict[str, object]]]] = []

    def login(self, profile_dir, provider, timeout_seconds=600):
        self.logins.append((Path(profile_dir), provider.platform))
        return AccountCandidate(provider.platform, "候选账号", "user-100", provider.identity_url)

    def verify(self, profile_dir, provider):
        if provider.platform == Platform.DOUYIN:
            return AccountCandidate(provider.platform, "忆霖", "60185413619", provider.identity_url)
        return AccountCandidate(provider.platform, "候选账号", "user-100", provider.identity_url)

    def import_cookies(self, profile_dir, cookies):
        self.imports.append((Path(profile_dir), list(cookies)))


class AccountServiceTest(unittest.TestCase):
    def test_login_creates_candidate_and_confirm_adds_current_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = AccountService(Path(tmp), browser=FakeBrowser())

            candidate = service.start_login(Platform.YOUTUBE)

            self.assertEqual(service.list_accounts(), [])
            self.assertEqual(candidate["display_name"], "候选账号")
            self.assertTrue(candidate["candidate_id"])

            account = service.confirm_login(candidate["candidate_id"], make_current=True)

            self.assertEqual(account.display_name, "候选账号")
            self.assertTrue(account.is_current)
            self.assertEqual(account.status, AccountStatus.ACTIVE)
            self.assertFalse(service.candidate_path(candidate["candidate_id"]).exists())

    def test_cancel_login_removes_candidate_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = AccountService(Path(tmp), browser=FakeBrowser())
            candidate = service.start_login(Platform.TIKTOK)
            profile_dir = service.candidate_profile_dir(candidate["candidate_id"])
            self.assertTrue(profile_dir.exists())

            service.cancel_login(candidate["candidate_id"])

            self.assertFalse(profile_dir.exists())
            self.assertFalse(service.candidate_path(candidate["candidate_id"]).exists())

    def test_verify_and_switch_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = AccountService(Path(tmp), browser=FakeBrowser())
            first = service.confirm_login(service.start_login(Platform.BILIBILI)["candidate_id"])
            second_candidate = service.start_login(Platform.BILIBILI)
            second_path = service.candidate_path(second_candidate["candidate_id"])
            payload = json.loads(second_path.read_text(encoding="utf-8"))
            payload["platform_user_id"] = "user-200"
            payload["display_name"] = "第二账号"
            second_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            second = service.confirm_login(second_candidate["candidate_id"], make_current=False)

            service.switch_account(Platform.BILIBILI, second.id)
            verified = service.verify_account(first.id)

            self.assertEqual(service.current_account(Platform.BILIBILI).id, second.id)
            self.assertEqual(verified.status, AccountStatus.ACTIVE)
            self.assertTrue(verified.last_verified_at)

    def test_migrates_legacy_douyin_cookie_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / ".cookies.json"
            legacy.write_text(json.dumps({"sessionid": "secret", "ttwid": "token"}), encoding="utf-8")
            browser = FakeBrowser()
            service = AccountService(root, browser=browser)

            candidate = service.migrate_legacy_douyin(legacy)

            self.assertEqual(candidate["display_name"], "忆霖")
            self.assertEqual(candidate["platform_user_id"], "60185413619")
            self.assertEqual(len(browser.imports), 1)
            self.assertEqual({item["name"] for item in browser.imports[0][1]}, {"sessionid", "ttwid"})
            self.assertTrue(all(float(item["expires"]) > 0 for item in browser.imports[0][1]))
            self.assertTrue((root / "accounts" / "legacy-backups" / ".cookies.json").exists())

    def test_auto_migrates_legacy_douyin_once_when_account_list_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".cookies.json").write_text(
                json.dumps({"sessionid": "secret"}),
                encoding="utf-8",
            )
            service = AccountService(root, browser=FakeBrowser())

            migrated = service.auto_migrate_legacy_douyin()
            repeated = service.auto_migrate_legacy_douyin()

            self.assertIsNotNone(migrated)
            self.assertTrue(migrated.is_current)
            self.assertEqual(migrated.display_name, "忆霖")
            self.assertIsNone(repeated)
            marker = json.loads(
                (root / "accounts" / "legacy-migration.json").read_text(encoding="utf-8")
            )
            self.assertEqual(marker["status"], "complete")


if __name__ == "__main__":
    unittest.main()
