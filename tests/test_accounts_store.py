from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.accounts.models import AccountProfile, AccountStatus, Platform
from obsidian_ingest.accounts.store import AccountStore


class AccountStoreTest(unittest.TestCase):
    def test_platforms_cover_supported_account_sources(self) -> None:
        self.assertEqual(
            {platform.value for platform in Platform},
            {"douyin", "bilibili", "youtube", "tiktok"},
        )

    def test_adds_accounts_and_keeps_one_current_account_per_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp))
            first = self._account("douyin", "忆霖", "60185413619")
            second = self._account("douyin", "学习号", "9988")

            store.save_account(first, make_current=True)
            store.save_account(second, make_current=False)

            self.assertEqual(store.current(Platform.DOUYIN).id, first.id)
            self.assertEqual([account.id for account in store.list(Platform.DOUYIN)], [first.id, second.id])

            store.set_current(Platform.DOUYIN, second.id)

            self.assertEqual(store.current(Platform.DOUYIN).id, second.id)
            self.assertFalse(store.get(first.id).is_current)
            self.assertTrue(store.get(second.id).is_current)

    def test_deleting_current_account_selects_remaining_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = AccountStore(Path(tmp))
            first = self._account("youtube", "主账号", "channel-1")
            second = self._account("youtube", "备用账号", "channel-2")
            store.save_account(first, make_current=True)
            store.save_account(second, make_current=False)

            store.delete(first.id, remove_profile=False)

            self.assertEqual(store.current(Platform.YOUTUBE).id, second.id)
            self.assertIsNone(store.get(first.id))

    def test_creates_isolated_profile_directory_and_metadata_has_no_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = AccountStore(root)
            profile_dir = store.profile_dir(Platform.BILIBILI, "account-1")
            account = AccountProfile(
                id="account-1",
                platform=Platform.BILIBILI,
                display_name="知识收藏",
                platform_user_id="42",
                profile_dir=store.relative_profile_dir(profile_dir),
                status=AccountStatus.ACTIVE,
            )
            store.save_account(account, make_current=True)

            self.assertTrue(profile_dir.is_dir())
            raw = (root / "accounts" / "accounts.json").read_text(encoding="utf-8")
            self.assertNotIn("cookie", raw.lower())
            self.assertNotIn("session", raw.lower())
            self.assertNotIn(str(root), raw)

    def test_recovers_from_corrupt_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            metadata = root / "accounts" / "accounts.json"
            metadata.parent.mkdir(parents=True)
            metadata.write_text("{not-json", encoding="utf-8")

            store = AccountStore(root)

            self.assertEqual(store.list(), [])
            backups = list(metadata.parent.glob("accounts.corrupt-*.json"))
            self.assertEqual(len(backups), 1)
            self.assertTrue(metadata.exists())
            self.assertEqual(json.loads(metadata.read_text(encoding="utf-8"))["version"], 1)

    @staticmethod
    def _account(platform: str, name: str, user_id: str) -> AccountProfile:
        value = Platform(platform)
        safe_id = f"{platform}-{user_id}"
        return AccountProfile(
            id=safe_id,
            platform=value,
            display_name=name,
            platform_user_id=user_id,
            profile_dir=f"profiles/{platform}/{safe_id}",
            status=AccountStatus.ACTIVE,
        )


if __name__ == "__main__":
    unittest.main()
