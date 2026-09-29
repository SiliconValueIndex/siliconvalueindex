"""Offline stand-in for the Best Buy Products API.

Reads made-up listings from data/raw/prices/mock_bestbuy.json and runs them
through the real Best Buy search and normalizer, so the whole pipeline
(fetch -> normalize -> history -> score -> site) can be exercised without an
API key. Observations are labelled retailer "mock". It is never listed in
pricing.retailers; run it explicitly with `--retailers mock` and discard the
output with `git restore data/`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from svi.config import RAW_DIR, Config
from svi.ids import Resolver
from svi.models import UnresolvedName
from svi.scrapers import bestbuy

FIXTURE_PATH = RAW_DIR / "prices" / "mock_bestbuy.json"


def load_products(path: Path = FIXTURE_PATH) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["products"]


def fixture_fetch(products: list[dict]):
    """A `fetch` for bestbuy.scrape_prices that mimics Best Buy's keyword search:
    every search word must appear in the product name."""

    def fetch(query: str, category_id: str, api_key: str) -> list[dict]:
        words = [part.removeprefix("search=").lower() for part in query.split("&")]
        return [p for p in products if all(w in p["name"].lower() for w in words)]

    return fetch


def scrape_prices(
    resolver: Resolver,
    registry: pd.DataFrame,
    cfg: Config,
    *,
    run_id: str,
    now: datetime,
    path: Path = FIXTURE_PATH,
) -> tuple[pd.DataFrame, list[UnresolvedName]]:
    obs, unresolved = bestbuy.scrape_prices(
        resolver,
        registry,
        cfg,
        run_id=run_id,
        now=now,
        api_key="mock",
        fetch=fixture_fetch(load_products(path)),
        pause=0,
    )
    obs["retailer"] = "mock"
    return obs, unresolved
