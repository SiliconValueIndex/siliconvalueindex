from datetime import UTC, datetime

import pandas as pd
import pytest

from svi.config import get_config
from svi.normalize.benchmarks import SuiteTransform, apply_transform, fit_suite_transform
from svi.prices import select_current_prices, validate_observations
from svi.scoring.cost_per_fps import assign_zone, compute_cost_per_fps, score_view, zone_thresholds


def test_cost_per_fps_guards_bad_inputs():
    df = pd.DataFrame({"fps": [50.0, 0.0, 40.0, 10.0], "price": [500.0, 300.0, -5.0, None]})
    out = compute_cost_per_fps(df)
    assert out.loc[0, "cost_per_fps"] == 10.0
    assert out["cost_per_fps"].isna().tolist() == [False, True, True, True]


def test_zone_assignment_absolute_and_percentile():
    zones = get_config().zones
    assert assign_zone(7.99, 8, 12) == "great"
    assert assign_zone(8.0, 8, 12) == "fair"
    assert assign_zone(12.0, 8, 12) == "poor"
    cost = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
    g, f = zone_thresholds(cost, "percentile", zones)
    assert 3.0 < g < 5.0 and 6.0 < f < 8.0


def test_score_view_ranks_and_uses_view_zone_mode():
    cfg = get_config()
    eff = pd.DataFrame(
        {
            "gpu_id": ["a", "b", "c"],
            "resolution": ["1440p"] * 3,
            "mode": ["raster"] * 3,
            "fps": [100.0, 50.0, 25.0],
            "raw_fps": [100.0, 50.0, 25.0],
            "suite_version": ["s"] * 3,
            "normalized": [False, True, False],
            "pct_of_top": [100.0, 50.0, 25.0],
        }
    )
    prices = pd.DataFrame({"gpu_id": ["a", "b", "c"], "price": [500.0, 500.0, None]})
    ranked, meta = score_view(eff, prices, cfg.zones, resolution="1440p", mode="raster")
    assert ranked["gpu_id"].tolist() == ["a", "b"]  # c has no price -> excluded
    assert ranked["rank"].tolist() == [1, 2]
    assert ranked["zone"].tolist() == ["great", "fair"]
    assert meta["mode"] == "absolute"


def _overlap():
    legacy = pd.Series([40, 60, 80, 100, 120, 140], dtype=float)
    current = 0.9 * legacy - 10
    df = pd.DataFrame({"gpu_id": list("abcdef"), "legacy_fps": legacy, "current_fps": current})
    return df


def test_linear_fit_recovers_line_and_drops_outlier():
    cfg = get_config().normalization
    df = _overlap()
    df.loc[2, "current_fps"] = 200  # corrupt one row
    t = fit_suite_transform(
        df, cfg, resolution="1440p", mode="raster", from_suite="x", to_suite="y", method="linear"
    )
    assert t.dropped_outliers == ["c"]
    assert t.params["a"] == pytest.approx(0.9, abs=1e-6)
    assert t.params["b"] == pytest.approx(-10, abs=1e-6)
    out = apply_transform(t, pd.Series([50.0]), cfg)
    assert out.iloc[0] == pytest.approx(35.0, abs=0.1)


def test_linear_extrapolation_guard_uses_endpoint_ratio():
    cfg = get_config().normalization
    t = SuiteTransform(
        "1440p", "raster", "x", "y", "linear", {"a": 0.9, "b": -10}, legacy_min=40, legacy_max=140
    )
    # Far below the fitted range the line would give a tiny/negative value; the guard
    # applies the ratio observed at the low endpoint (0.9*40-10)/40 = 0.65 instead.
    out = apply_transform(t, pd.Series([10.0]), cfg)
    assert out.iloc[0] == pytest.approx(6.5, abs=0.1)


def test_ratio_trimmed_matches_original_algorithm():
    cfg = get_config().normalization
    df = _overlap()
    t = fit_suite_transform(
        df,
        cfg,
        resolution="1440p",
        mode="raster",
        from_suite="x",
        to_suite="y",
        method="ratio_trimmed",
    )
    ratios = (df["current_fps"] / df["legacy_fps"]).sort_values()
    n = len(ratios)
    expected = ratios.iloc[int(n * 0.1) : int(n * 0.9)].mean()
    assert t.params["scale"] == pytest.approx(expected)


def _hist(rows):
    df = pd.DataFrame(rows, columns=["gpu_id", "retailer", "price", "is_valid", "fetched_at"])
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True)
    df["url"] = ""
    df["condition"] = "new"
    return df


def test_select_current_prices_uses_latest_day_lowest_valid():
    cfg = get_config().pricing
    now = datetime(2026, 9, 16, tzinfo=UTC)
    hist = _hist(
        [
            ("g", "bestbuy", 400, True, "2026-09-01"),
            ("g", "bestbuy", 450, True, "2026-09-15"),
            ("g", "manual", 430, True, "2026-09-15"),
            ("g", "bestbuy", 100, False, "2026-09-15"),  # invalid, ignored
        ]
    )
    cur = select_current_prices(hist, cfg, now=now)
    assert cur.loc[0, "price"] == 430 and cur.loc[0, "retailer"] == "manual"
    assert cur.loc[0, "min_90d"] == 400 and cur.loc[0, "n_points"] == 3


def test_validate_observations_flags_band_and_stock():
    cfg = get_config().pricing
    now = datetime(2026, 9, 16, tzinfo=UTC)
    hist = _hist(
        [("g", "bestbuy", 500, True, "2026-09-01"), ("g", "bestbuy", 520, True, "2026-09-08")]
    )
    obs = pd.DataFrame(
        {
            "gpu_id": ["g", "g", "g", "g"],
            "price": [510.0, 90.0, 2000.0, 505.0],
            "in_stock": [True, True, True, False],
            "condition": ["new", "new", "new", "new"],
        }
    )
    out = validate_observations(obs, hist, cfg, now=now)
    assert out["invalid_reason"].tolist() == [
        "",
        "price_below_floor",
        "price_above_ceiling",
        "not_in_stock",
    ]
