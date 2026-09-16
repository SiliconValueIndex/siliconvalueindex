"""Write the JSON files the Astro site consumes, validated against the schemas."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from jsonschema import Draft202012Validator

from svi.config import SITE_DATA_DIR, Config, split_view
from svi.export.schemas import SCHEMAS
from svi.normalize.benchmarks import SuiteTransform

VENDOR_PREFIX = {"NVIDIA": "GeForce", "AMD": "Radeon", "Intel": "Intel"}


def _clean(v):
    """Make pandas/numpy scalars JSON-safe; NaN becomes None."""
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if hasattr(v, "item"):
        v = v.item()
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(v, datetime):
        return v.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return v


def _int_or_none(v):
    v = _clean(v)
    if v is None or v == "":
        return None
    return int(float(v))


def retailer_links(vendor: str, display_name: str) -> dict[str, str]:
    q = quote_plus(f"{VENDOR_PREFIX.get(vendor, '')} {display_name}".strip())
    return {
        "newegg": f"https://www.newegg.com/p/pl?d={q}&N=100007709",
        "amazon": f"https://www.amazon.com/s?k={q}&i=computers",
        "bestbuy": f"https://www.bestbuy.com/site/searchpage.jsp?st={q}",
    }


@dataclass
class BuildContext:
    cfg: Config
    run_id: str
    generated_at: datetime
    registry: pd.DataFrame
    effective: pd.DataFrame
    transforms: list[SuiteTransform]
    rankings: dict[str, pd.DataFrame]
    zone_meta: dict[str, dict]
    current_prices: pd.DataFrame
    daily_lows: pd.DataFrame
    anomalies: list[dict] = field(default_factory=list)
    unresolved: list[dict] = field(default_factory=list)
    source_fetched: dict[str, str | None] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def build_gpus(ctx: BuildContext) -> list[dict]:
    bench_by_gpu: dict[str, dict] = {}
    for r in ctx.effective.itertuples(index=False):
        bench_by_gpu.setdefault(r.gpu_id, {}).setdefault(r.resolution, {})[r.mode] = {
            "fps": float(r.fps),
            "raw_fps": float(r.raw_fps),
            "pct_of_top": _clean(r.pct_of_top),
            "suite_version": str(r.suite_version),
            "normalized": bool(r.normalized),
        }
    rank_by_gpu: dict[str, dict] = {}
    for view, df in ctx.rankings.items():
        for r in df.itertuples(index=False):
            rank_by_gpu.setdefault(r.gpu_id, {})[view] = {
                "rank": int(r.rank),
                "cost_per_fps": float(r.cost_per_fps),
                "zone": str(r.zone),
            }
    price_by_gpu = {r.gpu_id: r for r in ctx.current_prices.itertuples(index=False)}

    gpus = []
    for r in ctx.registry.itertuples(index=False):
        p = price_by_gpu.get(r.gpu_id)
        current_price = (
            {
                "price": float(p.price),
                "retailer": str(p.retailer),
                "url": str(p.url) if isinstance(p.url, str) else "",
                "condition": str(p.condition),
                "fetched_at": _clean(p.fetched_at),
            }
            if p is not None
            else None
        )
        price_stats = {
            "min_90d": _clean(getattr(p, "min_90d", None)) if p is not None else None,
            "median_90d": _clean(getattr(p, "median_90d", None)) if p is not None else None,
            "n_points": int(_clean(getattr(p, "n_points", 0)) or 0) if p is not None else 0,
        }
        gpus.append(
            {
                "gpu_id": r.gpu_id,
                "component_type": str(getattr(r, "component_type", "gpu")),
                "vendor": r.vendor,
                "architecture": r.architecture,
                "series": r.series,
                "display_name": r.display_name,
                "release_year": int(r.release_year),
                "msrp_usd": _clean(r.msrp_usd) if str(_clean(r.msrp_usd) or "") != "" else None,
                "tdp_w": _int_or_none(r.tdp_w),
                "vram_gb": _int_or_none(r.vram_gb),
                "is_active": str(r.is_active).lower() in ("true", "1", "yes"),
                "benchmarks": bench_by_gpu.get(r.gpu_id, {}),
                "rankings": rank_by_gpu.get(r.gpu_id, {}),
                "current_price": current_price,
                "retailer_links": retailer_links(r.vendor, r.display_name),
                "price_stats": price_stats,
            }
        )
    return gpus


def build_rankings(ctx: BuildContext) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for view, df in ctx.rankings.items():
        out[view] = [
            {
                "gpu_id": r.gpu_id,
                "rank": int(r.rank),
                "fps": float(r.fps),
                "price": float(r.price),
                "cost_per_fps": float(r.cost_per_fps),
                "zone": str(r.zone),
                "normalized": bool(r.normalized),
            }
            for r in df.itertuples(index=False)
        ]
    return out


def build_price_history(ctx: BuildContext) -> dict[str, list]:
    hist: dict[str, list] = {}
    for r in ctx.daily_lows.itertuples(index=False):
        hist.setdefault(r.gpu_id, []).append([str(r.date), float(r.price), str(r.retailer)])
    return hist


def build_manifest(
    ctx: BuildContext, gpus: list[dict], rankings: dict[str, list[dict]], needs_review: bool
) -> dict:
    cfg = ctx.cfg
    suites: dict[str, str] = {}
    for view in rankings:
        resolution, mode = split_view(view)
        sub = ctx.effective[
            (ctx.effective["resolution"] == resolution)
            & (ctx.effective["mode"] == mode)
            & (~ctx.effective["normalized"])
        ]
        if not sub.empty:
            suites[view] = str(sub["suite_version"].iloc[0])
    zones = {
        view: {
            "mode": m["mode"],
            "great_max": float(m["great_max"]),
            "fair_max": float(m["fair_max"]),
        }
        for view, m in ctx.zone_meta.items()
        if view in rankings
    }
    return {
        "generated_at": _clean(ctx.generated_at),
        "run_id": ctx.run_id,
        "primary_view": cfg.benchmarks.primary_view,
        "views": list(rankings.keys()),
        "gpu_count": len(gpus),
        "ranked_counts": {v: len(rows) for v, rows in rankings.items()},
        "zones": zones,
        "normalization": {
            "method": cfg.normalization.method,
            "transforms": [t.to_dict() for t in ctx.transforms],
        },
        "benchmark_suites": suites,
        "sources": [
            {
                "name": "Tom's Hardware GPU Hierarchy",
                "url": cfg.benchmarks.current_url,
                "kind": "benchmarks",
                "fetched_at": ctx.source_fetched.get("toms"),
            },
            {
                "name": "Best Buy Products API",
                "url": "https://www.bestbuy.com",
                "kind": "prices",
                "fetched_at": ctx.source_fetched.get("bestbuy"),
            },
            {
                "name": "Manual price overrides",
                "url": cfg.project.repo_url + "/blob/main/data/reference/price_overrides.csv",
                "kind": "prices",
                "fetched_at": ctx.source_fetched.get("manual"),
            },
        ],
        "anomalies": ctx.anomalies,
        "unresolved": ctx.unresolved,
        "needs_review": needs_review,
    }


def _read_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_changelog_entry(
    ctx: BuildContext, gpus: list[dict], rankings: dict[str, list[dict]], previous_dir: Path
) -> dict:
    prev_gpus = _read_json(previous_dir / "gpus.json") or []
    prev_manifest = _read_json(previous_dir / "manifest.json") or {}
    prev_ids = {g["gpu_id"] for g in prev_gpus}
    new_ids = {g["gpu_id"] for g in gpus}
    prev_price = {g["gpu_id"]: (g.get("current_price") or {}).get("price") for g in prev_gpus}
    changes = []
    for g in gpus:
        old = prev_price.get(g["gpu_id"])
        new = (g.get("current_price") or {}).get("price")
        if old and new and abs(new - old) / old * 100 >= 5:
            changes.append(
                {
                    "gpu_id": g["gpu_id"],
                    "from": old,
                    "to": new,
                    "pct": round((new - old) / old * 100, 1),
                }
            )
    primary = ctx.cfg.benchmarks.primary_view
    prev_suite = (prev_manifest.get("benchmark_suites") or {}).get(primary)
    cur_suite = None
    if primary in rankings:
        sub = ctx.effective[(~ctx.effective["normalized"])]
        res, mode = split_view(primary)
        sub = sub[(sub["resolution"] == res) & (sub["mode"] == mode)]
        cur_suite = str(sub["suite_version"].iloc[0]) if not sub.empty else None
    return {
        "run_id": ctx.run_id,
        "generated_at": _clean(ctx.generated_at),
        "added_gpus": sorted(new_ids - prev_ids),
        "removed_gpus": sorted(prev_ids - new_ids),
        "price_changes": sorted(changes, key=lambda c: -abs(c["pct"])),
        "benchmark_suite_changed": bool(prev_suite and cur_suite and prev_suite != cur_suite),
        "unresolved_count": len(ctx.unresolved),
        "notes": ctx.notes,
    }


def validate(name: str, payload) -> None:
    errors = sorted(Draft202012Validator(SCHEMAS[name]).iter_errors(payload), key=lambda e: e.path)
    if errors:
        first = errors[0]
        raise ValueError(
            f"{name}.json failed schema: {list(first.path)}: {first.message} ({len(errors)} errors)"
        )


def guard_gpu_count(new_count: int, previous_dir: Path, max_drop_pct: float) -> None:
    prev = _read_json(previous_dir / "manifest.json")
    if not prev:
        return
    old = int(prev.get("gpu_count", 0))
    if old and new_count < old * (1 - max_drop_pct / 100):
        raise RuntimeError(
            f"Refusing to publish: gpu_count fell from {old} to {new_count} (> {max_drop_pct}% drop)"
        )


def write_site(ctx: BuildContext, needs_review: bool, out_dir: Path = SITE_DATA_DIR) -> dict:
    gpus = build_gpus(ctx)
    rankings = build_rankings(ctx)
    price_history = build_price_history(ctx)
    manifest = build_manifest(ctx, gpus, rankings, needs_review)
    entry = build_changelog_entry(ctx, gpus, rankings, out_dir)
    changelog = _read_json(out_dir / "changelog.json") or []
    changelog = [e for e in changelog if e.get("run_id") != ctx.run_id]
    changelog.insert(0, entry)
    changelog = changelog[:200]

    guard_gpu_count(len(gpus), out_dir, ctx.cfg.guards.max_gpu_count_drop_pct)
    for name, payload in (
        ("manifest", manifest),
        ("gpus", gpus),
        ("rankings", rankings),
        ("price_history", price_history),
        ("changelog", changelog),
    ):
        validate(name, payload)
    ranked_ids = {r["gpu_id"] for rows in rankings.values() for r in rows}
    known = {g["gpu_id"] for g in gpus}
    if not ranked_ids <= known:
        raise ValueError(f"rankings reference unknown gpu_ids: {sorted(ranked_ids - known)}")

    out_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("manifest", manifest),
        ("gpus", gpus),
        ("rankings", rankings),
        ("price_history", price_history),
        ("changelog", changelog),
    ):
        (out_dir / f"{name}.json").write_text(
            json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    return {
        "gpus": len(gpus),
        "views": {v: len(r) for v, r in rankings.items()},
        "changelog": entry,
    }
