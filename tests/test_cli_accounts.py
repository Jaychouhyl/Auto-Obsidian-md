from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.accounts.models import AccountProfile, AccountStatus, Platform
from obsidian_ingest.accounts.store import AccountStore
from obsidian_ingest.cli import main


class CliAccountsTest(unittest.TestCase):
    def test_accounts_list_returns_structured_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            vault = root / "vault"
            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)
            store = AccountStore(root)
            store.save_account(
                AccountProfile(
                    id="douyin-1",
                    platform=Platform.DOUYIN,
                    display_name="忆霖",
                    platform_user_id="60185413619",
                    profile_dir="profiles/douyin/douyin-1",
                    status=AccountStatus.ACTIVE,
                ),
                make_current=True,
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["accounts", "list", "--json", "--config", str(config)])

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "done")
            self.assertEqual(payload["accounts"][0]["display_name"], "忆霖")
            self.assertTrue(payload["accounts"][0]["is_current"])

    def test_accounts_switch_reports_missing_account_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            vault = root / "vault"
            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(
                    [
                        "accounts",
                        "switch",
                        "--platform",
                        "douyin",
                        "--account-id",
                        "missing",
                        "--json",
                        "--config",
                        str(config),
                    ]
                )

            self.assertEqual(code, 1)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "failed")
            self.assertEqual(payload["error"]["code"], "account_not_found")


if __name__ == "__main__":
    unittest.main()
