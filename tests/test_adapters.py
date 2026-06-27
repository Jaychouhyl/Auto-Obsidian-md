import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from obsidian_ingest.acquire import AcquisitionRequest, build_acquisition_command, acquire_source
from obsidian_ingest.summarize import build_openai_compatible_payload, fallback_summary
from obsidian_ingest.transcribe import build_transcription_command, transcribe_source


class AdapterTest(unittest.TestCase):
    def test_builds_yt_dlp_command_for_youtube(self):
        request = AcquisitionRequest(url="https://youtu.be/abc", platform="youtube", output_dir=Path("cache"))

        command = build_acquisition_command(request, yt_dlp_cmd="yt-dlp", douyin_cmd="douyin-downloader")

        self.assertEqual(command[0], "yt-dlp")
        self.assertIn("--write-auto-subs", command)
        self.assertIn("https://youtu.be/abc", command)

    def test_builds_douyin_downloader_command_for_douyin(self):
        request = AcquisitionRequest(url="https://v.douyin.com/abc/", platform="douyin", output_dir=Path("cache"))

        command = build_acquisition_command(request, yt_dlp_cmd="yt-dlp", douyin_cmd="douyin-dl")

        self.assertEqual(command[0], "douyin-dl")
        self.assertIn("-u", command)
        self.assertIn("-p", command)
        self.assertIn("https://v.douyin.com/abc/", command)

    def test_builds_douyin_command_with_config_file(self):
        request = AcquisitionRequest(url="https://v.douyin.com/abc/", platform="douyin", output_dir=Path("cache"))

        command = build_acquisition_command(
            request,
            yt_dlp_cmd="yt-dlp",
            douyin_cmd="douyin-dl",
            douyin_config="C:/tmp/auto-obsidian-md/douyin-config.yml",
        )

        self.assertIn("-c", command)
        self.assertIn("C:/tmp/auto-obsidian-md/douyin-config.yml", command)

    def test_acquire_source_falls_back_when_command_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = acquire_source(
                AcquisitionRequest(url="https://example.com/a", platform="web", output_dir=Path(tmp)),
                yt_dlp_cmd="obsidian-ingest-missing-tool",
                dry_run_missing_tools=True,
            )

            self.assertEqual(result.status, "metadata_only")
            self.assertIn("https://example.com/a", result.transcript_hint)

    def test_acquire_source_reads_local_text_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            transcript = Path(tmp) / "bilibili-export.srt"
            transcript.write_text("00:00 学习目标\n00:12 第一条知识点", encoding="utf-8")

            result = acquire_source(
                AcquisitionRequest(url=str(transcript), platform="local_file", output_dir=Path(tmp)),
                dry_run_missing_tools=True,
            )

            self.assertEqual(result.status, "local_text")
            self.assertIsNone(result.media_path)
            self.assertIn("第一条知识点", result.transcript_hint)
            self.assertNotIn("00:00", result.transcript_hint)

    def test_builds_whisper_command(self):
        command = build_transcription_command(Path("audio.mp3"), engine="whisper", whisper_cmd="whisper")

        self.assertEqual(command[0], "whisper")
        self.assertIn("audio.mp3", command)
        self.assertIn("tiny", command)
        self.assertIn("--output_format", command)
        self.assertIn("False", command)
        self.assertIn("--verbose", command)
        self.assertNotIn("--language", command)

    def test_transcribe_source_uses_hint_when_no_media(self):
        result = transcribe_source(media_path=None, transcript_hint="raw source text")

        self.assertEqual(result.text, "raw source text")
        self.assertEqual(result.engine, "hint")

    def test_builds_openai_compatible_payload(self):
        payload = build_openai_compatible_payload("model-a", "transcript text", "zh-CN")

        self.assertEqual(payload["model"], "model-a")
        self.assertIn("messages", payload)
        self.assertIn("transcript text", json.dumps(payload, ensure_ascii=False))

    def test_builds_deepseek_v4_payload_with_thinking_enabled(self):
        payload = build_openai_compatible_payload("deepseek-v4-pro", "transcript text", "zh-CN")

        self.assertEqual(payload["model"], "deepseek-v4-pro")
        self.assertEqual(payload["thinking"], {"type": "enabled"})
        self.assertEqual(payload["reasoning_effort"], "high")

    def test_builds_payload_with_allowed_folders(self):
        payload = build_openai_compatible_payload(
            "deepseek-v4-pro",
            "考研资料",
            "zh-CN",
            allowed_folders=["考研资料汇总", "Inbox/Learning Inbox"],
            fallback_folder="Inbox/Learning Inbox",
        )

        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertIn("folder", serialized)
        self.assertIn("考研资料汇总", serialized)
        self.assertIn("Inbox/Learning Inbox", serialized)

    def test_summarize_transcript_accepts_string_tags_from_llm(self):
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                content = {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "summary": "摘要",
                                        "key_points": ["要点"],
                                        "action_items": ["行动"],
                                        "tags": "#量化, 止损, 仓位 管理, 123",
                                        "folder": "炒股与量化学习",
                                    },
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                }
                return json.dumps(content, ensure_ascii=False).encode("utf-8")

        with patch("urllib.request.urlopen", return_value=FakeResponse()):
            from obsidian_ingest.summarize import summarize_transcript

            summary = summarize_transcript(
                "量化交易",
                enabled=True,
                api_key="test-key",
                base_url="https://api.example.com",
                allowed_folders=["炒股与量化学习", "Inbox/Learning Inbox"],
                fallback_folder="Inbox/Learning Inbox",
            )

        self.assertEqual(summary.tags, ["量化", "止损", "仓位-管理"])

    def test_fallback_summary_infers_kaoyan_folder(self):
        summary = fallback_summary(
            "二战考研离校前要处理档案、户口、复试材料。",
            allowed_folders=["AI学习", "考研资料汇总", "Inbox/Learning Inbox"],
            fallback_folder="Inbox/Learning Inbox",
        )

        self.assertEqual(summary.folder, "考研资料汇总")

    def test_fallback_summary_infers_quant_folder(self):
        summary = fallback_summary(
            "量化交易复盘要记录股票买点、止损线、仓位管理和回撤控制。",
            allowed_folders=["AI学习", "炒股与量化学习", "Inbox/Learning Inbox"],
            fallback_folder="Inbox/Learning Inbox",
        )

        self.assertEqual(summary.folder, "炒股与量化学习")

    def test_fallback_summary_infers_postgraduate_english_folder(self):
        summary = fallback_summary(
            "研后英语学习要继续背单词、练听力和复盘英文长难句。",
            allowed_folders=["AI学习", "研后/英语学习", "Inbox/Learning Inbox"],
            fallback_folder="Inbox/Learning Inbox",
        )

        self.assertEqual(summary.folder, "研后/英语学习")

    def test_fallback_summary_extracts_key_points(self):
        summary = fallback_summary("第一点很重要。\n第二点也重要。\n第三点是行动。")

        self.assertTrue(summary.summary)
        self.assertGreaterEqual(len(summary.key_points), 2)

    def test_fallback_summary_generates_topic_tags(self):
        summary = fallback_summary("量化交易需要设置止损，控制仓位，并记录复盘。")

        self.assertIn("量化交易", summary.tags)
        self.assertIn("止损", summary.tags)
        self.assertIn("仓位管理", summary.tags)


if __name__ == "__main__":
    unittest.main()
