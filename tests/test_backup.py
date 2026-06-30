from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from obsidian_ingest.backup import create_project_backup, restore_project_backup
from obsidian_ingest.cli import main


class BackupTest(unittest.TestCase):
    def test_create_backup_includes_project_state_without_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            config.write_text("[paths]\n", encoding="utf-8")
            (root / "links.txt").write_text("https://example.com\n", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "queue.sqlite").write_bytes(b"sqlite")
            (root / "accounts" / "profiles").mkdir(parents=True)
            (root / "accounts" / "profiles" / "douyin.json").write_text("{}", encoding="utf-8")
            (root / "accounts" / "profiles" / "Cache").mkdir()
            (root / "accounts" / "profiles" / "Cache" / "data_0").write_bytes(b"cache")
            (root / "accounts" / "profiles" / "Login Data").write_bytes(b"password-db")
            (root / "cache").mkdir()
            (root / "cache" / "video.mp4").write_bytes(b"large")

            result = create_project_backup(config)

            self.assertTrue(result.backup_path.exists())
            self.assertIn("config.toml", result.included)
            self.assertIn("backup-manifest.json", result.included)
            self.assertIn("links.txt", result.included)
            self.assertIn("data/queue.sqlite", result.included)
            self.assertIn("accounts/profiles/douyin.json", result.included)
            self.assertNotIn("accounts/profiles/Cache/data_0", result.included)
            self.assertNotIn("accounts/profiles/Login Data", result.included)
            self.assertNotIn("cache/video.mp4", result.included)
            with ZipFile(result.backup_path) as archive:
                self.assertIn("config.toml", archive.namelist())
                manifest = json.loads(archive.read("backup-manifest.json").decode("utf-8"))
                self.assertEqual(manifest["app"], "Auto Obsidian MD")
                self.assertIn("Do not publish", manifest["privacy"])

    def test_restore_backup_overwrites_allowed_project_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            config.write_text("old", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "queue.sqlite").write_text("old-db", encoding="utf-8")

            backup = create_project_backup(config)
            config.write_text("changed", encoding="utf-8")
            (root / "data" / "queue.sqlite").write_text("changed-db", encoding="utf-8")

            result = restore_project_backup(config, backup.backup_path)

            self.assertIn("config.toml", result.restored)
            self.assertIn("data/queue.sqlite", result.restored)
            self.assertEqual(config.read_text(encoding="utf-8"), "old")
            self.assertEqual((root / "data" / "queue.sqlite").read_text(encoding="utf-8"), "old-db")

    def test_cli_backup_and_restore_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            config.write_text("before", encoding="utf-8")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["backup", "--json", "--config", str(config)])

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "done")
            backup_path = payload["backup_path"]

            config.write_text("after", encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["restore", backup_path, "--yes", "--json", "--config", str(config)])

            self.assertEqual(code, 0)
            self.assertEqual(config.read_text(encoding="utf-8"), "before")


if __name__ == "__main__":
    unittest.main()
