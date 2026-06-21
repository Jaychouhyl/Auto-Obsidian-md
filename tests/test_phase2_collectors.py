from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.cli import main
from obsidian_ingest.collectors.directory import scan_directory_files
from obsidian_ingest.collectors.rss import parse_feed_items
from obsidian_ingest.collectors.webpage import extract_webpage_text


class Phase2CollectorsTest(unittest.TestCase):
    def test_scans_arbitrary_directory_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "nested"
            nested.mkdir()
            (root / "a.pdf").write_text("pdf", encoding="utf-8")
            (nested / "b.vtt").write_text("caption", encoding="utf-8")
            (root / "ignore.tmp").write_text("tmp", encoding="utf-8")

            files = scan_directory_files(root)

            self.assertEqual([path.name for path in files], ["a.pdf", "b.vtt"])

    def test_parses_rss_items(self) -> None:
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
          <channel>
            <title>Learning</title>
            <item>
              <title>Item A</title>
              <link>https://example.com/a?utm_source=rss</link>
            </item>
            <item>
              <title>Item B</title>
              <link>https://example.com/b</link>
            </item>
          </channel>
        </rss>
        """

        items = parse_feed_items(xml, source_url="https://example.com/feed.xml", limit=1)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Item A")
        self.assertEqual(items[0].url, "https://example.com/a?utm_source=rss")

    def test_extracts_readable_webpage_text(self) -> None:
        html = """
        <html><head><title>Example Page</title><script>bad()</script></head>
        <body><nav>menu</nav><article><h1>Hello</h1><p>Useful text.</p></article></body></html>
        """

        page = extract_webpage_text(html, source_url="https://example.com/a")

        self.assertEqual(page.title, "Example Page")
        self.assertIn("Hello", page.text)
        self.assertIn("Useful text.", page.text)
        self.assertNotIn("bad()", page.text)

    def test_phase2_cli_commands_return_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            vault = root / "vault"
            downloads = root / "downloads"
            downloads.mkdir()
            (downloads / "course.pdf").write_text("pdf", encoding="utf-8")

            feed = root / "feeds.txt"
            feed_xml = root / "feed.xml"
            feed_xml.write_text(
                "<rss><channel><item><title>Feed Item</title><link>https://example.com/feed-item</link></item></channel></rss>",
                encoding="utf-8",
            )
            feed.write_text(f"\ufeff{feed_xml}\n", encoding="utf-8")

            page = root / "page.html"
            page.write_text("<html><title>Saved Page</title><body><main>Saved body.</main></body></html>", encoding="utf-8")

            self.assertEqual(main(["init", "--config", str(config), "--vault", str(vault)]), 0)

            for argv in (
                ["scan-directory", "--dir", str(downloads), "--json", "--config", str(config)],
                ["collect-rss", "--feeds", str(feed), "--limit", "5", "--json", "--config", str(config)],
                ["clip-webpage", str(page), "--json", "--config", str(config)],
            ):
                stdout = io.StringIO()
                with contextlib.redirect_stdout(stdout):
                    code = main(argv)
                self.assertEqual(code, 0)
                payload = json.loads(stdout.getvalue())
                self.assertEqual(payload["status"], "done")
                self.assertGreaterEqual(payload["queued"], 1)


if __name__ == "__main__":
    unittest.main()
