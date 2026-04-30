#!/usr/bin/env python3
from __future__ import annotations

import argparse
import mimetypes
import os
import smtplib
from email.message import EmailMessage
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send daily AI testing report email.")
    parser.add_argument("--to", required=True, help="Recipient email address.")
    parser.add_argument("--subject", required=True, help="Email subject.")
    parser.add_argument("--html-report", required=True, help="Generated HTML report path.")
    parser.add_argument("--poster", required=True, help="Generated poster path.")
    parser.add_argument("--link", required=True, help="Public report link.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    smtp_from = os.environ.get("SMTP_FROM") or smtp_username

    missing = [
        name
        for name, value in {
            "SMTP_HOST": smtp_host,
            "SMTP_USERNAME": smtp_username,
            "SMTP_PASSWORD": smtp_password,
            "SMTP_FROM or SMTP_USERNAME": smtp_from,
        }.items()
        if not value
    ]
    if missing:
        raise SystemExit(f"Missing SMTP configuration: {', '.join(missing)}")

    html_report = Path(args.html_report)
    poster = Path(args.poster)
    if not html_report.exists():
        raise SystemExit(f"HTML report not found: {html_report}")
    if not poster.exists():
        raise SystemExit(f"Poster not found: {poster}")

    message = EmailMessage()
    message["From"] = smtp_from
    message["To"] = args.to
    message["Subject"] = args.subject
    message.set_content(
        f"软件测试与自动化执行流 GitHub 热点日报已生成：{args.link}\n\n"
        "附件包含日报海报，可用于快速预览和转发。"
    )
    message.add_alternative(
        f"""
        <html>
          <body>
            <h2>软件测试与自动化执行流 GitHub 热点日报</h2>
            <p>报告已生成，可直接打开 HTML 页面查看并点击跳转 GitHub 项目。</p>
            <p><a href="{args.link}">打开 HTML 报告</a></p>
            <p>附件包含本次日报海报。</p>
          </body>
        </html>
        """,
        subtype="html",
    )

    attach_file(message, poster)
    attach_file(message, html_report)

    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
    else:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)

    print(f"Sent report email to {args.to}")
    return 0


def attach_file(message: EmailMessage, path: Path) -> None:
    content_type, _ = mimetypes.guess_type(path.name)
    if not content_type:
        content_type = "application/octet-stream"
    maintype, subtype = content_type.split("/", 1)
    message.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)


if __name__ == "__main__":
    raise SystemExit(main())
