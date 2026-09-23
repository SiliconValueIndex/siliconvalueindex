from datetime import UTC, datetime
from types import SimpleNamespace

import pandas as pd
import pytest
import requests

from svi import build, cli, prices
from svi.config import get_config
from svi.models import UnresolvedName
from svi.scrapers import bestbuy, retailers

NOW = datetime(2026, 9, 22, tzinfo=UTC)


def observations(price=500):
    return pd.DataFrame(
        [
            dict(
                gpu_id="gpu-1",
                retailer="bestbuy",
                sku="1",
                title_raw="Test GPU",
                price=price,
                currency="USD",
                url="",
                condition="new",
                in_stock=True,
                is_valid=True,
                invalid_reason="",
                fetched_at=NOW,
                run_id="test",
            )
        ],
        columns=prices.PRICE_COLUMNS,
    )


def failing(exc):
    def adapter(*args, **kwargs):
        raise exc

    return adapter


def collect(adapters, append, names=None, history=None):
    return build.collect_retailer_prices(
        list(adapters) if names is None else names,
        None,
        pd.DataFrame(),
        get_config(),
        pd.DataFrame(columns=prices.PRICE_COLUMNS) if history is None else history,
        run_id="test",
        now=NOW,
        adapters=adapters,
        append=append,
    )


def test_registry():
    assert retailers.get_adapter("bestbuy") is retailers.ADAPTERS["bestbuy"]
    assert "manual" not in retailers.ADAPTERS
    with pytest.raises(KeyError, match="unknown retailer"):
        retailers.get_adapter("missing")


def test_collection_continues_and_tracks_only_success():
    appended = []
    unresolved = UnresolvedName(source="test", raw_name="Unknown GPU", canonical="unknown")

    def append(obs):
        appended.append(obs)
        return obs

    result = collect(
        {
            "bad": failing(RuntimeError("failed")),
            "bestbuy": failing(retailers.RetailerSkipped("no key")),
            "good": lambda *a, **kw: (observations(), [unresolved]),
        },
        append,
        names=["manual", "missing", "bad", "bestbuy", "good"],
    )
    assert result.fetch_failures == ["missing: unknown retailer", "bad: failed"]
    assert result.notes == ["Best Buy skipped: no key", "good: 1 valid of 1 observations"]
    assert result.source_fetched == {"good": "2026-09-22T00:00:00Z"}
    assert result.unresolved == [unresolved.model_dump()]
    assert len(appended) == 1
    assert result.history is appended[0]


def test_validation_uses_history_before_append():
    appended = []

    def append(obs):
        appended.append(obs)
        return obs

    result = collect(
        {"bestbuy": lambda *a, **kw: (observations(1), [])},
        append,
        history=observations(500),
    )
    assert not appended[0].iloc[0].is_valid
    assert appended[0].iloc[0].invalid_reason == "price_below_floor"
    assert result.notes == ["Best Buy: 0 valid of 1 observations"]


@pytest.fixture
def check_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    registry = pd.DataFrame(
        {
            "gpu_id": ["inactive", "gpu-1", "gpu-2", "gpu-3", "gpu-4"],
            "is_active": ["false", "true", "true", "true", "true"],
        }
    )
    monkeypatch.setattr(build, "load_registry", lambda: registry)
    from svi.ids import Resolver

    monkeypatch.setattr(Resolver, "from_files", lambda: None)
    monkeypatch.setattr(prices, "load_history", lambda: observations(500))

    def no_write(*args, **kwargs):
        pytest.fail("prices-check attempted a write")

    monkeypatch.setattr(prices, "append_history", no_write)
    monkeypatch.setattr(build, "append_history", no_write)
    monkeypatch.setattr(build, "write_site", no_write)
    yield tmp_path
    assert list(tmp_path.iterdir()) == []


def test_prices_check_unknown_retailer(monkeypatch, capsys, check_env):
    monkeypatch.setattr(retailers, "ADAPTERS", {})
    assert cli.main(["prices-check", "--retailer", "nope"]) == 1
    assert capsys.readouterr().out == "nope: unknown retailer\n"


def test_prices_check_rows_and_limit(monkeypatch, capsys, check_env):
    def adapter(resolver, registry, cfg, *, run_id, now):
        assert registry.gpu_id.tolist() == ["gpu-1", "gpu-2"]
        return observations(0), [
            UnresolvedName(source="test", raw_name="Unmatched title", canonical="unmatched")
        ]

    monkeypatch.setattr(retailers, "ADAPTERS", {"fake": adapter})
    assert cli.main(["prices-check", "--retailer", "fake", "--limit", "2"]) == 0
    output = capsys.readouterr().out
    for value in [
        "gpu-1",
        "bestbuy",
        "Test GPU",
        "no_price",
        "Unmatched title",
        "0 valid of 1 observations",
        "in_stock",
        "condition",
        "is_valid",
    ]:
        assert value in output


def test_prices_check_empty_default_limit(monkeypatch, capsys, check_env):
    def adapter(resolver, registry, cfg, **kwargs):
        assert registry.gpu_id.tolist() == ["gpu-1", "gpu-2", "gpu-3"]
        return pd.DataFrame(columns=prices.PRICE_COLUMNS), []

    monkeypatch.setattr(retailers, "ADAPTERS", {"fake": adapter})
    assert cli.main(["prices-check", "--retailer", "fake"]) == 0
    assert "0 valid of 0 observations" in capsys.readouterr().out


@pytest.mark.parametrize(
    "exc,code",
    [
        (retailers.RetailerSkipped("skip DUMMYKEY123"), 2),
        (RuntimeError("error DUMMYKEY123"), 1),
    ],
)
def test_error_redaction(monkeypatch, capsys, check_env, exc, code):
    monkeypatch.setenv("BESTBUY_API_KEY", "DUMMYKEY123")
    adapters = {"bestbuy": failing(exc)}
    monkeypatch.setattr(retailers, "ADAPTERS", adapters)
    assert cli.main(["prices-check", "--retailer", "bestbuy"]) == code
    output = capsys.readouterr().out
    result = collect(adapters, lambda obs: pytest.fail("unexpected append"))
    assert "DUMMYKEY123" not in output + str(result)
    assert "***" in output
    if code == 2:
        assert result.fetch_failures == []
        assert result.notes == ["Best Buy skipped: skip ***"]
    else:
        assert result.fetch_failures == ["bestbuy: error ***"]
    assert result.source_fetched == {}


@pytest.mark.parametrize("status", [None, 403, 500])
def test_fetch_errors_stay_safe_through_collection_and_cli(monkeypatch, capsys, check_env, status):
    monkeypatch.setenv("BESTBUY_API_KEY", "DUMMYKEY123")
    monkeypatch.setattr(bestbuy.time, "sleep", lambda _: None)

    def get(*args, **kwargs):
        if status is None:
            raise requests.ConnectionError("https://example.test/?apiKey=DUMMYKEY123")
        return SimpleNamespace(status_code=status, text="DUMMYKEY123")

    monkeypatch.setattr(bestbuy.requests, "get", get)

    def adapter(*args, **kwargs):
        bestbuy.fetch_products("secret query", "category", "DUMMYKEY123")

    with pytest.raises(bestbuy.BestBuyError) as caught:
        adapter()
    assert "DUMMYKEY123" not in str(caught.value)
    assert "secret query" not in str(caught.value)
    adapters = {"bestbuy": adapter}
    result = collect(adapters, lambda obs: pytest.fail("unexpected append"))
    assert result.fetch_failures
    assert "DUMMYKEY123" not in str(result.fetch_failures)
    monkeypatch.setattr(retailers, "ADAPTERS", adapters)
    assert cli.main(["prices-check", "--retailer", "bestbuy"]) == 1
    assert "DUMMYKEY123" not in capsys.readouterr().out


def test_build_cli_retailer_override(monkeypatch):
    calls = []
    monkeypatch.setattr(build, "run_build", lambda **kwargs: calls.append(kwargs))
    assert cli.main(["build", "--retailers", "bestbuy,other", "--skip-prices"]) == 0
    assert calls[0]["retailers"] == ["bestbuy", "other"]
    assert calls[0]["skip_prices"] is True
    assert cli.main(["build"]) == 0
    assert calls[1]["retailers"] is None


@pytest.mark.parametrize("override", [None, ["other"], []])
def test_run_build_selects_config_or_override(monkeypatch, tmp_path, override):
    from svi.ids import Resolver

    cfg = get_config()
    monkeypatch.setattr(build, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(
        build, "load_registry", lambda: pd.DataFrame({"gpu_id": ["gpu-1"], "is_active": ["true"]})
    )
    monkeypatch.setattr(Resolver, "from_files", lambda: None)
    monkeypatch.setattr(build, "load_benchmarks", pd.DataFrame)
    monkeypatch.setattr(build, "load_history", pd.DataFrame)

    class Collected(Exception):
        pass

    def collect_selected(names, *args, **kwargs):
        assert names == (cfg.pricing.retailers if override is None else override)
        raise Collected

    monkeypatch.setattr(build, "collect_retailer_prices", collect_selected)
    with pytest.raises(Collected):
        build.run_build(offline=False, skip_benchmarks=True, retailers=override, cfg=cfg)
