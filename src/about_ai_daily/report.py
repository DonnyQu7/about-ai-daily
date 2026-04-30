from __future__ import annotations

import html
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .classifier import CATEGORIES
from .models import KnowledgeItem, ReportSection


def write_outputs(
    items: list[KnowledgeItem],
    errors: list[str],
    report_title: str,
    output_dir: str | Path,
    data_dir: str | Path,
    run_date: datetime | None = None,
) -> tuple[Path, Path]:
    section = ReportSection(key="single", title="候选项目", hours=24, items=items, raw_count=len(items))
    paths = write_report_outputs([section], errors, report_title, output_dir, data_dir, run_date)
    return paths["markdown"], paths["json"]


def write_report_outputs(
    sections: list[ReportSection],
    errors: list[str],
    report_title: str,
    output_dir: str | Path,
    data_dir: str | Path,
    run_date: datetime | None = None,
) -> dict[str, Path]:
    now = run_date or datetime.now(timezone.utc)
    date_key = now.astimezone().date().isoformat()
    output_path = Path(output_dir)
    data_path = Path(data_dir) / "items" / f"{date_key}.json"
    markdown_path = output_path / f"{date_key}.md"
    html_path = output_path / f"{date_key}.html"
    poster_path = output_path / f"{date_key}-poster.svg"

    output_path.mkdir(parents=True, exist_ok=True)
    data_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path.write_text(render_markdown(sections, errors, report_title, now), encoding="utf-8")
    html_path.write_text(render_html(sections, errors, report_title, now, poster_path.name), encoding="utf-8")
    poster_path.write_text(render_poster_svg(sections, report_title, now), encoding="utf-8")
    data_path.write_text(
        json.dumps(
            {
                "generated_at": now.replace(microsecond=0).isoformat(),
                "errors": errors,
                "sections": [
                    {
                        "key": section.key,
                        "title": section.title,
                        "hours": section.hours,
                        "raw_count": section.raw_count,
                        "count": len(section.items),
                        "items": [item.to_dict() for item in section.items],
                    }
                    for section in sections
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "markdown": markdown_path,
        "html": html_path,
        "poster": poster_path,
        "json": data_path,
    }


def render_markdown(
    sections: list[ReportSection],
    errors: list[str],
    report_title: str,
    generated_at: datetime,
) -> str:
    lines: list[str] = [
        f"# {report_title} · {generated_at.astimezone().date().isoformat()}",
        "",
        f"> Generated at: {generated_at.astimezone().replace(microsecond=0).isoformat()}",
        "",
        "## 今日摘要",
        "",
    ]

    highlights = top_highlights(sections)
    if not highlights:
        lines.append("没有达到阈值的 GitHub 候选项目。可以降低 `report.min_score` 或扩大查询词。")
    else:
        for item in highlights:
            lines.append(f"- **{item.category}**：[{item.title}]({item.url})（评分 {item.score:.1f}）")

    for section in sections:
        lines.extend(["", f"## {section.title}", ""])
        lines.append(f"- 原始候选：{section.raw_count}")
        lines.append(f"- 入选项目：{len(section.items)}")
        lines.append("")
        append_markdown_section(lines, section.items)

    if errors:
        lines.extend(["", "## 采集告警", ""])
        for error in dedupe_errors(errors):
            lines.append(f"- {error}")

    lines.extend(
        [
            "",
            "## 选型建议",
            "",
            "- 优先看与 QA、E2E、API 测试、CI 执行流、测试数据和代码质量直接相关的项目。",
            "- 泛营销、销售、内容创作、非工程业务场景已默认降权。",
            "- 对高 Star 且仍在更新的项目，建议进一步检查 README、release、issue 活跃度和 license。",
            "",
        ]
    )
    return "\n".join(lines)


def append_markdown_section(lines: list[str], items: list[KnowledgeItem]) -> None:
    grouped = group_by_category(items)
    ordered_categories = list(CATEGORIES.keys()) + sorted(set(grouped) - set(CATEGORIES))
    for category in ordered_categories:
        category_items = grouped.get(category, [])
        if not category_items:
            continue

        lines.extend([f"### {category}", ""])
        for index, item in enumerate(category_items, start=1):
            lines.append(f"{index}. [{item.title}]({item.url})")
            lines.append(f"   - GitHub：{item.url}")
            lines.append(f"   - 做什么：{project_summary(item)}")
            lines.append(f"   - 评分：{item.score:.1f}")
            if item.published_at:
                lines.append(f"   - 更新时间：{item.published_at}")
            lines.append(f"   - 推荐理由：{'; '.join(item.reason)}")
            metric_text = render_metrics(item)
            if metric_text:
                lines.append(f"   - 热度信号：{metric_text}")
            lines.append("")


def render_html(
    sections: list[ReportSection],
    errors: list[str],
    report_title: str,
    generated_at: datetime,
    poster_filename: str,
) -> str:
    generated = generated_at.astimezone().replace(microsecond=0).isoformat()
    highlight_cards = "\n".join(render_highlight_card(item) for item in top_highlights(sections))
    section_html = "\n".join(render_html_section(section) for section in sections)
    error_html = render_error_html(errors)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(report_title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d9e1ee;
      --accent: #0f766e;
      --accent-2: #1d4ed8;
      --warn: #b45309;
      --shadow: 0 12px 34px rgba(23, 32, 51, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
      line-height: 1.55;
    }}
    a {{ color: inherit; text-decoration: none; }}
    .shell {{ max-width: 1180px; margin: 0 auto; padding: 32px 20px 56px; }}
    .hero {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 24px;
      align-items: stretch;
      margin-bottom: 22px;
    }}
    .hero-main, .hero-side, .section, .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}
    .hero-main {{ padding: 28px; }}
    .hero-side {{ padding: 22px; display: flex; flex-direction: column; gap: 14px; }}
    h1 {{ margin: 0 0 12px; font-size: 34px; line-height: 1.16; letter-spacing: 0; }}
    h2 {{ margin: 0 0 16px; font-size: 22px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 17px; letter-spacing: 0; }}
    .meta {{ color: var(--muted); font-size: 14px; }}
    .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 22px; }}
    .stat {{ border: 1px solid var(--line); border-radius: 8px; padding: 12px; background: #fbfcff; }}
    .stat b {{ display: block; font-size: 24px; color: var(--accent-2); }}
    .poster-link {{
      display: inline-flex;
      justify-content: center;
      align-items: center;
      min-height: 42px;
      border-radius: 8px;
      background: var(--ink);
      color: #fff;
      font-weight: 700;
      padding: 0 14px;
    }}
    .highlights {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-bottom: 22px; }}
    .card {{ padding: 18px; }}
    .card:hover {{ border-color: #9db4d5; transform: translateY(-1px); transition: 120ms ease; }}
    .badge {{ display: inline-flex; align-items: center; border: 1px solid #b6d7d2; color: #075e55; background: #ecfdf9; border-radius: 999px; padding: 2px 9px; font-size: 12px; font-weight: 700; }}
    .score {{ color: var(--accent-2); font-weight: 800; }}
    .summary {{ color: #344054; margin: 10px 0 12px; }}
    .url {{ color: var(--accent-2); word-break: break-all; font-size: 13px; }}
    .section {{ padding: 22px; margin: 22px 0; }}
    .category {{ margin-top: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }}
    .kv {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
    .pill {{ background: #eef2f7; color: #344054; border-radius: 999px; padding: 2px 8px; font-size: 12px; }}
    .reason {{ color: var(--muted); font-size: 13px; margin-top: 10px; }}
    .errors {{ border-color: #f3c98b; background: #fffbeb; color: #7c3e00; }}
    @media (max-width: 860px) {{
      .hero, .highlights, .grid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 28px; }}
      .stats {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="hero-main">
        <div class="badge">Software Testing Radar</div>
        <h1>{escape(report_title)}</h1>
        <p class="meta">生成时间：{escape(generated)} · 视角：软件测试、QA 自动化、执行流、工程质量</p>
        <div class="stats">
          <div class="stat"><b>{sum(section.raw_count for section in sections)}</b><span>原始候选</span></div>
          <div class="stat"><b>{sum(len(section.items) for section in sections)}</b><span>入选项目</span></div>
          <div class="stat"><b>{len(set(item.url for section in sections for item in section.items))}</b><span>去重项目</span></div>
        </div>
      </div>
      <aside class="hero-side">
        <h2>筛选原则</h2>
        <p class="meta">商业营销、内容创作、垂直行业但与编程/测试无关的项目已降权。优先关注 QA、E2E、API 测试、CI 执行流、代码质量和自动化工程。</p>
        <a class="poster-link" href="{escape(poster_filename)}">打开日报海报</a>
      </aside>
    </section>

    <section>
      <h2>Top Highlights</h2>
      <div class="highlights">{highlight_cards}</div>
    </section>

    {section_html}
    {error_html}
  </main>
</body>
</html>
"""


def render_html_section(section: ReportSection) -> str:
    grouped = group_by_category(section.items)
    categories = []
    ordered_categories = list(CATEGORIES.keys()) + sorted(set(grouped) - set(CATEGORIES))
    for category in ordered_categories:
        items = grouped.get(category, [])
        if not items:
            continue
        cards = "\n".join(render_project_card(item) for item in items)
        categories.append(f"""<div class="category">
  <h3>{escape(category)}</h3>
  <div class="grid">{cards}</div>
</div>""")

    content = "\n".join(categories) or "<p class=\"meta\">没有达到阈值的候选项目。</p>"
    return f"""<section class="section">
  <h2>{escape(section.title)}</h2>
  <p class="meta">窗口：最近 {section.hours} 小时 · 原始候选 {section.raw_count} · 入选 {len(section.items)}</p>
  {content}
</section>"""


def render_highlight_card(item: KnowledgeItem) -> str:
    return f"""<a class="card" href="{escape(item.url)}" target="_blank" rel="noopener">
  <span class="badge">{escape(item.category)}</span>
  <h3>{escape(item.title)}</h3>
  <p class="summary">{escape(project_summary(item))}</p>
  <div class="score">评分 {item.score:.1f}</div>
</a>"""


def render_project_card(item: KnowledgeItem) -> str:
    return f"""<a class="card" href="{escape(item.url)}" target="_blank" rel="noopener">
  <span class="badge">{escape(item.category)}</span>
  <h3>{escape(item.title)}</h3>
  <p class="summary"><strong>做什么：</strong>{escape(project_summary(item))}</p>
  <div class="url">{escape(item.url)}</div>
  <div class="kv">
    <span class="pill">评分 {item.score:.1f}</span>
    <span class="pill">{escape(render_metrics(item))}</span>
  </div>
  <p class="reason">{escape('; '.join(item.reason))}</p>
</a>"""


def render_error_html(errors: list[str]) -> str:
    unique = dedupe_errors(errors)
    if not unique:
        return ""
    items = "".join(f"<li>{escape(error)}</li>" for error in unique)
    return f"""<section class="section errors">
  <h2>采集告警</h2>
  <ul>{items}</ul>
</section>"""


def render_poster_svg(
    sections: list[ReportSection],
    report_title: str,
    generated_at: datetime,
) -> str:
    highlights = top_highlights(sections, limit=6)
    rows = []
    y = 210
    for index, item in enumerate(highlights, start=1):
        title = truncate(f"{index}. {item.title}", 52)
        summary = truncate(project_summary(item), 76)
        rows.append(f'<text x="70" y="{y}" class="item-title">{escape(title)}</text>')
        rows.append(f'<text x="70" y="{y + 28}" class="item-summary">{escape(summary)}</text>')
        rows.append(f'<text x="930" y="{y}" class="score">评分 {item.score:.1f}</text>')
        y += 88

    date_text = generated_at.astimezone().date().isoformat()
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">
  <style>
    .bg {{ fill: #f5f7fb; }}
    .panel {{ fill: #ffffff; stroke: #d9e1ee; stroke-width: 2; }}
    .title {{ font: 700 52px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #172033; }}
    .sub {{ font: 400 25px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #667085; }}
    .item-title {{ font: 700 25px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #172033; }}
    .item-summary {{ font: 400 21px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #475467; }}
    .score {{ font: 700 22px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #1d4ed8; text-anchor: end; }}
    .foot {{ font: 500 22px -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; fill: #0f766e; }}
  </style>
  <rect class="bg" width="1080" height="1350"/>
  <rect class="panel" x="42" y="42" width="996" height="1266" rx="18"/>
  <text x="70" y="118" class="sub">Software Testing Radar · {escape(date_text)}</text>
  <text x="70" y="178" class="title">{escape(truncate(report_title, 24))}</text>
  {''.join(rows)}
  <text x="70" y="1240" class="foot">聚焦 QA 自动化、执行流、E2E/API 测试、工程质量 · HTML 报告可点击跳转 GitHub</text>
</svg>
"""


def group_by_category(items: list[KnowledgeItem]) -> dict[str, list[KnowledgeItem]]:
    grouped: dict[str, list[KnowledgeItem]] = defaultdict(list)
    for item in items:
        grouped[item.category].append(item)
    return grouped


def top_highlights(sections: list[ReportSection], limit: int = 8) -> list[KnowledgeItem]:
    seen: set[str] = set()
    highlights: list[KnowledgeItem] = []
    for item in sorted((item for section in sections for item in section.items), key=lambda x: x.score, reverse=True):
        if item.url in seen:
            continue
        seen.add(item.url)
        highlights.append(item)
        if len(highlights) >= limit:
            break
    return highlights


def project_summary(item: KnowledgeItem) -> str:
    summary = (item.summary or "").strip()
    if summary:
        return truncate(summary, 260)
    return "该项目没有提供描述，建议打开 GitHub README 进一步确认。"


def render_metrics(item: KnowledgeItem) -> str:
    if item.source_type == "github":
        return f"stars={item.metrics.get('stars', 0)}, forks={item.metrics.get('forks', 0)}, language={item.metrics.get('language') or 'unknown'}"
    if item.source_type == "hacker_news":
        return f"score={item.metrics.get('hn_score', 0)}, comments={item.metrics.get('comments', 0)}"
    if item.source_type == "rss":
        return f"source_weight={item.metrics.get('source_weight', 1.0)}"
    return ""


def dedupe_errors(errors: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for error in errors:
        if error not in seen:
            seen.add(error)
            unique.append(error)
    return unique


def truncate(value: str, max_length: int) -> str:
    value = " ".join(value.split())
    if len(value) <= max_length:
        return value
    return value[: max_length - 1].rstrip() + "…"


def escape(value: object) -> str:
    return html.escape(str(value), quote=True)
