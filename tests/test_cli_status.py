from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.cli import main


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


if __name__ == "__main__":
    unittest.main()
