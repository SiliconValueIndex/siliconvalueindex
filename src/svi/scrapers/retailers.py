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


ADAPTERS: dict[str, RetailerAdapter] = {"bestbuy": _bestbuy}


def get_adapter(name: str) -> RetailerAdapter:
    try:
        return ADAPTERS[name]
    except KeyError:
        raise KeyError(f"{name}: unknown retailer") from None


def redact_secrets(text: str) -> str:
    """Remove configured credentials before displaying adapter errors or skips."""
    if secret := os.environ.get("BESTBUY_API_KEY"):
        text = text.replace(secret, "***")
    return text
