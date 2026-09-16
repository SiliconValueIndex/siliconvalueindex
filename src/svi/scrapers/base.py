"""Shared HTTP fetching: descriptive user agent, retries, robots check, snapshots."""

from __future__ import annotations

import time
import urllib.robotparser as robotparser
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

import requests

from svi.config import RAW_DIR

USER_AGENT = (
    "SiliconValueIndexBot/2.0 (+https://siliconvalueindex.com; weekly benchmark index refresh)"
)
SNAPSHOT_DIR = RAW_DIR / "benchmarks" / "toms"


class FetchError(RuntimeError):
    pass


@lru_cache(maxsize=8)
def _robots(origin: str) -> robotparser.RobotFileParser:
    rp = robotparser.RobotFileParser(f"{origin}/robots.txt")
    try:
        rp.read()
    except Exception:  # noqa: BLE001 - unreadable robots: be conservative, allow nothing
        rp.disallow_all = True
    return rp


def allowed_by_robots(url: str) -> bool:
    parts = urlsplit(url)
    return _robots(f"{parts.scheme}://{parts.netloc}").can_fetch(USER_AGENT, url)


def fetch_text(
    url: str, *, retries: int = 3, timeout: int = 60, respect_robots: bool = True
) -> str:
    if respect_robots and not allowed_by_robots(url):
        raise FetchError(f"robots.txt disallows {url}")
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            if r.status_code == 200 and r.text:
                return r.text
            last = FetchError(f"HTTP {r.status_code} for {url}")
        except requests.RequestException as exc:
            last = exc
        time.sleep(2 * (attempt + 1))
    raise FetchError(f"failed to fetch {url}: {last}")


def save_snapshot(text: str, name: str, now: datetime | None = None) -> Path:
    """Keep the raw HTML so a run can be reprocessed offline. Gitignored."""
    now = now or datetime.now(UTC)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{now.strftime('%Y-%m-%d')}_{name}.html"
    path.write_text(text, encoding="utf-8")
    return path
