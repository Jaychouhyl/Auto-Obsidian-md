from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from obsidian_ingest.accounts.models import AccountProfile, AccountStatus, Platform
from obsidian_ingest.accounts.runtime import current_account_cookie_file
from obsidian_ingest.accounts.service import AccountServiceError
from obsidian_ingest.accounts.store import AccountStore
from obsidian_ingest.acquire import AcquisitionRequest, build_acquisition_command
from obsidian_ingest.collectors.douyin import copy_config_with_account
from obsidian_ingest.collectors.platform_lists import collect_platform_list
from obsidian_ingest.config import load_config, write_default_config


class AccountIntegrationTest(unittest.TestCase):
    def test_yt_dlp_command_uses_cookie_file(self) -> None:
        command = build_acquisition_command(
            AcquisitionRequest(
                "https://www.youtube.com/watch?v=abc",
                "youtube",
                Path("cache"),
            ),
            cookies_file=Path("account.cookies.txt"),
        )

        self.assertIn("--cookies", command)
        self.assertEqual(command[command.index("--cookies") + 1], "account.cookies.txt")

    def test_required_account_reports_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = self._config(Path(tmp))

            with self.assertRaises(AccountServiceError) as raised:
                with current_account_cookie_file(config, Platform.DOUYIN, required=True):
                    pass

            self.assertEqual(raised.exception.code, "account_required")

    def test_temporary_account_cookie_file_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            store = AccountStore(root)
            store.save_account(self._account(store, Platform.YOUTUBE), make_current=True)

            def loader(_profile: Path):
                return [
                    {
                        "domain": ".youtube.com",
                        "path": "/",
                        "secure": True,
                        "expires": 1999999999,
                        "name": "SID",
                        "value": "secret",
                    }
                ]

            with current_account_cookie_file(
                config,
                Platform.YOUTUBE,
                required=True,
                cookie_loader=loader,
            ) as cookie_path:
                self.assertIsNotNone(cookie_path)
                self.assertTrue(cookie_path.exists())

            self.assertFalse(cookie_path.exists())

    def test_douyin_run_config_replaces_cookie_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "douyin.yml"
            target = root / "run.yml"
            source.write_text(
                "number:\n  collect: 1\ncookies:\n  old_cookie: old\nserver:\n  max_jobs: 1\n",
                encoding="utf-8",
            )

            copy_config_with_account(
                source,
                target,
                count=3,
                cookies=[{"name": "sessionid", "value": "new-secret"}],
            )

            text = target.read_text(encoding="utf-8")
            self.assertIn("  collect: 3", text)
            self.assertIn("cookies:\n  sessionid: \"new-secret\"", text)
            self.assertNotIn("old_cookie", text)
            self.assertIn("server:\n  max_jobs: 1", text)

    def test_platform_list_passes_current_account_cookie_to_yt_dlp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = self._config(root)
            store = AccountStore(root)
            store.save_account(self._account(store, Platform.BILIBILI), make_current=True)
            commands: list[list[str]] = []

            def loader(_profile: Path):
                return [
                    {
                        "domain": ".bilibili.com",
                        "path": "/",
                        "secure": True,
                        "expires": 1999999999,
                        "name": "SESSDATA",
                        "value": "secret",
                    }
                ]

            def fake_run(command, **_kwargs):
                commands.append(command)
                return subprocess.CompletedProcess(
                    command,
                    0,
                    stdout=json.dumps(
                        {
                            "entries": [
                                {
                                    "id": "BV1TEST",
                                    "title": "测试视频",
                                    "webpage_url": "https://www.bilibili.com/video/BV1TEST",
                                }
                            ]
                        }
                    ),
                    stderr="",
                )

            with patch("obsidian_ingest.collectors.platform_lists.subprocess.run", side_effect=fake_run):
                result = collect_platform_list(
                    config,
                    "https://space.bilibili.com/42/favlist",
                    platform="bilibili",
                    cookie_loader=loader,
                )

            self.assertEqual(result.queued, 1)
            self.assertIn("--cookies", commands[0])
            cookie_path = Path(commands[0][commands[0].index("--cookies") + 1])
            self.assertFalse(cookie_path.exists())

    @staticmethod
    def _config(root: Path):
        config_path = root / "config.toml"
        write_default_config(config_path, root / "vault")
        return load_config(config_path)

    @staticmethod
    def _account(store: AccountStore, platform: Platform) -> AccountProfile:
        account_id = f"{platform.value}-test"
        profile = store.profile_dir(platform, account_id)
        return AccountProfile(
            id=account_id,
            platform=platform,
            display_name="测试账号",
            platform_user_id="100",
            profile_dir=store.relative_profile_dir(profile),
            status=AccountStatus.ACTIVE,
        )


if __name__ == "__main__":
    unittest.main()
