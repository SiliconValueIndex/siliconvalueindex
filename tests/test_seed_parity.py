"""Milestone gate: the new pipeline, run on the seed CSVs with the original
ratio_trimmed method, must reproduce the live site's 1440p cost-per-FPS numbers."""

import json
from datetime import UTC
from pathlib import Path

import pytest

from svi.config import get_config
from svi.ids import Resolver
from svi.normalize.benchmarks import build_effective_benchmarks
from svi.prices import select_current_prices
from svi.scoring.cost_per_fps import score_view
from svi.seed import seed_benchmarks, seed_prices

GOLDEN = Path(__file__).parent / "golden" / "live_rankings_2026-03-06.json"


@pytest.fixture(scope="module")
def seeded():
    resolver = Resolver.from_files()
    bench, unres_b = seed_benchmarks(resolver)
    prices, unres_p = seed_prices(resolver)
    assert not unres_b, [u.raw_name for u in unres_b]
    assert not unres_p, [u.raw_name for u in unres_p]
    return resolver, bench, prices


def test_seed_row_counts(seeded):
    _, bench, prices = seeded
    assert (bench["suite_version"] == "2026-03").sum() == 34
    assert (bench["suite_version"] == "2022").sum() == 42
    assert len(prices) == 59
    assert prices["gpu_id"].is_unique


def test_ratio_trimmed_reproduces_live_rankings(seeded):
    resolver, bench, prices = seeded
    cfg = get_config()
    norm_cfg = cfg.normalization.model_copy(update={"method": "ratio_trimmed"})
    effective, transforms, _ = build_effective_benchmarks(bench, norm_cfg)
    assert len(transforms) == 1
    assert transforms[0].params["scale"] == pytest.approx(0.7037, abs=0.001)
    assert transforms[0].n_overlap == 17

    # Seed prices are dated 2026-03-06; evaluate "now" as of the seed so nothing is stale.
    from datetime import datetime

    now = datetime(2026, 3, 7, tzinfo=UTC)
    current = select_current_prices(
        prices.assign(fetched_at=prices["fetched_at"]), cfg.pricing, now=now
    )
    ranked, meta = score_view(effective, current, cfg.zones, resolution="1440p", mode="raster")
    assert meta["mode"] == "absolute"
    assert len(ranked) == 59

    golden = json.loads(GOLDEN.read_text())
    by_id = {resolver.resolve(r["gpu_model"]): r["cost_per_fps"] for r in golden["rows"]}
    got = dict(zip(ranked["gpu_id"], ranked["cost_per_fps"], strict=True))
    mismatches = {
        gid: (got.get(gid), exp)
        for gid, exp in by_id.items()
        if abs((got.get(gid) or 0) - exp) > 0.011
    }
    assert not mismatches, mismatches
    # Same order as the live chart (ties aside).
    assert list(ranked["gpu_id"])[:5] == [
        resolver.resolve(r["gpu_model"]) for r in golden["rows"][:5]
    ]


def test_linear_method_changes_only_legacy_cards(seeded):
    _, bench, _ = seeded
    cfg = get_config()
    ratio_eff, _, _ = build_effective_benchmarks(
        bench, cfg.normalization.model_copy(update={"method": "ratio_trimmed"})
    )
    lin_eff, transforms, anomalies = build_effective_benchmarks(
        bench, cfg.normalization.model_copy(update={"method": "linear"})
    )
    merged = ratio_eff.merge(lin_eff, on=["gpu_id", "resolution", "mode"], suffixes=("_r", "_l"))
    modern = merged[~merged["normalized_r"]]
    assert (modern["fps_r"] == modern["fps_l"]).all()
    t = transforms[0]
    assert t.method == "linear" and t.params["a"] > 0.8 and t.r2 > 0.9
    # The swapped 4070 Ti Super row is a known outlier and must be surfaced, not hidden.
    assert "nvidia-rtx-4070-ti-super" in t.dropped_outliers or any(
        a["gpu_id"] == "nvidia-rtx-4070-ti-super" for a in anomalies
    )
