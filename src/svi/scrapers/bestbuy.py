"""Best Buy Products API client.

Docs: https://bestbuyapis.github.io/api-documentation/#products-api
Free developer keys allow 5 requests per second and 50,000 per day, far above
what a weekly run of ~60 searches needs. The key is read from BESTBUY_API_KEY and
never written to disk.

For every active GPU we run one keyword search inside the desktop graphics card
category, keep listings whose title resolves to that same gpu_id, drop bundles,
laptops and non-new condition, and record every remaining offer as a price
observation. Validation against price history happens in svi.prices.
"""

from __future__ import annotations

import os
import time
from datetime import UTC, datetime

import pandas as pd
import requests

from svi.config import Config
from svi.ids import Resolver, has_negative_token
from svi.models import UnresolvedName
from svi.prices import PRICE_COLUMNS
from svi.scrapers.base import USER_AGENT

API_URL = "https://api.bestbuy.com/v1/products"
SHOW = "sku,name,regularPrice,salePrice,onlineAvailability,url,condition,manufacturer"
VENDOR_PREFIX = {"NVIDIA": "GeForce", "AMD": "Radeon", "Intel": "Intel"}


class BestBuyError(RuntimeError):
    pass


def search_query(vendor: str, display_name: str) -> str:
    """Best Buy's search syntax: each word must appear in the product name."""
    words = f"{VENDOR_PREFIX.get(vendor, '')} {display_name}".split()
    return "&".join(f"search={w}" for w in words)


def fetch_products(query: str, category_id: str, api_key: str, *, timeout: int = 30) -> list[dict]:
    url = f"{API_URL}(({query})&categoryPath.id={category_id})"
    params = {"apiKey": api_key, "format": "json", "show": SHOW, "pageSize": 50}
    last: Exception | None = None
    for attempt in range(3):
        try:
            r = requests.get(
                url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout
            )
            if r.status_code == 200:
                return r.json().get("products", [])
            if r.status_code == 403:
                raise BestBuyError("Best Buy API rejected the key (403)")
            last = BestBuyError(f"HTTP {r.status_code}: {r.text[:200]}")
        except requests.RequestException as exc:
            last = exc
        time.sleep(1 + attempt)
    raise BestBuyError(f"search failed for {query}: {last}")


def products_to_observations(
    products: list[dict],
    gpu_id: str,
    resolver: Resolver,
    *,
    now: datetime,
    run_id: str,
) -> tuple[list[dict], list[UnresolvedName]]:
    """Keep listings that resolve to gpu_id. Returns (observations, unresolved_titles)."""
    obs: list[dict] = []
    unresolved: list[UnresolvedName] = []
    for p in products:
        title = str(p.get("name", ""))
        if has_negative_token(title):
            continue
        hit = resolver.resolve(title, source="bestbuy")
        if isinstance(hit, UnresolvedName):
            unresolved.append(hit)
            continue
        if hit != gpu_id:
            continue  # a different card matched the keyword search
        price = p.get("salePrice") or p.get("regularPrice")
        condition = str(p.get("condition", "new")).lower()
        obs.append(
            {
                "gpu_id": gpu_id,
                "retailer": "bestbuy",
                "sku": str(p.get("sku", "")),
                "title_raw": title,
                "price": float(price) if price else None,
                "currency": "USD",
                "url": str(p.get("url", "")),
                "condition": "new" if condition == "new" else "refurb",
                "in_stock": bool(p.get("onlineAvailability", False)),
                "is_valid": True,
                "invalid_reason": "",
                "fetched_at": now,
                "run_id": run_id,
            }
        )
    return obs, unresolved


def scrape_prices(
    resolver: Resolver,
    registry: pd.DataFrame,
    cfg: Config,
    *,
    run_id: str,
    now: datetime | None = None,
    api_key: str | None = None,
    fetch=None,
    pause: float = 0.25,
) -> tuple[pd.DataFrame, list[UnresolvedName]]:
    """One search per active GPU. `fetch` is injectable for tests."""
    fetch = fetch or fetch_products
    now = now or datetime.now(UTC)
    api_key = api_key or os.environ.get("BESTBUY_API_KEY", "")
    if not api_key:
        raise BestBuyError("BESTBUY_API_KEY is not set")
    active = registry[registry["is_active"].astype(str).str.lower() == "true"]
    rows: list[dict] = []
    unresolved: dict[str, UnresolvedName] = {}
    for r in active.itertuples(index=False):
        products = fetch(
            search_query(r.vendor, r.display_name), cfg.pricing.bestbuy_category_id, api_key
        )
        obs, unres = products_to_observations(products, r.gpu_id, resolver, now=now, run_id=run_id)
        rows += obs
        for u in unres:
            unresolved.setdefault(u.raw_name, u)
        time.sleep(pause)
    df = pd.DataFrame(rows, columns=PRICE_COLUMNS)
    return df, list(unresolved.values())
