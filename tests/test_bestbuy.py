from datetime import UTC, datetime

import pandas as pd
import pytest

from svi.config import get_config
from svi.ids import Resolver
from svi.scrapers.bestbuy import (
    BestBuyError,
    products_to_observations,
    scrape_prices,
    search_query,
)

NOW = datetime(2026, 9, 16, tzinfo=UTC)

# Shape of the Best Buy Products API response, trimmed to the fields we request.
PRODUCTS_4070 = [
    {
        "sku": 6536507,
        "name": "MSI - NVIDIA GeForce RTX 4070 VENTUS 2X 12GB GDDR6X PCI Express 4.0 "
        "Graphics Card - Black",
        "regularPrice": 599.99,
        "salePrice": 549.99,
        "onlineAvailability": True,
        "url": "https://api.bestbuy.com/click/-/6536507/pdp",
        "condition": "new",
    },
    {
        "sku": 6536508,
        "name": "ASUS - NVIDIA GeForce RTX 4070 Ti SUPER 16GB GDDR6X OC Graphics Card",
        "regularPrice": 849.99,
        "salePrice": 849.99,
        "onlineAvailability": True,
        "url": "https://api.bestbuy.com/click/-/6536508/pdp",
        "condition": "new",
    },
    {
        "sku": 6536509,
        "name": "Gigabyte - NVIDIA GeForce RTX 4070 Gaming Laptop 16GB",
        "regularPrice": 1299.99,
        "salePrice": 1299.99,
        "onlineAvailability": True,
        "url": "",
        "condition": "new",
    },
    {
        "sku": 6536510,
        "name": "PNY - NVIDIA GeForce RTX 4070 12GB Refurbished",
        "regularPrice": 499.99,
        "salePrice": 499.99,
        "onlineAvailability": True,
        "url": "",
        "condition": "refurbished",
    },
    {
        "sku": 6536511,
        "name": "Zotac - NVIDIA GeForce RTX 4070 Twin Edge 12GB",
        "regularPrice": 569.99,
        "salePrice": None,
        "onlineAvailability": False,
        "url": "",
        "condition": "new",
    },
]


def test_search_query_words():
    assert (
        search_query("NVIDIA", "RTX 4070 Ti Super")
        == "search=GeForce&search=RTX&search=4070&search=Ti&search=Super"
    )


def test_products_filtered_to_requested_gpu():
    resolver = Resolver.from_files()
    obs, unresolved = products_to_observations(
        PRODUCTS_4070, "nvidia-rtx-4070", resolver, now=NOW, run_id="t"
    )
    titles = [o["title_raw"] for o in obs]
    assert len(obs) == 2  # MSI (sale) and Zotac (out of stock); Ti Super, laptop, refurb excluded
    assert obs[0]["price"] == 549.99 and obs[0]["in_stock"] is True
    assert obs[1]["price"] == 569.99 and obs[1]["in_stock"] is False
    assert all("Ti SUPER" not in t and "Laptop" not in t for t in titles)
    assert not unresolved


def test_scrape_prices_uses_injected_fetch_and_requires_key(monkeypatch):
    monkeypatch.delenv("BESTBUY_API_KEY", raising=False)
    resolver = Resolver.from_files()
    registry = pd.DataFrame(
        [
            {
                "gpu_id": "nvidia-rtx-4070",
                "vendor": "NVIDIA",
                "display_name": "RTX 4070",
                "is_active": "true",
            },
            {
                "gpu_id": "nvidia-rtx-2060",
                "vendor": "NVIDIA",
                "display_name": "RTX 2060",
                "is_active": "false",
            },
        ]
    )
    with pytest.raises(BestBuyError):
        scrape_prices(resolver, registry, get_config(), run_id="t", now=NOW, fetch=lambda *a: [])

    calls: list[str] = []

    def fake_fetch(query, category, key):
        calls.append(query)
        return PRODUCTS_4070

    df, unresolved = scrape_prices(
        resolver,
        registry,
        get_config(),
        run_id="t",
        now=NOW,
        api_key="k",
        fetch=fake_fetch,
        pause=0,
    )
    assert calls == ["search=GeForce&search=RTX&search=4070"]  # inactive card not searched
    assert len(df) == 2 and set(df["gpu_id"]) == {"nvidia-rtx-4070"}
    assert list(df.columns)[:3] == ["gpu_id", "retailer", "sku"]
