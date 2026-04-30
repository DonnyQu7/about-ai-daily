from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class KnowledgeItem:
    source_type: str
    source_name: str
    title: str
    url: str
    summary: str = ""
    published_at: str | None = None
    collected_at: str = field(default_factory=utc_now_iso)
    score: float = 0.0
    category: str = "未分类"
    tags: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    reason: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "source_name": self.source_name,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "published_at": self.published_at,
            "collected_at": self.collected_at,
            "score": round(self.score, 2),
            "category": self.category,
            "tags": self.tags,
            "metrics": self.metrics,
            "reason": self.reason,
        }


@dataclass
class CollectionResult:
    items: list[KnowledgeItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def extend(self, other: "CollectionResult") -> None:
        self.items.extend(other.items)
        self.errors.extend(other.errors)


@dataclass
class ReportSection:
    key: str
    title: str
    hours: int
    items: list[KnowledgeItem] = field(default_factory=list)
    raw_count: int = 0
