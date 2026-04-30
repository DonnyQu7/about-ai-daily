from __future__ import annotations

import concurrent.futures
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any

from .http import HttpError, get_json, get_text, github_headers
from .models import CollectionResult, KnowledgeItem
from .text import clean_text, parse_datetime, to_iso


def collect_all(config: dict[str, Any], hours: int) -> CollectionResult:
    result = CollectionResult()

    if config.get("github", {}).get("enabled", False):
        result.extend(collect_github(config.get("github", {}), hours))

    if config.get("rss", {}).get("enabled", False):
        result.extend(collect_rss(config.get("rss", {}), hours))

    if config.get("hacker_news", {}).get("enabled", False):
        result.extend(collect_hacker_news(config.get("hacker_news", {}), hours))

    if config.get("x", {}).get("enabled", False):
        result.errors.append("X/Twitter collector is not implemented in MVP.")

    return result


def collect_github(config: dict[str, Any], hours: int) -> CollectionResult:
    result = CollectionResult()
    since_date = (datetime.now(timezone.utc) - timedelta(hours=hours)).date().isoformat()
    per_query = int(config.get("per_query", 15))
    min_stars = int(config.get("min_stars", 20))
    queries = config.get("queries", [])
    expected_account = config.get("account")
    headers, auth_warning = github_headers(expected_account)
    if auth_warning:
        result.errors.append(auth_warning)

    for query in queries:
        github_query = f"{query} pushed:>={since_date} stars:>={min_stars}"
        encoded = urllib.parse.urlencode(
            {
                "q": github_query,
                "sort": "stars",
                "order": "desc",
                "per_page": str(per_query),
            }
        )
        url = f"https://api.github.com/search/repositories?{encoded}"
        try:
            payload = get_json(url, headers=headers, timeout=30)
        except HttpError as exc:
            if "rate limit exceeded" in str(exc).casefold():
                result.errors.append(
                    "GitHub API rate limit exceeded. Set GITHUB_TOKEN for stable daily runs."
                )
                break
            result.errors.append(f"GitHub query failed [{query}]: {exc}")
            continue

        for repo in payload.get("items", []):
            item = KnowledgeItem(
                source_type="github",
                source_name="GitHub",
                title=repo.get("full_name") or repo.get("name") or "",
                url=repo.get("html_url") or "",
                summary=clean_text(repo.get("description"), 500),
                published_at=repo.get("pushed_at") or repo.get("updated_at") or repo.get("created_at"),
                tags=[tag for tag in [repo.get("language"), "github"] if tag],
                metrics={
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "open_issues": repo.get("open_issues_count", 0),
                    "language": repo.get("language"),
                    "created_at": repo.get("created_at"),
                    "updated_at": repo.get("updated_at"),
                    "query": query,
                },
            )
            if item.title and item.url:
                result.items.append(item)

    return result


def collect_hacker_news(config: dict[str, Any], hours: int) -> CollectionResult:
    result = CollectionResult()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    top_n = int(config.get("top_stories", 100))
    min_score = int(config.get("min_score", 5))
    keywords = [str(k).casefold() for k in config.get("keywords", [])]

    try:
        story_ids = get_json("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=20)
    except HttpError as exc:
        result.errors.append(f"Hacker News topstories failed: {exc}")
        return result

    selected_ids = story_ids[:top_n]

    def fetch_story(story_id: int) -> KnowledgeItem | None:
        try:
            story = get_json(
                f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                timeout=15,
            )
        except HttpError:
            return None

        if not story or story.get("type") != "story":
            return None

        title = clean_text(story.get("title"))
        if not title:
            return None

        published = datetime.fromtimestamp(int(story.get("time", 0)), timezone.utc)
        if published < cutoff:
            return None

        score = int(story.get("score") or 0)
        if score < min_score:
            return None

        title_blob = title.casefold()
        if keywords and not any(keyword in title_blob for keyword in keywords):
            return None

        url = story.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
        return KnowledgeItem(
            source_type="hacker_news",
            source_name="Hacker News",
            title=title,
            url=url,
            summary=f"HN discussion: https://news.ycombinator.com/item?id={story_id}",
            published_at=to_iso(published),
            tags=["hacker-news"],
            metrics={
                "hn_score": score,
                "comments": int(story.get("descendants") or 0),
                "hn_id": story_id,
            },
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        for item in executor.map(fetch_story, selected_ids):
            if item:
                result.items.append(item)

    return result


def collect_rss(config: dict[str, Any], hours: int) -> CollectionResult:
    result = CollectionResult()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    for feed in config.get("feeds", []):
        name = feed.get("name") or feed.get("url")
        url = feed.get("url")
        weight = float(feed.get("weight") or 1.0)
        if not url:
            continue

        try:
            xml_text = get_text(url, headers={"Accept": "application/rss+xml, application/atom+xml, text/xml"}, timeout=30)
            result.items.extend(parse_feed(xml_text, name, url, weight, cutoff))
        except (HttpError, ET.ParseError) as exc:
            result.errors.append(f"RSS feed failed [{name}]: {exc}")

    return result


def parse_feed(
    xml_text: str,
    source_name: str,
    source_url: str,
    source_weight: float,
    cutoff: datetime,
) -> list[KnowledgeItem]:
    root = ET.fromstring(xml_text)
    root_tag = strip_namespace(root.tag).casefold()
    if root_tag == "rss":
        entries = root.findall("./channel/item")
        return [item for entry in entries if (item := parse_rss_item(entry, source_name, source_weight, cutoff))]

    if root_tag == "feed":
        entries = root.findall("./{*}entry")
        return [item for entry in entries if (item := parse_atom_entry(entry, source_name, source_weight, cutoff))]

    raise ET.ParseError(f"Unsupported feed root for {source_url}: {root.tag}")


def parse_rss_item(
    entry: ET.Element,
    source_name: str,
    source_weight: float,
    cutoff: datetime,
) -> KnowledgeItem | None:
    title = clean_text(find_text(entry, "title"))
    link = clean_text(find_text(entry, "link"))
    summary = clean_text(find_text(entry, "description") or find_text(entry, "{*}encoded"), 500)
    published = parse_datetime(find_text(entry, "pubDate") or find_text(entry, "date"))

    if published and published < cutoff:
        return None
    if not title or not link:
        return None

    return KnowledgeItem(
        source_type="rss",
        source_name=source_name,
        title=title,
        url=link,
        summary=summary,
        published_at=to_iso(published),
        tags=["rss"],
        metrics={"source_weight": source_weight},
    )


def parse_atom_entry(
    entry: ET.Element,
    source_name: str,
    source_weight: float,
    cutoff: datetime,
) -> KnowledgeItem | None:
    title = clean_text(find_text(entry, "{*}title"))
    link = find_atom_link(entry)
    summary = clean_text(find_text(entry, "{*}summary") or find_text(entry, "{*}content"), 500)
    published = parse_datetime(find_text(entry, "{*}published") or find_text(entry, "{*}updated"))

    if published and published < cutoff:
        return None
    if not title or not link:
        return None

    return KnowledgeItem(
        source_type="rss",
        source_name=source_name,
        title=title,
        url=link,
        summary=summary,
        published_at=to_iso(published),
        tags=["rss"],
        metrics={"source_weight": source_weight},
    )


def find_text(entry: ET.Element, path: str) -> str | None:
    node = entry.find(path)
    if node is not None and node.text:
        return node.text
    return None


def find_atom_link(entry: ET.Element) -> str:
    for link in entry.findall("{*}link"):
        rel = link.attrib.get("rel", "alternate")
        href = link.attrib.get("href")
        if href and rel == "alternate":
            return href
    first = entry.find("{*}link")
    return first.attrib.get("href", "") if first is not None else ""


def strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[1]
    return tag


def polite_pause(seconds: float = 0.2) -> None:
    time.sleep(seconds)
