from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from typing import Any


USER_AGENT = "AboutAI-Daily/0.1 (+https://github.com/local/about-ai-daily)"


class HttpError(RuntimeError):
    pass


def build_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if extra:
        headers.update(extra)
    return headers


def get_text(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers=build_headers(headers))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:180]
        raise HttpError(f"HTTP {exc.code} for {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise HttpError(f"Network error for {url}: {exc.reason}") from exc


def get_json(url: str, headers: dict[str, str] | None = None, timeout: int = 20) -> Any:
    text = get_text(url, headers=headers, timeout=timeout)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise HttpError(f"Invalid JSON from {url}: {exc}") from exc


def github_headers(expected_user: str | None = None) -> tuple[dict[str, str], str | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    warning = None
    if not token and expected_user:
        token = gh_cli_token(expected_user)
        if not token:
            warning = (
                f"GitHub CLI has no valid token for {expected_user}. "
                f"Run: gh auth login -h github.com"
            )
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers, warning


def gh_cli_token(user: str) -> str | None:
    try:
        result = subprocess.run(
            ["gh", "auth", "token", "--hostname", "github.com", "--user", user],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

    if result.returncode != 0:
        return None
    token = result.stdout.strip()
    return token or None
