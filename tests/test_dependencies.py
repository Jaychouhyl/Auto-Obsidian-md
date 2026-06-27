from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
import contextlib
from pathlib import Path
from unittest.mock import patch

from obsidian_ingest.cli import main
from obsidian_ingest.config import load_config, write_default_config
from obsidian_ingest.dependencies import dependency_report, install_managed_dependencies


class DependencyManagementTest(unittest.TestCase):
    def test_report_marks_installable_and_manual_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.toml"
            write_default_config(config_path, root / "vault")
            config = load_config(config_path)

            with patch("obsidian_ingest.dependencies._is_windows", return_value=True):
                report = dependency_report(
                    config,
                    command_resolver=lambda _command: None,
                    edge_finder=lambda: None,
                )

            by_id = {item["id"]: item for item in report["items"]}
            self.assertEqual(by_id["yt-dlp"]["status"], "missing")
            self.assertTrue(by_id["yt-dlp"]["installable"])
            self.assertEqual(by_id["ffmpeg"]["status"], "missing")
            self.assertTrue(by_id["ffmpeg"]["installable"])
            self.assertEqual(by_id["douyin-downloader"]["status"], "missing")
            self.assertFalse(by_id["douyin-downloader"]["installable"])
            self.assertEqual(by_id["edge"]["status"], "missing")
            self.assertFalse(by_id["edge"]["installable"])

    def test_install_managed_dependencies_dry_run_does_not_write_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.toml"
            write_default_config(config_path, root / "vault")

            before = config_path.read_text(encoding="utf-8")
            config = load_config(config_path)
            with patch("obsidian_ingest.dependencies._is_windows", return_value=True):
                result = install_managed_dependencies(config, tool_ids=["yt-dlp", "ffmpeg"], dry_run=True)

            self.assertEqual([item["id"] for item in result["planned"]], ["yt-dlp", "ffmpeg"])
            self.assertEqual(result["installed"], [])
            self.assertEqual(config_path.read_text(encoding="utf-8"), before)

    def test_install_managed_dependencies_downloads_and_updates_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.toml"
            write_default_config(config_path, root / "vault")
            config = load_config(config_path)

            def fake_download(url: str, target: Path) -> None:
                target.parent.mkdir(parents=True, exist_ok=True)
                if url.endswith(".zip"):
                    data = io.BytesIO()
                    with zipfile.ZipFile(data, "w") as archive:
                        archive.writestr("ffmpeg-build/bin/ffmpeg.exe", "ffmpeg")
                        archive.writestr("ffmpeg-build/bin/ffprobe.exe", "ffprobe")
                    target.write_bytes(data.getvalue())
                else:
                    target.write_text("yt-dlp", encoding="utf-8")

            with patch("obsidian_ingest.dependencies._is_windows", return_value=True):
                result = install_managed_dependencies(
                    config,
                    tool_ids=["yt-dlp", "ffmpeg"],
                    downloader=fake_download,
                )

            self.assertEqual([item["id"] for item in result["installed"]], ["yt-dlp", "ffmpeg"])
            updated = load_config(config_path)
            self.assertTrue(updated.tools.yt_dlp.endswith("tools/yt-dlp/yt-dlp.exe"))
            self.assertTrue(updated.tools.ffmpeg.endswith("tools/ffmpeg/bin/ffmpeg.exe"))
            self.assertTrue(Path(updated.tools.yt_dlp).is_file())
            self.assertTrue(Path(updated.tools.ffmpeg).is_file())

    def test_dependencies_report_cli_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "config.toml"
            write_default_config(config_path, root / "vault")

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["dependencies", "report", "--json", "--config", str(config_path)])

            self.assertEqual(code, 0)
            payload = json.loads(stdout.getvalue())
            self.assertEqual(payload["status"], "done")
            self.assertIn("items", payload)


if __name__ == "__main__":
    unittest.main()
