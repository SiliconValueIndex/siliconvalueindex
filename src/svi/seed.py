"""Convert the original hand-maintained CSVs into the new long-format tables.

Run once (svi seed). Idempotent: re-running rewrites the same rows.
- data/raw/benchmarks/toms_legacy_2022_1440p.csv  -> suite_version 2022
- data/raw/benchmarks/toms_modern_2026_1440p.csv  -> suite_version 2026-03
- data/raw/prices/newegg_manual_2026-03-06.csv   -> first prices_history snapshot
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from svi.config import PROCESSED_DIR, RAW_DIR
from svi.ids import Resolver
from svi.models import UnresolvedName
from svi.prices import PRICE_COLUMNS, PRICES_HISTORY_PATH

BENCHMARKS_PATH = PROCESSED_DIR / "benchmarks.csv"
BENCHMARK_COLUMNS = [
    "gpu_id",
    "component_type",
    "source",
    "suite_version",
    "resolution",
    "setting",
    "mode",
    "fps",
    "pct_of_top",
    "fetched_at",
    "snapshot_ref",
]

SEED_BENCHMARKS = [
    (RAW_DIR / "benchmarks" / "toms_legacy_2022_1440p.csv", "2022"),
    (RAW_DIR / "benchmarks" / "toms_modern_2026_1440p.csv", "2026-03"),
]
SEED_PRICES = RAW_DIR / "prices" / "newegg_manual_2026-03-06.csv"


def _to_utc(date_str: str) -> datetime:
    return datetime.fromisoformat(str(date_str)).replace(tzinfo=UTC)


def seed_benchmarks(resolver: Resolver) -> tuple[pd.DataFrame, list[UnresolvedName]]:
    rows: list[dict] = []
    unresolved: list[UnresolvedName] = []
    for path, suite in SEED_BENCHMARKS:
        raw = pd.read_csv(path)
        raw["gpu_model"] = raw["gpu_model"].astype(str).str.strip()
        raw["raw_fps_1440p"] = pd.to_numeric(raw["raw_fps_1440p"], errors="coerce")
        raw = raw.dropna(subset=["raw_fps_1440p"])
        for r in raw.itertuples(index=False):
            hit = resolver.resolve(r.gpu_model, source=f"seed:{path.name}")
            if isinstance(hit, UnresolvedName):
                unresolved.append(hit)
                continue
            rows.append(
                {
                    "gpu_id": hit,
                    "component_type": "gpu",
                    "source": "toms_gpu_hierarchy",
                    "suite_version": suite,
                    "resolution": "1440p",
                    "setting": "ultra",
                    "mode": "raster",
                    "fps": float(r.raw_fps_1440p),
                    "pct_of_top": None,
                    "fetched_at": _to_utc(r.last_updated),
                    "snapshot_ref": str(path.relative_to(path.parents[3])).replace("\\", "/"),
                }
            )
    df = pd.DataFrame(rows, columns=BENCHMARK_COLUMNS)
    for _suite, grp in df.groupby("suite_version"):
        top = grp["fps"].max()
        df.loc[grp.index, "pct_of_top"] = (grp["fps"] / top * 100).round(1)
    return df, unresolved


def seed_prices(resolver: Resolver) -> tuple[pd.DataFrame, list[UnresolvedName]]:
    raw = pd.read_csv(SEED_PRICES)
    raw = raw.rename(columns={"Price": "price", "Link": "url", "Last Updated": "last_updated"})
    raw["gpu_model"] = raw["gpu_model"].astype(str).str.strip()
    rows: list[dict] = []
    unresolved: list[UnresolvedName] = []
    for r in raw.itertuples(index=False):
        hit = resolver.resolve(r.gpu_model, source="seed:new_prices.csv")
        if isinstance(hit, UnresolvedName):
            unresolved.append(hit)
            continue
        price = float(r.price) if pd.notna(r.price) else None
        rows.append(
            {
                "gpu_id": hit,
                "retailer": "newegg",
                "sku": "",
                "title_raw": r.gpu_model,
                "price": price,
                "currency": "USD",
                "url": r.url if isinstance(r.url, str) else "",
                "condition": "new",
                "in_stock": True,
                "is_valid": price is not None and price > 0,
                "invalid_reason": "" if price and price > 0 else "no_price",
                "fetched_at": _to_utc(r.last_updated),
                "run_id": "seed-2026-03",
            }
        )
    return pd.DataFrame(rows, columns=PRICE_COLUMNS), unresolved


def write_benchmarks(df: pd.DataFrame, path: Path = BENCHMARKS_PATH) -> None:
    out = df.copy()
    out["fetched_at"] = pd.to_datetime(out["fetched_at"], utc=True).dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, lineterminator="\n")


def run_seed() -> dict:
    resolver = Resolver.from_files()
    bench, unres_b = seed_benchmarks(resolver)
    prices, unres_p = seed_prices(resolver)
    write_benchmarks(bench)
    out = prices.copy()
    out["fetched_at"] = pd.to_datetime(out["fetched_at"], utc=True).dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    PRICES_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.sort_values(["fetched_at", "gpu_id"]).to_csv(
        PRICES_HISTORY_PATH, index=False, lineterminator="\n"
    )
    return {
        "benchmark_rows": len(bench),
        "price_rows": len(prices),
        "unresolved": [u.model_dump() for u in unres_b + unres_p],
    }
