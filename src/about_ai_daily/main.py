from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .classifier import classify_items
from .collectors import collect_all, collect_github
from .config import load_config
from .dedupe import dedupe_items
from .models import ReportSection
from .report import write_outputs, write_report_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate daily AI application intelligence report.")
    parser.add_argument("--config", default="config/sources.example.json", help="Path to JSON config file.")
    parser.add_argument("--hours", type=int, default=24, help="Collection time window.")
    parser.add_argument("--output-dir", default="reports", help="Markdown report output directory.")
    parser.add_argument("--data-dir", default="data", help="JSON data output directory.")
    parser.add_argument("--max-items", type=int, default=None, help="Override max report items.")
    return parser


def run(args: argparse.Namespace) -> tuple[dict[str, Path], int, int]:
    config = load_config(args.config)
    report_config = config.get("report", {})
    windows = report_config.get("windows") or []

    if windows:
        sections: list[ReportSection] = []
        errors: list[str] = []
        total_raw = 0
        total_selected = 0
        github_config = config.get("github", {})
        min_score = float(report_config.get("min_score", 4.5))

        for window in windows:
            hours = int(window.get("hours", args.hours))
            max_items = args.max_items or int(window.get("max_items", report_config.get("max_items", 50)))
            collection = collect_github(github_config, hours)
            deduped = dedupe_items(collection.items)
            selected = classify_items(deduped, min_score=min_score)[:max_items]
            errors.extend(collection.errors)
            total_raw += len(collection.items)
            total_selected += len(selected)
            sections.append(
                ReportSection(
                    key=str(window.get("key", f"{hours}h")),
                    title=str(window.get("title", f"最近 {hours} 小时 GitHub 热点")),
                    hours=hours,
                    items=selected,
                    raw_count=len(collection.items),
                )
            )

        paths = write_report_outputs(
            sections,
            errors,
            report_config.get("title", "软件测试与自动化执行流 GitHub 热点日报"),
            args.output_dir,
            args.data_dir,
        )
        return paths, total_raw, total_selected

    collection = collect_all(config, args.hours)
    deduped = dedupe_items(collection.items)
    min_score = float(report_config.get("min_score", 2.5))
    classified = classify_items(deduped, min_score=min_score)

    max_items = args.max_items or int(report_config.get("max_items", 50))
    selected = classified[:max_items]

    report_path, data_path = write_outputs(
        selected,
        collection.errors,
        report_config.get("title", "AI 应用落地知识日报"),
        args.output_dir,
        args.data_dir,
    )
    return {"markdown": report_path, "json": data_path}, len(collection.items), len(selected)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        paths, raw_count, selected_count = run(args)
    except Exception as exc:
        print(f"about-ai-daily failed: {exc}", file=sys.stderr)
        return 1

    print(f"Collected raw items: {raw_count}")
    print(f"Selected report items: {selected_count}")
    if "markdown" in paths:
        print(f"Markdown report: {paths['markdown']}")
    if "html" in paths:
        print(f"HTML report: {paths['html']}")
    if "poster" in paths:
        print(f"Poster: {paths['poster']}")
    if "json" in paths:
        print(f"JSON archive: {paths['json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
