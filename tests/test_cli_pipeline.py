import os
import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.cli import main


class CliPipelineTest(unittest.TestCase):
    def test_init_add_run_once_writes_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            vault = project / "vault"
            config = project / "config.toml"

            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)
            self.assertTrue(config.exists())

            self.assertEqual(
                main(["add", "https://example.com/article", "--config", str(config), "--title", "Example Article"]),
                0,
            )
            self.assertEqual(main(["run", "--config", str(config), "--once"]), 0)

            notes = list((vault / "Inbox" / "Learning Inbox").glob("*.md"))
            self.assertEqual(len(notes), 1)
            content = notes[0].read_text(encoding="utf-8")
            self.assertIn("Example Article", content)
            self.assertIn("https://example.com/article", content)

    def test_import_links_accepts_plain_text_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            vault = project / "vault"
            config = project / "config.toml"
            links = project / "links.txt"
            links.write_text("https://example.com/a\nhttps://youtu.be/abc\n", encoding="utf-8")

            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)
            self.assertEqual(main(["import-links", str(links), "--config", str(config)]), 0)
            self.assertEqual(main(["run", "--config", str(config), "--once", "--limit", "2"]), 0)

            notes = list((vault / "Inbox" / "Learning Inbox").glob("*.md"))
            self.assertEqual(len(notes), 2)

    def test_doctor_reports_missing_optional_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / "config.toml"
            vault = Path(tmp) / "vault"
            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)
            self.assertEqual(main(["doctor", "--config", str(config)]), 0)


if __name__ == "__main__":
    unittest.main()
