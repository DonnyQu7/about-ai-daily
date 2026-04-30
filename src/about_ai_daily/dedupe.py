from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import KnowledgeItem
from .text import normalize_key


TRACKING_PREFIXES = ("utm_",)
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "ref"}


def dedupe_items(items: list[KnowledgeItem]) -> list[KnowledgeItem]:
    seen: dict[str, KnowledgeItem] = {}

    for item in items:
        key = item_key(item)
        if key not in seen:
            seen[key] = item
            continue

        current = seen[key]
        if item_quality(item) > item_quality(current):
            merged = item
            merged.tags = sorted(set(current.tags + item.tags))
            merged.reason = sorted(set(current.reason + item.reason))
            seen[key] = merged

    return list(seen.values())


def item_key(item: KnowledgeItem) -> str:
    if item.url:
        return f"url:{normalize_url(item.url)}"
    return f"title:{normalize_key(item.title)}"


def normalize_url(url: str) -> str:
    parsed = urlsplit(url.strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key not in TRACKING_PARAMS and not key.startswith(TRACKING_PREFIXES)
    ]
    normalized_query = urlencode(query)
    path = parsed.path.rstrip("/") or parsed.path
    return urlunsplit((parsed.scheme.casefold(), parsed.netloc.casefold(), path, normalized_query, ""))


def item_quality(item: KnowledgeItem) -> float:
    if item.source_type == "github":
        return float(item.metrics.get("stars") or 0)
    if item.source_type == "hacker_news":
        return float(item.metrics.get("hn_score") or 0)
    return float(len(item.summary or ""))

