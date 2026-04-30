from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "report": {
        "title": "AI 应用落地知识日报",
        "language": "zh-CN",
        "min_score": 2.5,
        "max_items": 50,
    },
    "github": {
        "enabled": True,
        "per_query": 15,
        "min_stars": 20,
        "queries": [
            "AI agent workflow automation",
            "RAG knowledge base enterprise",
            "AI coding assistant developer tool",
        ],
    },
    "hacker_news": {
        "enabled": True,
        "top_stories": 100,
        "min_score": 5,
        "keywords": ["ai", "llm", "agent", "rag", "openai", "anthropic"],
    },
    "rss": {"enabled": True, "feeds": []},
    "x": {"enabled": False},
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with config_path.open("r", encoding="utf-8") as f:
        user_config = json.load(f)

    return deep_merge(DEFAULT_CONFIG, user_config)

