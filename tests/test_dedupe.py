import unittest

from about_ai_daily.dedupe import dedupe_items
from about_ai_daily.models import KnowledgeItem


class DedupeTest(unittest.TestCase):
    def test_dedupe_removes_tracking_params(self):
        items = [
            KnowledgeItem(source_type="rss", source_name="A", title="A", url="https://example.com/a?utm_source=x"),
            KnowledgeItem(source_type="rss", source_name="B", title="A copy", url="https://example.com/a"),
        ]

        self.assertEqual(len(dedupe_items(items)), 1)


if __name__ == "__main__":
    unittest.main()
