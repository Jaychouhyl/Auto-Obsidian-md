import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from obsidian_ingest.obsidian_writer import LocalVaultWriter, ObsidianRestWriter, make_safe_filename


class ObsidianWriterTest(unittest.TestCase):
    def test_sanitizes_windows_unsafe_filename_characters(self):
        self.assertEqual(
            make_safe_filename("A:B/C*D?E\"F<G>H|I"),
            "A-B-C-D-E-F-G-H-I",
        )

    def test_local_vault_writer_creates_markdown_inside_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = LocalVaultWriter(Path(tmp), folder="Inbox/Video Notes")

            result = writer.write_note("A/B test", "# Note")

            self.assertEqual(result.relative_path, "Inbox/Video Notes/A-B test.md")
            written = Path(tmp) / result.relative_path
            self.assertTrue(written.exists())
            self.assertEqual(written.read_text(encoding="utf-8"), "# Note")

    def test_local_vault_writer_accepts_per_note_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            writer = LocalVaultWriter(Path(tmp), folder="Inbox/Video Notes")

            result = writer.write_note("Routing test", "# Note", folder="考研资料汇总")

            self.assertEqual(result.relative_path, "考研资料汇总/Routing test.md")
            self.assertTrue((Path(tmp) / result.relative_path).exists())

    def test_rest_writer_uses_local_rest_api_put_request(self):
        requests = []

        def fake_urlopen(request, timeout=0):
            requests.append(request)

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc, tb):
                    return False

                def read(self):
                    return b"{}"

            return Response()

        writer = ObsidianRestWriter("http://127.0.0.1:27123", "secret", folder="Inbox")
        with patch("urllib.request.urlopen", fake_urlopen):
            result = writer.write_note("Title", "# Body", folder="AI学习")

        self.assertEqual(result.relative_path, "AI学习/Title.md")
        self.assertEqual(requests[0].method, "PUT")
        self.assertIn("/vault/AI%E5%AD%A6%E4%B9%A0/Title.md", requests[0].full_url)
        self.assertEqual(requests[0].headers["Authorization"], "Bearer secret")
        self.assertEqual(requests[0].headers["Content-type"], "text/markdown")
        self.assertEqual(requests[0].data.decode("utf-8"), "# Body")


if __name__ == "__main__":
    unittest.main()
