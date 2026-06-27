from __future__ import annotations

import unittest

from obsidian_ingest.pipeline import build_summary_input
from obsidian_ingest.queue_store import QueueItem
from obsidian_ingest.transcribe import TranscriptionResult


class PipelineSummaryInputTest(unittest.TestCase):
    def test_summary_input_includes_title_and_transcript(self) -> None:
        item = QueueItem(
            id=1,
            url="D:/cache/video.mp4",
            title="英语如何开口说？跟着外语节目主持人偷偷学",
            platform="local_file",
            content_type="video",
            status="pending",
            created_at="2026-06-27T00:00:00+00:00",
            updated_at="2026-06-27T00:00:00+00:00",
            metadata={},
            note_path=None,
            error=None,
        )
        transcription = TranscriptionResult("Thanks for watching", "whisper", [])

        text = build_summary_input(item, transcription)

        self.assertIn("标题：英语如何开口说？跟着外语节目主持人偷偷学", text)
        self.assertIn("转写/正文：", text)
        self.assertIn("Thanks for watching", text)


if __name__ == "__main__":
    unittest.main()
