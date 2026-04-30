import unittest

from about_ai_daily.classifier import classify_item
from about_ai_daily.models import KnowledgeItem


class ClassifierTest(unittest.TestCase):
    def test_classifies_qa_automation_item(self):
        item = KnowledgeItem(
            source_type="github",
            source_name="GitHub",
            title="example/qa-agent-runner",
            url="https://github.com/example/qa-agent-runner",
            summary="Open source AI testing agent for Playwright E2E test automation and CI workflow orchestration.",
            metrics={"stars": 100, "forks": 12},
        )

        classify_item(item)

        self.assertIn(
            item.category,
            {"QA 自动化 / 测试 Agent", "E2E / 浏览器自动化测试", "自动化执行流 / CI 编排"},
        )
        self.assertGreaterEqual(item.score, 4.5)

    def test_downranks_user_agent_detection_false_positive(self):
        item = KnowledgeItem(
            source_type="github",
            source_name="GitHub",
            title="example/user-agent-parser",
            url="https://github.com/example/user-agent-parser",
            summary="Detect browsers, devices, bots, apps, AI crawlers, and user-agent strings.",
            metrics={"stars": 10000, "forks": 1000},
        )

        classify_item(item)

        self.assertLess(item.score, 4.5)

    def test_downranks_business_only_item(self):
        item = KnowledgeItem(
            source_type="github",
            source_name="GitHub",
            title="example/ai-sales-crm-agent",
            url="https://github.com/example/ai-sales-crm-agent",
            summary="AI sales and CRM automation tool for marketing lead generation.",
            metrics={"stars": 5000, "forks": 400},
        )

        classify_item(item)

        self.assertLess(item.score, 4.5)

    def test_downranks_game_automation_false_positive(self):
        item = KnowledgeItem(
            source_type="github",
            source_name="GitHub",
            title="example/game-ui-automation",
            url="https://github.com/example/game-ui-automation",
            summary="UI Automation Testing Tools for Genshin Impact game automation.",
            metrics={"stars": 20000, "forks": 1000},
        )

        classify_item(item)

        self.assertLess(item.score, 4.5)


if __name__ == "__main__":
    unittest.main()
