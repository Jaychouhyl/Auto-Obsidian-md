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


if __name__ == "__main__":
    unittest.main()
