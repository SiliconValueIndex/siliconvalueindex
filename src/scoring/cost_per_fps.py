from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = REPO_ROOT / "data" / "processed" / "gpu_dataset.csv"
OUTPUT_DIR = REPO_ROOT / "outputs"


@dataclass(frozen=True)
class Columns:
    gpu: str = "gpu_model"
    fps: str = "normalized_fps_1440p"
    new_price: str = "new_price"
    used_price: str = "used_price"
    new_cpf: str = "new_cost_per_fps"
    used_cpf: str = "used_cost_per_fps"


def compute_cost_per_fps(df: pd.DataFrame) -> pd.DataFrame:
    c = Columns()
    out = df.copy()

    # Clean
    out[c.gpu] = out[c.gpu].astype(str).str.strip()
    out[c.fps] = pd.to_numeric(out.get(c.fps), errors="coerce")
    out[c.new_price] = pd.to_numeric(out.get(c.new_price), errors="coerce") if c.new_price in out.columns else pd.NA
    out[c.used_price] = pd.to_numeric(out.get(c.used_price), errors="coerce") if c.used_price in out.columns else pd.NA

    # Avoid divide-by-zero
    out.loc[out[c.fps] <= 0, c.fps] = pd.NA

    # Compute
    if c.new_price in out.columns:
        out[c.new_cpf] = out[c.new_price] / out[c.fps]

    if c.used_price in out.columns:
        out[c.used_cpf] = out[c.used_price] / out[c.fps]

    return out


def rank_and_export(df: pd.DataFrame) -> Path:
    c = Columns()

    ranked = df.copy()

    # Rank by new price if available; otherwise skip ranking
    if c.new_cpf in ranked.columns:
        ranked_new = ranked.dropna(subset=[c.new_cpf]).sort_values(c.new_cpf).reset_index(drop=True)
        ranked_new.insert(0, "rank_new_value", range(1, len(ranked_new) + 1))
    else:
        ranked_new = ranked

    # Keep a tidy set of columns if present
    keep = [col for col in [
        "rank_new_value",
        c.gpu,
        "benchmark_group" if "benchmark_group" in ranked_new.columns else None,
        c.fps,
        c.new_price if c.new_price in ranked_new.columns else None,
        c.new_cpf if c.new_cpf in ranked_new.columns else None,
        c.used_price if c.used_price in ranked_new.columns else None,
        c.used_cpf if c.used_cpf in ranked_new.columns else None,
        "source" if "source" in ranked_new.columns else None,
    ] if col is not None]

    ranked_new = ranked_new[keep]

    # Round for readability
    if c.fps in ranked_new.columns:
        ranked_new[c.fps] = ranked_new[c.fps].round(1)
    if c.new_cpf in ranked_new.columns:
        ranked_new[c.new_cpf] = ranked_new[c.new_cpf].round(3)
    if c.used_cpf in ranked_new.columns:
        ranked_new[c.used_cpf] = ranked_new[c.used_cpf].round(3)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"gpu_rankings_new_{date.today().isoformat()}.csv"
    ranked_new.to_csv(out_path, index=False)
    return out_path


def main() -> None:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"Missing input dataset: {INPUT_PATH}")

    df = pd.read_csv(INPUT_PATH)
    scored = compute_cost_per_fps(df)
    out_path = rank_and_export(scored)

    print(f"Loaded: {INPUT_PATH} ({len(df)} rows)")
    print(f"Wrote:  {out_path}")

    # Quick sanity output
    if "new_cost_per_fps" in scored.columns:
        preview = scored.dropna(subset=["new_cost_per_fps"]).sort_values("new_cost_per_fps").head(5)
        print("\nTop 5 by new cost-per-FPS:")
        print(preview[["gpu_model", "normalized_fps_1440p", "new_price", "new_cost_per_fps"]].to_string(index=False))


if __name__ == "__main__":
    main()