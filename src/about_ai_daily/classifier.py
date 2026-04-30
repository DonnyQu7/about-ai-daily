from __future__ import annotations

import math
import re

from .models import KnowledgeItem


CATEGORIES: dict[str, list[str]] = {
    "QA 自动化 / 测试 Agent": [
        "qa",
        "quality assurance",
        "test agent",
        "testing agent",
        "test automation",
        "automated testing",
        "bug reproduction",
        "bug reproduce",
        "defect",
        "regression",
        "flaky",
    ],
    "E2E / 浏览器自动化测试": [
        "e2e",
        "end-to-end",
        "playwright",
        "selenium",
        "cypress",
        "browser automation",
        "web testing",
        "ui testing",
        "headless browser",
        "puppeteer",
    ],
    "API / 接口测试与 Mock": [
        "api testing",
        "api test",
        "mock",
        "contract test",
        "contract testing",
        "postman",
        "openapi",
        "grpc",
        "load test",
        "performance test",
    ],
    "自动化执行流 / CI 编排": [
        "workflow",
        "workflows",
        "orchestration",
        "pipeline",
        "ci",
        "cd",
        "github actions",
        "executor",
        "runner",
        "scheduler",
        "automation",
        "mcp",
    ],
    "测试数据 / 环境 / DevOps": [
        "test data",
        "fixture",
        "environment",
        "sandbox",
        "docker",
        "kubernetes",
        "preview environment",
        "staging",
        "seed data",
    ],
    "代码质量 / Review / 静态分析": [
        "code review",
        "static analysis",
        "lint",
        "coverage",
        "quality gate",
        "sonarqube",
        "bug detection",
        "debug",
        "debugging",
    ],
    "测试用例生成 / LLM 辅助测试": [
        "test generation",
        "generate tests",
        "unit test",
        "unit tests",
        "llm",
        "ai",
        "agentic",
        "claude",
        "codex",
        "copilot",
    ],
    "工程可观测性 / 质量信号": [
        "observability",
        "monitoring",
        "trace",
        "tracing",
        "metrics",
        "log",
        "logs",
        "incident",
        "slo",
    ],
    "开发者效率自动化": [
        "developer tool",
        "devtool",
        "ide",
        "cli",
        "sdk",
        "code agent",
        "coding agent",
        "repo",
        "repository",
    ],
}

QA_ENGINEERING_KEYWORDS = [
    "qa",
    "quality assurance",
    "test",
    "tests",
    "testing",
    "tester",
    "automation",
    "workflow",
    "workflows",
    "pipeline",
    "ci",
    "cd",
    "runner",
    "executor",
    "orchestration",
    "playwright",
    "selenium",
    "cypress",
    "puppeteer",
    "e2e",
    "end-to-end",
    "browser automation",
    "api testing",
    "mock",
    "coverage",
    "code review",
    "static analysis",
    "debug",
    "debugging",
    "bug",
    "defect",
    "regression",
    "flaky",
    "observability",
    "monitoring",
]

AI_OR_AGENT_KEYWORDS = [
    "ai",
    "llm",
    "agent",
    "agents",
    "agentic",
    "mcp",
    "claude",
    "codex",
    "copilot",
    "openai",
    "gemini",
]

IMPLEMENTATION_KEYWORDS = [
    "open source",
    "framework",
    "sdk",
    "cli",
    "api",
    "dashboard",
    "self-hosted",
    "docker",
    "github actions",
    "plugin",
    "integration",
    "deploy",
    "deployment",
]

BUSINESS_OR_CONTENT_NEGATIVES = [
    "sales",
    "marketing",
    "crm",
    "lead generation",
    "customer support",
    "newsletter",
    "social media",
    "content creator",
    "video production",
    "film",
    "image generation",
    "healthcare",
    "medical",
    "legal",
    "finance",
    "trading",
    "real estate",
    "ecommerce",
]

FALSE_POSITIVE_NEGATIVES = [
    "user-agent",
    "ai crawler",
    "ai crawlers",
    "crawler detection",
]

OFF_TARGET_ENGINEERING_NEGATIVES = [
    "genshin",
    "game",
    "gaming",
    "red team",
    "redteam",
    "bug bounty",
    "reconnaissance",
    "recon",
    "penetration tester",
    "penetration testers",
    "ctf",
]

SOFTWARE_DELIVERY_CONTEXT = [
    "software",
    "code",
    "coding",
    "developer",
    "devtool",
    "ide",
    "repo",
    "repository",
    "pull request",
    "pr",
    "github",
    "gitlab",
    "api",
    "sdk",
    "cli",
    "ci",
    "cd",
    "pipeline",
    "playwright",
    "selenium",
    "cypress",
    "unit test",
    "e2e",
    "qa",
    "test automation",
]


def classify_items(items: list[KnowledgeItem], min_score: float = 4.5) -> list[KnowledgeItem]:
    classified: list[KnowledgeItem] = []
    for item in items:
        classify_item(item)
        if item.score >= min_score:
            classified.append(item)
    return sorted(classified, key=lambda x: x.score, reverse=True)


def classify_item(item: KnowledgeItem) -> KnowledgeItem:
    blob = f"{item.title}\n{item.summary}".casefold()
    reasons: list[str] = []

    engineering_hits = keyword_hits(blob, QA_ENGINEERING_KEYWORDS)
    ai_hits = keyword_hits(blob, AI_OR_AGENT_KEYWORDS)
    implementation_hits = keyword_hits(blob, IMPLEMENTATION_KEYWORDS)
    business_hits = keyword_hits(blob, BUSINESS_OR_CONTENT_NEGATIVES)
    false_positive_hits = keyword_hits(blob, FALSE_POSITIVE_NEGATIVES)
    off_target_hits = keyword_hits(blob, OFF_TARGET_ENGINEERING_NEGATIVES)
    software_context_hits = keyword_hits(blob, SOFTWARE_DELIVERY_CONTEXT)

    score = 0.0
    if engineering_hits:
        score += 2.2 + min(len(engineering_hits), 6) * 0.4
        reasons.append(f"测试/工程自动化关键词：{', '.join(engineering_hits[:6])}")
    else:
        score -= 2.5
        reasons.append("缺少软件测试或工程自动化语境")

    if ai_hits:
        score += 0.8 + min(len(ai_hits), 4) * 0.25
        reasons.append(f"AI/Agent 关键词：{', '.join(ai_hits[:5])}")

    if implementation_hits:
        score += 0.8 + min(len(implementation_hits), 4) * 0.25
        reasons.append(f"可落地工程信号：{', '.join(implementation_hits[:5])}")

    if software_context_hits:
        score += min(len(software_context_hits), 4) * 0.2
        reasons.append(f"软件交付语境：{', '.join(software_context_hits[:5])}")
    else:
        score -= 1.5
        reasons.append("缺少软件交付/测试工程语境")

    if business_hits and len(engineering_hits) < 2:
        score -= 4.0
        reasons.append(f"商业/非工程语境降权：{', '.join(business_hits[:4])}")
    elif business_hits:
        score -= 1.0
        reasons.append(f"含弱相关业务语境：{', '.join(business_hits[:4])}")

    if false_positive_hits:
        score -= 5.0
        reasons.append(f"非目标项目降权：{', '.join(false_positive_hits[:3])}")

    if off_target_hits:
        score -= 4.5
        reasons.append(f"偏离软件测试行业降权：{', '.join(off_target_hits[:4])}")

    source_score = source_signal_score(item)
    if source_score:
        score += source_score
        reasons.append(f"GitHub 热度加分：{source_score:.1f}")

    category, category_hits = choose_category(blob)
    item.category = category
    if category_hits:
        score += min(len(category_hits), 4) * 0.25
        reasons.append(f"分类命中：{', '.join(category_hits[:5])}")

    if item.source_type == "github":
        score += 0.4

    item.tags = sorted(set(item.tags + engineering_hits[:4] + ai_hits[:3] + implementation_hits[:3]))
    item.score = round(score, 3)
    item.reason = reasons or ["相关性较弱，保留为候选"]
    return item


def keyword_hits(blob: str, keywords: list[str]) -> list[str]:
    hits: list[str] = []
    for keyword in keywords:
        if keyword_matches(blob, keyword):
            hits.append(keyword)
    return hits


def keyword_matches(blob: str, keyword: str) -> bool:
    normalized = keyword.casefold()
    if " " in normalized or "-" in normalized:
        return normalized in blob
    if re.fullmatch(r"[a-z0-9]+", normalized):
        return re.search(rf"(?<![a-z0-9]){re.escape(normalized)}(?![a-z0-9])", blob) is not None
    return normalized in blob


def choose_category(blob: str) -> tuple[str, list[str]]:
    best_category = "开发者效率自动化"
    best_hits: list[str] = []
    for category, keywords in CATEGORIES.items():
        hits = keyword_hits(blob, keywords)
        if len(hits) > len(best_hits):
            best_category = category
            best_hits = hits
    return best_category, best_hits


def source_signal_score(item: KnowledgeItem) -> float:
    if item.source_type == "github":
        stars = int(item.metrics.get("stars") or 0)
        forks = int(item.metrics.get("forks") or 0)
        open_issues = int(item.metrics.get("open_issues") or 0)
        issue_signal = math.log10(open_issues + 1) * 0.1 if open_issues else 0.0
        return min(2.5, math.log10(stars + 1) * 0.55 + math.log10(forks + 1) * 0.2 + issue_signal)

    if item.source_type == "hacker_news":
        score = int(item.metrics.get("hn_score") or 0)
        comments = int(item.metrics.get("comments") or 0)
        return min(1.8, math.log10(score + 1) * 0.7 + math.log10(comments + 1) * 0.25)

    if item.source_type == "rss":
        return float(item.metrics.get("source_weight") or 1.0) * 0.3

    return 0.0
