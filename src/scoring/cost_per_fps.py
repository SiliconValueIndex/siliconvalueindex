from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]

BENCHMARKS_PATH = REPO_ROOT / "data" / "processed" / "benchmarks_normalized.csv"
NEW_PRICES_PATH = REPO_ROOT / "data" / "processed" / "new_prices.csv"
OUTPUT_DIR = REPO_ROOT / "outputs"


@dataclass(frozen=True)
class Columns:
    gpu: str = "gpu_model"
    fps: str = "normalized_fps_1440p"
    new_price_raw: str = "Price"
    new_price: str = "new_price"
    new_cpf: str = "new_cost_per_fps"
    link: str = "Link"


def load_and_merge() -> pd.DataFrame:
    c = Columns()

    if not BENCHMARKS_PATH.exists():
        raise FileNotFoundError(f"Missing benchmark dataset: {BENCHMARKS_PATH}")

    if not NEW_PRICES_PATH.exists():
        raise FileNotFoundError(f"Missing new prices dataset: {NEW_PRICES_PATH}")

    benchmarks = pd.read_csv(BENCHMARKS_PATH)
    prices = pd.read_csv(NEW_PRICES_PATH)

    benchmarks[c.gpu] = benchmarks[c.gpu].astype(str).str.strip()
    prices[c.gpu] = prices[c.gpu].astype(str).str.strip()

    prices = prices.rename(columns={c.new_price_raw: c.new_price})

    merged = benchmarks.merge(
    prices[[c.gpu, c.new_price, c.link]],
    on=c.gpu,
    how="left"
    )

    return merged


def compute_cost_per_fps(df: pd.DataFrame) -> pd.DataFrame:
    c = Columns()
    out = df.copy()

    out[c.fps] = pd.to_numeric(out[c.fps], errors="coerce")
    out[c.new_price] = pd.to_numeric(out[c.new_price], errors="coerce")

    out.loc[out[c.new_price] <= 0, c.new_price] = pd.NA
    out[c.new_cpf] = out[c.new_price] / out[c.fps]

    return out


def rank_and_export(df: pd.DataFrame) -> Path:
    c = Columns()

    ranked = (
        df.dropna(subset=[c.new_cpf])
        .sort_values(c.new_cpf)
        .reset_index(drop=True)
    )

    ranked.insert(0, "rank_new_value", range(1, len(ranked) + 1))

    keep = [
    "rank_new_value",
    c.gpu,
    "benchmark_group",
    c.fps,
    c.new_price,
    c.new_cpf,
    c.link,
    "source",
    "last_updated",
    ]

    ranked = ranked[keep]

    ranked[c.fps] = ranked[c.fps].round(1)
    ranked[c.new_cpf] = ranked[c.new_cpf].round(3)
    ranked[c.new_price] = ranked[c.new_price].round(2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"gpu_rankings_new_{date.today().isoformat()}.csv"
    ranked.to_csv(out_path, index=False)

    return out_path


def main() -> None:
    merged = load_and_merge()
    scored = compute_cost_per_fps(merged)
    out_path = rank_and_export(scored)

    print(f"Loaded benchmarks: {BENCHMARKS_PATH}")
    print(f"Loaded prices:     {NEW_PRICES_PATH}")
    print(f"Wrote:             {out_path}")

    preview = (
        scored.dropna(subset=["new_cost_per_fps"])
        .sort_values("new_cost_per_fps")
        .head(10)
    )

    print("\nTop 10 by new cost-per-FPS:")
    print(
        preview[["gpu_model", "normalized_fps_1440p", "new_price", "new_cost_per_fps"]]
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()