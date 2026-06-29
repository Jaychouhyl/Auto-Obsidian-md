from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.collectors.douyin import (
    build_douyin_favorites_url,
    copy_config_with_collect_count,
    discover_douyin_exports,
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

    def test_prefers_text_export_over_video(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "collect" / "video-a"
            nested.mkdir(parents=True)
            (nested / "video-a.txt").write_text("hello", encoding="utf-8")
            (nested / "video-a.mp4").write_text("binary", encoding="utf-8")

            exports = discover_douyin_exports(root)

            self.assertEqual([path.name for path in exports], ["video-a.txt"])

    def test_falls_back_to_video_when_no_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "collect" / "video-b"
            nested.mkdir(parents=True)
            (nested / "video-b.mp4").write_text("binary", encoding="utf-8")
            (nested / "video-b_music.mp3").write_text("noise", encoding="utf-8")
            (nested / "video-b_cover.jpg").write_text("img", encoding="utf-8")

            exports = discover_douyin_exports(root)

            self.assertEqual([path.name for path in exports], ["video-b.mp4"])

    def test_keeps_separate_videos_in_same_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "collect" / "live-post"
            nested.mkdir(parents=True)
            (nested / "post_live_1.mp4").write_text("v1", encoding="utf-8")
            (nested / "post_live_2.mp4").write_text("v2", encoding="utf-8")

            exports = discover_douyin_exports(root)

            self.assertEqual(
                [path.name for path in exports],
                ["post_live_1.mp4", "post_live_2.mp4"],
            )

    def test_uses_downloader_manifest_order_before_file_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "collect" / "z-last-name"
            second = root / "collect" / "a-first-name"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            (first / "z-last-name.txt").write_text("first", encoding="utf-8")
            (second / "a-first-name.txt").write_text("second", encoding="utf-8")
            (root / "download_manifest.jsonl").write_text(
                '{"file_paths":["collect/z-last-name/z-last-name.txt"]}\n'
                '{"file_paths":["collect/a-first-name/a-first-name.txt"]}\n',
                encoding="utf-8",
            )

            exports = discover_douyin_exports(root)

            self.assertEqual([path.name for path in exports], ["z-last-name.txt", "a-first-name.txt"])

    def test_creates_markdown_export_for_gallery_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "collect" / "gallery-post"
            nested.mkdir(parents=True)
            (nested / "gallery-post_1.jpg").write_text("img", encoding="utf-8")
            (nested / "gallery-post_2.webp").write_text("img", encoding="utf-8")
            (nested / "gallery-post_data.json").write_text(
                '{"media_type":"gallery","desc":"二战提分经验贴","author_name":"学习博主","date":"2026-04-08","tags":["考研","二战"],"aweme_id":"123"}',
                encoding="utf-8",
            )

            exports = discover_douyin_exports(root)

            self.assertEqual([path.name for path in exports], ["gallery-post_gallery.md"])
            text = exports[0].read_text(encoding="utf-8")
            self.assertIn("# 二战提分经验贴", text)
            self.assertIn("- 作者：学习博主", text)
            self.assertIn("- 标签：考研、二战", text)
            self.assertIn("- 图片数量：2", text)

    def test_does_not_create_gallery_markdown_when_video_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "collect" / "video-post"
            nested.mkdir(parents=True)
            (nested / "video-post.mp4").write_text("binary", encoding="utf-8")
            (nested / "video-post_data.json").write_text(
                '{"media_type":"video","desc":"video desc"}',
                encoding="utf-8",
            )

            exports = discover_douyin_exports(root)

            self.assertEqual([path.name for path in exports], ["video-post.mp4"])


class InboxCollectorTest(unittest.TestCase):
    def test_scans_supported_files_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.pdf").write_text("pdf", encoding="utf-8")
            (root / "b.mp3").write_text("mp3", encoding="utf-8")
            (root / "c.png").write_bytes(b"png")
            (root / "ignore.tmp").write_text("tmp", encoding="utf-8")

            files = scan_inbox_files(root)

            self.assertEqual([path.name for path in files], ["a.pdf", "b.mp3", "c.png"])
            self.assertIn(".pdf", SUPPORTED_INBOX_EXTENSIONS)
            self.assertIn(".png", SUPPORTED_INBOX_EXTENSIONS)


if __name__ == "__main__":
    unittest.main()
