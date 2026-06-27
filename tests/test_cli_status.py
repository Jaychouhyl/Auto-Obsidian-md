from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.cli import main
from obsidian_ingest.queue_store import QueueStore


class CliStatusTest(unittest.TestCase):
    def test_status_json_reports_queue_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            vault = root / "vault"

            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)
            self.assertEqual(main(["add", "https://example.com/a", "--title", "A", "--config", str(config)]), 0)
            self.assertEqual(main(["add", "https://example.com/b", "--title", "B", "--config", str(config)]), 0)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["status", "--json", "--config", str(config)])

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["queue"]["pending"], 2)
            self.assertEqual(payload["queue"]["done"], 0)
            self.assertEqual(payload["queue"]["failed"], 0)
            self.assertTrue(payload["paths"]["queue_db"].endswith("queue.sqlite"))
            self.assertEqual(payload["obsidian"]["mode"], "local")
            self.assertIn("rest_base_url", payload["obsidian"])
            self.assertEqual(payload["llm"]["language"], "zh-CN")
            self.assertEqual(payload["outputs"]["formats"], ["markdown"])
            self.assertTrue(payload["outputs"]["html_dir"].replace("\\", "/").endswith("exports/html"))
            self.assertFalse(payload["outputs"]["notion_configured"])

    def test_queue_json_lists_recent_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            vault = root / "vault"

            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)
            self.assertEqual(main(["add", "D:/Downloads/example.pdf", "--title", "Example PDF", "--config", str(config)]), 0)

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["queue", "--json", "--limit", "5", "--config", str(config)])

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["items"][0]["title"], "Example PDF")
            self.assertEqual(payload["items"][0]["platform"], "local_file")
            self.assertEqual(payload["items"][0]["status"], "pending")

    def test_queue_json_can_filter_by_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            vault = root / "vault"

            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)
            self.assertEqual(main(["add", "https://example.com/pending", "--config", str(config)]), 0)
            self.assertEqual(main(["add", "https://example.com/failed", "--config", str(config)]), 0)

            store = QueueStore(root / "data" / "queue.sqlite")
            failed = next(item for item in store.list_recent(limit=10) if item.url.endswith("/failed"))
            store.mark_failed(failed.id, "download failed")

            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                try:
                    code = main(["queue", "--json", "--status", "failed", "--config", str(config)])
                except SystemExit as exc:
                    code = int(exc.code)

            self.assertEqual(code, 0, stderr.getvalue())
            payload = json.loads(stdout.getvalue())
            self.assertEqual(len(payload["items"]), 1)
            self.assertEqual(payload["items"][0]["status"], "failed")
            self.assertEqual(payload["items"][0]["error"], "download failed")


if __name__ == "__main__":
    unittest.main()
