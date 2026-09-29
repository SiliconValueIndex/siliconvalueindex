"""Retailer adapters and safe user-facing error messages."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Protocol

import pandas as pd

from svi.config import Config
from svi.ids import Resolver
from svi.models import UnresolvedName


class RetailerSkipped(Exception):
    """An expected reason why a retailer cannot run."""


class RetailerAdapter(Protocol):
    def __call__(
        self, resolver: Resolver, registry: pd.DataFrame, cfg: Config, *, run_id: str, now: datetime
    ) -> tuple[pd.DataFrame, list[UnresolvedName]]:
        """Return observations with exactly PRICE_COLUMNS and unresolved names."""
        ...


def _bestbuy(resolver, registry, cfg, *, run_id, now):
    from svi.scrapers.bestbuy import scrape_prices

    return scrape_prices(resolver, registry, cfg, run_id=run_id, now=now)


def _newegg(resolver, registry, cfg, *, run_id, now):
    from svi.scrapers.rakuten import scrape_newegg_prices

    return scrape_newegg_prices(resolver, registry, cfg, run_id=run_id, now=now)


def _mock(resolver, registry, cfg, *, run_id, now):
    from svi.scrapers.mock import scrape_prices

    return scrape_prices(resolver, registry, cfg, run_id=run_id, now=now)


# "mock" is offline test data: run it with --retailers mock, never list it in pricing.retailers.
ADAPTERS: dict[str, RetailerAdapter] = {"bestbuy": _bestbuy, "newegg": _newegg, "mock": _mock}
DISPLAY_NAMES = {"bestbuy": "Best Buy", "newegg": "Newegg", "mock": "Mock (test data)"}
SECRET_ENV_VARS = ("BESTBUY_API_KEY", "RAKUTEN_CLIENT_SECRET", "RAKUTEN_CLIENT_ID")


def display_name(name: str) -> str:
    return DISPLAY_NAMES.get(name, name)


def get_adapter(name: str) -> RetailerAdapter:
    try:
        return ADAPTERS[name]
    except KeyError:
        raise KeyError(f"{name}: unknown retailer") from None


def redact_secrets(text: str) -> str:
    """Remove configured credentials before displaying adapter errors or skips."""
    for var in SECRET_ENV_VARS:
        if secret := os.environ.get(var, "").strip():
            text = text.replace(secret, "***")
    return text
