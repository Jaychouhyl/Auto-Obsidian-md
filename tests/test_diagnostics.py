from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from obsidian_ingest.cli import main
from obsidian_ingest.diagnostics import create_diagnostic_package
from obsidian_ingest.queue_store import QueueStore


class DiagnosticsTest(unittest.TestCase):
    def test_diagnostic_package_redacts_secrets_and_includes_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            config.write_text(
                "\n".join(
                    [
                        "[paths]",
                        f'queue_db = "{(root / "data" / "queue.sqlite").as_posix()}"',
                        f'cache_dir = "{(root / "cache").as_posix()}"',
                        "",
                        "[obsidian]",
                        'mode = "local"',
                        f'vault_path = "{(root / "vault").as_posix()}"',
                        'folder = "Inbox"',
                        'rest_base_url = "http://127.0.0.1:27123"',
                        'rest_api_key = "rest-secret"',
                        "",
                        "[tools]",
                        'yt_dlp = "yt-dlp"',
                        'ffmpeg = "ffmpeg"',
                        'douyin_downloader = "douyin-dl"',
                        'douyin_config = ""',
                        'whisper = "whisper"',
                        'funasr = "funasr"',
                        'ocr = "builtin"',
                        "",
                        "[llm]",
                        "enabled = true",
                        'provider = "openai-compatible"',
                        'base_url = "https://api.deepseek.com/v1"',
                        'api_key = "deepseek-secret"',
                        'model = "deepseek-chat"',
                        'language = "zh-CN"',
                        "",
                        "[routing]",
                        "enabled = true",
                        'fallback_folder = "Inbox"',
                        'allowed_folders = ["Inbox"]',
                    ]
                ),
                encoding="utf-8",
            )
            (root / "vault").mkdir()
            (root / "cache").mkdir()
            (root / "logs").mkdir()
            (root / "logs" / "run.log").write_text('api_key = should-hide\n{"token": "json-secret"}\nnormal line\n', encoding="utf-8")
            (root / "links.txt").write_text("https://example.com/a\nhttps://example.com/b\n", encoding="utf-8")
            store = QueueStore(root / "data" / "queue.sqlite")
            item = store.enqueue("https://example.com/fail", title="failed source")
            store.mark_failed(item.id, "ffmpeg missing")

            result = create_diagnostic_package(config)

            self.assertTrue(result.package_path.exists())
            with ZipFile(result.package_path) as archive:
                names = set(archive.namelist())
                self.assertIn("diagnostic-manifest.json", names)
                self.assertIn("status.json", names)
                self.assertIn("doctor.json", names)
                self.assertIn("queue-summary.json", names)
                self.assertIn("config.redacted.toml", names)
                self.assertIn("logs/run.log", names)
                config_text = archive.read("config.redacted.toml").decode("utf-8")
                log_text = archive.read("logs/run.log").decode("utf-8")
                queue = json.loads(archive.read("queue-summary.json").decode("utf-8"))

            self.assertNotIn("deepseek-secret", config_text)
            self.assertNotIn("rest-secret", config_text)
            self.assertNotIn("should-hide", log_text)
            self.assertNotIn("json-secret", log_text)
            self.assertEqual(queue["counts"]["failed"], 1)
            self.assertEqual(queue["recent_failed"][0]["error"], "ffmpeg missing")

    def test_cli_diagnostics_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.toml"
            config.write_text(
                f'[paths]\nqueue_db = "{(root / "data" / "queue.sqlite").as_posix()}"\ncache_dir = "{(root / "cache").as_posix()}"\n\n'
                f'[obsidian]\nmode = "local"\nvault_path = "{(root / "vault").as_posix()}"\nfolder = "Inbox"\nrest_base_url = ""\nrest_api_key = ""\n\n'
                '[tools]\nyt_dlp = "yt-dlp"\nffmpeg = "ffmpeg"\ndouyin_downloader = "douyin-dl"\ndouyin_config = ""\nwhisper = "whisper"\nfunasr = "funasr"\nocr = "builtin"\n\n'
                '[llm]\nenabled = false\nprovider = "openai-compatible"\nbase_url = ""\napi_key = ""\nmodel = "deepseek-chat"\nlanguage = "zh-CN"\n\n'
                '[routing]\nenabled = true\nfallback_folder = "Inbox"\nallowed_folders = ["Inbox"]\n',
                encoding="utf-8",
            )
            (root / "vault").mkdir()

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["diagnostics", "--json", "--config", str(config)])

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "done")
            self.assertTrue(Path(payload["package_path"]).exists())


if __name__ == "__main__":
    unittest.main()
