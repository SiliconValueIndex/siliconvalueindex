import json
from datetime import UTC, datetime

import pandas as pd
import pytest

from svi import build, cli, prices
from svi.config import SITE_DATA_DIR, get_config
from svi.ids import Resolver
from svi.scrapers import mock

NOW = datetime(2026, 9, 29, tzinfo=UTC)


def one_gpu(gpu_id="nvidia-rtx-5070"):
    return build.select_gpus(build.load_registry(), [gpu_id])


def test_mock_runs_fixture_through_bestbuy_normalizer():
    cfg = get_config()
    obs, unresolved = mock.scrape_prices(
        Resolver.from_files(), one_gpu(), cfg, run_id="test", now=NOW
    )
    obs = prices.validate_observations(obs, prices.load_history(), cfg.pricing, now=NOW)
    assert set(obs["retailer"]) == {"mock"}
    assert set(obs["gpu_id"]) == {"nvidia-rtx-5070"}
    # The bundle is dropped before it becomes an observation.
    assert not obs["title_raw"].str.contains("Bundle").any()
    reasons = dict(zip(obs["sku"], obs["invalid_reason"], strict=True))
    assert reasons == {
        "9000001": "",
        "9000002": "",
        "9000003": "not_new",
        "9000004": "not_in_stock",
    }
    assert obs.loc[obs["is_valid"], "price"].min() == 579.99
    assert unresolved == []


def test_mock_search_requires_every_word():
    fetch = mock.fixture_fetch(mock.load_products())
    names = [p["name"] for p in fetch("search=GeForce&search=RTX&search=5070", "", "")]
    assert names and all("RTX 5070" in n for n in names)
    assert fetch("search=GeForce&search=RTX&search=9999", "", "") == []


def test_select_gpus_filters_and_rejects_unknown_ids():
    registry = build.load_registry()
    assert len(build.select_gpus(registry, None)) == (registry["is_active"] == "true").sum()
    assert list(build.select_gpus(registry, ["amd-rx-9070-xt"])["gpu_id"]) == ["amd-rx-9070-xt"]
    with pytest.raises(ValueError, match="nope"):
        build.select_gpus(registry, ["nope"])


def test_build_cli_passes_gpu_ids(monkeypatch):
    calls = []
    monkeypatch.setattr(build, "run_build", lambda **kwargs: calls.append(kwargs))
    assert cli.main(["build", "--gpu", "a", "--gpu", "b"]) == 0
    assert calls[0]["gpu_ids"] == ["a", "b"]


def test_duplicate_retailers_run_once():
    calls = []

    def adapter(resolver, registry, cfg, *, run_id, now):
        calls.append(1)
        return pd.DataFrame(columns=prices.PRICE_COLUMNS), []

    build.collect_retailer_prices(
        ["fake", "fake"],
        None,
        None,
        get_config(),
        pd.DataFrame(columns=prices.PRICE_COLUMNS),
        run_id="t",
        now=NOW,
        adapters={"fake": adapter},
        append=lambda obs: obs,
    )
    assert calls == [1]


# Guards: mock data must never reach the published site. The refresh workflow
# runs pytest before committing, so a leak blocks the commit.


def test_mock_is_never_a_scheduled_retailer():
    assert "mock" not in get_config().pricing.retailers


def test_committed_history_has_no_mock_prices():
    history = prices.load_history()
    assert not (history["retailer"] == "mock").any(), "run `git restore data/` after a mock build"


def test_committed_site_data_has_no_mock_prices():
    gpus = json.loads((SITE_DATA_DIR / "gpus.json").read_text(encoding="utf-8"))
    leaked = [g["gpu_id"] for g in gpus if (g.get("current_price") or {}).get("retailer") == "mock"]
    assert not leaked, "run `git restore data/` after a mock build"
