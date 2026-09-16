"""Cost per FPS scoring and value zones, one ranking per (resolution, mode) view.

A view has a playability floor. Cards under it keep their numbers but get no value
zone, rank after every playable card, and do not feed the percentile thresholds.
"""

from __future__ import annotations

import pandas as pd

from svi.config import PlayabilityConfig, ZonesConfig, view_key

ZONE_LABELS = ("great", "fair", "poor", "unplayable")


def zone_thresholds(cost: pd.Series, mode: str, zones: ZonesConfig) -> tuple[float, float]:
    """Return (great_max, fair_max) for a view, from config or from the distribution."""
    if mode == "absolute":
        return zones.absolute.great_max, zones.absolute.fair_max
    clean = cost.dropna()
    if clean.empty:
        return zones.absolute.great_max, zones.absolute.fair_max
    return (
        float(round(clean.quantile(zones.percentile.great), 2)),
        float(round(clean.quantile(zones.percentile.fair), 2)),
    )


def assign_zone(cost: float, great_max: float, fair_max: float) -> str:
    if pd.isna(cost):
        return ""
    if cost < great_max:
        return "great"
    if cost < fair_max:
        return "fair"
    return "poor"


def compute_cost_per_fps(df: pd.DataFrame) -> pd.DataFrame:
    """Add cost_per_fps = price / fps. Non-positive prices or fps are treated as missing."""
    out = df.copy()
    out["fps"] = pd.to_numeric(out["fps"], errors="coerce")
    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    out.loc[out["price"] <= 0, "price"] = pd.NA
    out.loc[out["fps"] <= 0, "fps"] = pd.NA
    out["cost_per_fps"] = (out["price"] / out["fps"]).astype(float).round(3)
    return out


def score_view(
    effective: pd.DataFrame,
    prices: pd.DataFrame,
    zones: ZonesConfig,
    *,
    resolution: str,
    mode: str,
    playability: PlayabilityConfig | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Rank one view. `effective` is the normalized benchmark frame, `prices` has
    gpu_id and price (current valid price). Returns (ranked, zone_meta)."""
    view = view_key(resolution, mode)
    floor = (playability or PlayabilityConfig()).floor_for(view)
    bench = effective[(effective["resolution"] == resolution) & (effective["mode"] == mode)]
    merged = bench.merge(prices[["gpu_id", "price"]], on="gpu_id", how="left")
    scored = compute_cost_per_fps(merged)
    scored = scored.dropna(subset=["cost_per_fps"])
    scored["playable"] = scored["fps"] >= floor
    ranked = scored.sort_values(["playable", "cost_per_fps"], ascending=[False, True]).reset_index(
        drop=True
    )
    ranked.insert(0, "rank", range(1, len(ranked) + 1))

    zmode = zones.mode_for(view)
    great_max, fair_max = zone_thresholds(
        ranked.loc[ranked["playable"], "cost_per_fps"], zmode, zones
    )
    ranked["zone"] = [
        assign_zone(c, great_max, fair_max) if p else "unplayable"
        for c, p in zip(ranked["cost_per_fps"], ranked["playable"], strict=True)
    ]
    meta = {
        "view": view,
        "mode": zmode,
        "great_max": great_max,
        "fair_max": fair_max,
        "min_fps": floor,
    }
    return ranked, meta


def score_all_views(
    effective: pd.DataFrame,
    prices: pd.DataFrame,
    zones: ZonesConfig,
    views: list[str],
    playability: PlayabilityConfig | None = None,
) -> tuple[dict[str, pd.DataFrame], dict[str, dict]]:
    rankings: dict[str, pd.DataFrame] = {}
    meta: dict[str, dict] = {}
    for view in views:
        resolution, mode = view.rsplit("_", 1)
        ranked, m = score_view(
            effective, prices, zones, resolution=resolution, mode=mode, playability=playability
        )
        if ranked.empty:
            continue
        rankings[view] = ranked
        meta[view] = m
    return rankings, meta
