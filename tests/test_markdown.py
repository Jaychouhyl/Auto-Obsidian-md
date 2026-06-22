import unittest

from obsidian_ingest.markdown import NotePayload, render_markdown_note
from obsidian_ingest.queue_store import QueueItem


class MarkdownRenderingTest(unittest.TestCase):
    def test_renders_frontmatter_sections_and_source_link(self):
        item = QueueItem(
            id=1,
            url="https://www.youtube.com/watch?v=abc",
            title="How to Learn",
            platform="youtube",
            content_type="video",
            status="pending",
            created_at="2026-06-03T10:00:00",
            updated_at="2026-06-03T10:00:00",
            metadata={},
            note_path=None,
            error=None,
        )
        payload = NotePayload(
            summary="This video explains deliberate practice.",
            key_points=["Practice with feedback", "Review weak spots"],
            action_items=["Create a weekly review checklist"],
            transcript="00:00 Start\n00:30 Main idea",
            routed_folder="AI学习",
        )

        rendered = render_markdown_note(item, payload)

        self.assertIn("source: youtube", rendered)
        self.assertIn('folder: "AI学习"', rendered)
        self.assertIn("url: https://www.youtube.com/watch?v=abc", rendered)
        self.assertIn("# How to Learn", rendered)
        self.assertIn("## 核心知识点", rendered)
        self.assertIn("- Practice with feedback", rendered)
        self.assertIn("## 原始转写", rendered)

    def test_topic_tags_render_into_frontmatter(self):
        item = QueueItem(
            id=2,
            url="https://example.com/x",
            title="量化笔记",
            platform="web",
            content_type="article",
            status="pending",
            created_at="2026-06-03T10:00:00",
            updated_at="2026-06-03T10:00:00",
            metadata={},
            note_path=None,
            error=None,
        )
        payload = NotePayload(summary="摘要", tags=["量化", "止损", "量化"])

        rendered = render_markdown_note(item, payload)

        self.assertIn("  - auto-ingest", rendered)
        self.assertIn("  - 量化", rendered)
        self.assertIn("  - 止损", rendered)
        # 去重：量化 只应出现一次
        self.assertEqual(rendered.count("  - 量化"), 1)

    def test_empty_tags_still_render_provenance_tag(self):
        item = QueueItem(
            id=3,
            url="https://example.com/y",
            title="无标签",
            platform="web",
            content_type="article",
            status="pending",
            created_at="2026-06-03T10:00:00",
            updated_at="2026-06-03T10:00:00",
            metadata={},
            note_path=None,
            error=None,
        )

        rendered = render_markdown_note(item, NotePayload(summary="x"))

        self.assertIn("  - auto-ingest", rendered)


if __name__ == "__main__":
    unittest.main()
