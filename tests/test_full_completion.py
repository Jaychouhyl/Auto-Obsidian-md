from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.cli import main
from obsidian_ingest.collectors.platform_lists import parse_yt_dlp_flat_json
from obsidian_ingest.knowledge import build_knowledge_maintenance
from obsidian_ingest.config import load_config
from obsidian_ingest.queue_store import QueueStore


class FullCompletionTest(unittest.TestCase):
    def test_parses_yt_dlp_flat_playlist_entries(self) -> None:
        raw = "\ufeff" + json.dumps(
            {
                "entries": [
                    {"title": "Video A", "webpage_url": "https://youtu.be/a"},
                    {"title": "Video B", "id": "b", "ie_key": "Youtube"},
                    {"title": "Video C", "id": "BV1xx", "ie_key": "BiliBili"},
                ]
            }
        )

        items = parse_yt_dlp_flat_json(raw, source_url="https://www.youtube.com/playlist?list=abc")

        self.assertEqual([item.title for item in items], ["Video A", "Video B", "Video C"])
        self.assertEqual(items[0].url, "https://youtu.be/a")
        self.assertEqual(items[1].url, "https://www.youtube.com/watch?v=b")
        self.assertEqual(items[2].url, "https://www.bilibili.com/video/BV1xx")

    def test_queue_retry_and_skip_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = QueueStore(Path(tmp) / "queue.sqlite")
            item = store.enqueue("https://example.com/a")
            store.mark_failed(item.id, "network error")

            self.assertEqual(store.retry_failed(limit=10), 1)
            retried = store.get(item.id)
            self.assertEqual(retried.status, "pending")
            self.assertIsNone(retried.error)

            store.mark_skipped(item.id, "not useful")
            skipped = store.get(item.id)
            self.assertEqual(skipped.status, "skipped")
            self.assertEqual(skipped.error, "not useful")
            self.assertEqual(store.count_by_status()["skipped"], 1)

    def test_knowledge_maintenance_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vault = root / "vault"
            target = vault / "AI学习"
            target.mkdir(parents=True)
            (target / "Note A.md").write_text(
                "---\nurl: https://example.com/a\nstatus: inbox\n---\n# Note A\nThis mentions Note B.\n",
                encoding="utf-8",
            )
            (target / "Note B.md").write_text(
                "---\nurl: https://example.com/a\nstatus: inbox\n---\n# Note B\n",
                encoding="utf-8",
            )
            config = root / "config.toml"
            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)

            result = build_knowledge_maintenance(load_config(config), write=True)

            self.assertGreaterEqual(result.total_notes, 2)
            self.assertTrue((vault / "Obsidian Ingest Pipeline" / "入库总览.md").exists())
            self.assertTrue((vault / "Obsidian Ingest Pipeline" / "重复内容检查.md").exists())
            self.assertTrue((vault / "Obsidian Ingest Pipeline" / "双链建议.md").exists())

    def test_full_completion_cli_commands_return_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            vault = root / "vault"
            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)

            metadata = root / "playlist.json"
            metadata.write_text(
                json.dumps({"entries": [{"title": "Video A", "webpage_url": "https://youtu.be/a"}]}),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(
                    [
                        "collect-list",
                        "https://www.youtube.com/playlist?list=abc",
                        "--metadata-file",
                        str(metadata),
                        "--json",
                        "--config",
                        str(config),
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["queued"], 1)

            store = QueueStore(root / "data" / "queue.sqlite")
            item = store.list_pending()[0]
            store.mark_failed(item.id, "boom")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["retry-failed", "--json", "--config", str(config)]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["retried"], 1)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["skip", str(item.id), "--reason", "manual", "--json", "--config", str(config)]), 0)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "skipped")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["knowledge-maintenance", "--write", "--json", "--config", str(config)]), 0)
            self.assertIn("入库总览.md", "\n".join(json.loads(stdout.getvalue())["files"]))

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["write-launcher", "--json", "--config", str(config)]), 0)
            self.assertTrue(Path(json.loads(stdout.getvalue())["launcher"]).exists())


if __name__ == "__main__":
    unittest.main()
