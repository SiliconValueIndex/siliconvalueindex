"""Newegg prices from Rakuten Advertising's Product Search API.

Docs: https://developers.rakutenadvertising.com/guides/product_search
Newegg's affiliate program runs on Rakuten. Once the publisher partnership is approved,
Product Search returns Newegg's catalog with prices and a tracked `linkurl` for each
listing, so no page scraping is needed. Credentials come from RAKUTEN_CLIENT_ID,
RAKUTEN_CLIENT_SECRET and RAKUTEN_SID and are never written to disk.

Until the partnership is approved the adapter raises RetailerSkipped, so a pending
application shows up as a note in the run report rather than a failure.

For every active GPU we run one keyword search limited to Newegg's advertiser id, keep
listings whose title resolves to that same gpu_id, drop bundles, laptops and non-new
condition, and record every remaining offer as a price observation. Validation against
price history happens in svi.prices.

The feed has no stock field. Listings are recorded as in stock; the price band in
validate_observations and the lowest-valid-price selection limit the effect of a stale
catalog row.
"""

from __future__ import annotations

import base64
import os
import re
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime

import pandas as pd
import requests

from svi.config import Config
from svi.ids import Resolver, has_negative_token
from svi.models import UnresolvedName
from svi.prices import PRICE_COLUMNS
from svi.scrapers.base import USER_AGENT
from svi.scrapers.bestbuy import VENDOR_PREFIX
from svi.scrapers.retailers import RetailerSkipped

API_BASE = "https://api.linksynergy.com"
TOKEN_URL = f"{API_BASE}/token"
SEARCH_URL = f"{API_BASE}/productsearch/1.0"
PAGE_SIZE = 100  # Product Search maximum
# Partnership states that mean the publisher may use the advertiser's links and feed.
APPROVED_STATUSES = {"active", "extended"}
# Product Search answers "no results" with this error document rather than an empty list.
NO_MATCHES_ERROR_ID = "7186919"
_NOT_NEW = re.compile(r"\bopen[\s-]?box\b|\brefurb", re.IGNORECASE)


class RakutenError(RuntimeError):
    pass


@dataclass(frozen=True)
class Credentials:
    client_id: str
    client_secret: str
    sid: str


def credentials_from_env() -> Credentials | None:
    values = [
        os.environ.get(k, "").strip()
        for k in ("RAKUTEN_CLIENT_ID", "RAKUTEN_CLIENT_SECRET", "RAKUTEN_SID")
    ]
    return Credentials(*values) if all(values) else None


def _request(method: str, url: str, *, what: str, timeout: int = 30, **kwargs) -> requests.Response:
    """HTTP with retries. Errors carry the exception class and status only: never the URL,
    headers, or body, which could contain credentials."""
    last = "RakutenError"
    for attempt in range(3):
        try:
            r = requests.request(
                method,
                url,
                headers={"User-Agent": USER_AGENT, **kwargs.pop("headers", {})},
                timeout=timeout,
                **kwargs,
            )
            if r.status_code in (401, 403):
                raise RakutenError(
                    f"Rakuten rejected the credentials for {what} (HTTP {r.status_code})"
                )
            if r.status_code < 500 and r.status_code != 429:
                return r
            last = f"RakutenError: {what} HTTP {r.status_code}"
        except requests.RequestException as exc:
            last = f"{type(exc).__name__} during {what}"
        time.sleep(2 * (attempt + 1))
    raise RakutenError(last) from None


def fetch_token(creds: Credentials) -> str:
    encoded = base64.b64encode(f"{creds.client_id}:{creds.client_secret}".encode()).decode()
    r = _request(
        "POST",
        TOKEN_URL,
        what="token request",
        headers={"Authorization": f"Bearer {encoded}"},
        data={"grant_type": "client_credentials", "scope": creds.sid},
    )
    if r.status_code != 200:
        raise RakutenError(f"Rakuten token request failed (HTTP {r.status_code})")
    return r.json()["access_token"]


def partnership_status(token: str, mid: str) -> str:
    """'pending', 'extended', ...; 'none' when the publisher never applied."""
    r = _request(
        "GET",
        f"{API_BASE}/v1/partnerships/{mid}",
        what="partnership lookup",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
    )
    if r.status_code == 404:
        return "none"
    if r.status_code != 200:
        raise RakutenError(f"Rakuten partnership lookup failed (HTTP {r.status_code})")
    return str((r.json().get("partnerships") or {}).get("status", "unknown")).lower()


def parse_search_xml(text: str) -> tuple[list[dict], int]:
    """Returns (items, total_pages). Item dicts hold the fields the adapter uses."""
    root = ET.fromstring(text)
    errors = root.find("Errors")
    if errors is not None:
        if (errors.findtext("ErrorID") or "").strip() == NO_MATCHES_ERROR_ID:
            return [], 0
        raise RakutenError(f"Product Search error {errors.findtext('ErrorID', '').strip()}")
    items = []
    for it in root.iter("item"):
        price = it.find("price")
        sale = it.find("saleprice")
        items.append(
            {
                "sku": (it.findtext("sku") or "").strip(),
                "productname": (it.findtext("productname") or "").strip(),
                "price": (price.text or "").strip() if price is not None else "",
                "saleprice": (sale.text or "").strip() if sale is not None else "",
                "currency": (price.get("currency", "USD") if price is not None else "USD").upper(),
                "linkurl": (it.findtext("linkurl") or "").strip(),
            }
        )
    return items, int(root.findtext("TotalPages") or 0)


def search_products(
    token: str, keyword: str, mid: str, *, max_pages: int = 2, pause: float = 1.0
) -> list[dict]:
    items: list[dict] = []
    for page in range(1, max_pages + 1):
        r = _request(
            "GET",
            SEARCH_URL,
            what="product search",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/xml"},
            params={"keyword": keyword, "mid": mid, "max": PAGE_SIZE, "pagenumber": page},
        )
        if r.status_code != 200:
            raise RakutenError(f"Product Search failed (HTTP {r.status_code})")
        page_items, total_pages = parse_search_xml(r.text)
        items += page_items
        if page >= total_pages:
            break
        time.sleep(pause)
    return items


def search_keyword(vendor: str, display_name: str) -> str:
    """Product Search matches all words in `keyword`."""
    return f"{VENDOR_PREFIX.get(vendor, '')} {display_name}".strip()


def _price(value: str) -> float | None:
    try:
        p = float(value.replace(",", ""))
    except ValueError:
        return None
    return p if p > 0 else None


def items_to_observations(
    items: list[dict],
    gpu_id: str,
    resolver: Resolver,
    *,
    now: datetime,
    run_id: str,
) -> tuple[list[dict], list[UnresolvedName]]:
    """Keep listings that resolve to gpu_id. Returns (observations, unresolved_titles)."""
    obs: list[dict] = []
    unresolved: list[UnresolvedName] = []
    for it in items:
        title = it["productname"]
        if has_negative_token(title) or it["currency"] != "USD":
            continue
        hit = resolver.resolve(title, source="newegg")
        if isinstance(hit, UnresolvedName):
            unresolved.append(hit)
            continue
        if hit != gpu_id:
            continue  # a different card matched the keyword search
        obs.append(
            {
                "gpu_id": gpu_id,
                "retailer": "newegg",
                "sku": it["sku"],
                "title_raw": title,
                "price": _price(it["saleprice"]) or _price(it["price"]),
                "currency": "USD",
                "url": it["linkurl"],  # Rakuten tracking link: the affiliate link
                "condition": "refurb" if _NOT_NEW.search(title) else "new",
                "in_stock": True,  # the feed has no availability field; see module docstring
                "is_valid": True,
                "invalid_reason": "",
                "fetched_at": now,
                "run_id": run_id,
            }
        )
    return obs, unresolved


def scrape_newegg_prices(
    resolver: Resolver,
    registry: pd.DataFrame,
    cfg: Config,
    *,
    run_id: str,
    now: datetime | None = None,
    creds: Credentials | None = None,
    token_fn=fetch_token,
    status_fn=partnership_status,
    search_fn=search_products,
    pause: float = 1.0,
) -> tuple[pd.DataFrame, list[UnresolvedName]]:
    """One search per active GPU. Network functions are injectable for tests."""
    now = now or datetime.now(UTC)
    creds = creds or credentials_from_env()
    if creds is None:
        raise RetailerSkipped(
            "RAKUTEN_CLIENT_ID, RAKUTEN_CLIENT_SECRET and RAKUTEN_SID are not all set"
        )
    mid = cfg.pricing.newegg_rakuten_mid
    token = token_fn(creds)
    status = status_fn(token, mid)
    if status not in APPROVED_STATUSES:
        raise RetailerSkipped(f"Newegg partnership on Rakuten is '{status}', not approved yet")

    active = registry[registry["is_active"].astype(str).str.lower() == "true"]
    rows: list[dict] = []
    unresolved: dict[str, UnresolvedName] = {}
    for r in active.itertuples(index=False):
        items = search_fn(token, search_keyword(r.vendor, r.display_name), mid)
        obs, unres = items_to_observations(items, r.gpu_id, resolver, now=now, run_id=run_id)
        rows += obs
        for u in unres:
            unresolved.setdefault(u.raw_name, u)
        time.sleep(pause)
    return pd.DataFrame(rows, columns=PRICE_COLUMNS), list(unresolved.values())
