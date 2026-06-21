import tempfile
import unittest
from pathlib import Path

from obsidian_ingest.queue_store import QueueStore


class QueueStoreTest(unittest.TestCase):
    def test_enqueue_deduplicates_by_url_and_preserves_first_title(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = QueueStore(Path(tmp) / "queue.sqlite")

            first = store.enqueue("https://example.com/a", title="First title")
            second = store.enqueue("https://example.com/a", title="Second title")

            self.assertEqual(first.id, second.id)
            pending = store.list_pending(limit=10)
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].title, "First title")
            self.assertEqual(pending[0].status, "pending")

    def test_enqueue_normalizes_tracking_query_for_dedupe(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = QueueStore(Path(tmp) / "queue.sqlite")

            first = store.enqueue("https://Example.com/a/?b=2&utm_source=x", title="First")
            second = store.enqueue("https://example.com/a?utm_medium=y&b=2", title="Second")

            self.assertEqual(first.id, second.id)
            self.assertEqual(store.list_pending(limit=10)[0].url, "https://example.com/a?b=2")

    def test_status_updates_are_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = QueueStore(Path(tmp) / "queue.sqlite")
            item = store.enqueue("https://example.com/a")

            store.mark_done(item.id, note_path="Inbox/example.md")
            fetched = store.get(item.id)

            self.assertEqual(fetched.status, "done")
            self.assertEqual(fetched.note_path, "Inbox/example.md")

    def test_list_recent_can_filter_by_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = QueueStore(Path(tmp) / "queue.sqlite")
            done = store.enqueue("https://example.com/done")
            failed = store.enqueue("https://example.com/failed")
            store.enqueue("https://example.com/pending")

            store.mark_done(done.id, note_path="Inbox/done.md")
            store.mark_failed(failed.id, error="download failed")

            try:
                items = store.list_recent(limit=10, status="failed")
            except TypeError as exc:
                self.fail(str(exc))

            self.assertEqual([item.id for item in items], [failed.id])
            self.assertEqual(items[0].error, "download failed")


if __name__ == "__main__":
    unittest.main()
