from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.collectors.douyin import (
    build_douyin_favorites_url,
    copy_config_with_collect_count,
    discover_douyin_text_exports,
)
from obsidian_ingest.collectors.inbox import SUPPORTED_INBOX_EXTENSIONS, scan_inbox_files


class DouyinCollectorTest(unittest.TestCase):
    def test_builds_timestamped_favorites_url(self) -> None:
        url = build_douyin_favorites_url("20260620-120000")
        self.assertIn("https://www.douyin.com/user/self?showTab=favorite_collection", url)
        self.assertIn("obsidian_ingest_run=20260620-120000", url)

    def test_copies_config_with_collect_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "douyin-config.yml"
            target = root / "run.yml"
            source.write_text(
                "number:\n  collect: 1\n  like: 0\n",
                encoding="utf-8",
            )

            copy_config_with_collect_count(source, target, count=7)

            text = target.read_text(encoding="utf-8")
            self.assertIn("  collect: 7", text)
            self.assertIn("  like: 0", text)

    def test_discovers_text_exports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "collect" / "video-a"
            nested.mkdir(parents=True)
            (nested / "video-a.txt").write_text("hello", encoding="utf-8")
            (nested / "video-a.mp4").write_text("binary", encoding="utf-8")

            exports = discover_douyin_text_exports(root)

            self.assertEqual([path.name for path in exports], ["video-a.txt"])


class InboxCollectorTest(unittest.TestCase):
    def test_scans_supported_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.pdf").write_text("pdf", encoding="utf-8")
            (root / "b.mp3").write_text("mp3", encoding="utf-8")
            (root / "ignore.tmp").write_text("tmp", encoding="utf-8")

            files = scan_inbox_files(root)

            self.assertEqual([path.name for path in files], ["a.pdf", "b.mp3"])
            self.assertIn(".pdf", SUPPORTED_INBOX_EXTENSIONS)


if __name__ == "__main__":
    unittest.main()
