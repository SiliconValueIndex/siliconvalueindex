from __future__ import annotations
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
INPUT_PATH = REPO_ROOT / "data" / "processed" / "gpu_working_set.csv"
OUTPUT_PATH = REPO_ROOT / "data" / "processed" / "gpu_working_set_scored.csv"

def compute_cost_per_fps(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["avg_fps_1440p"] = pd.to_numeric(out["avg_fps_1440p"], errors="coerce")
    out["new_price"] = pd.to_numeric(out["new_price"], errors="coerce")
    out["used_price"] = pd.to_numeric(out["used_price"], errors="coerce")

    out["new_cost_per_fps"] = out["new_price"] / out["avg_fps_1440p"]
    out["used_cost_per_fps"] = out["used_price"] / out["avg_fps_1440p"]

    return out

def main() -> None:
    df = pd.read_csv(INPUT_PATH)
    scored = compute_cost_per_fps(df)
    scored.to_csv(OUTPUT_PATH, index=False)
    print(f"Wrote: {OUTPUT_PATH} ({len(scored)} rows)")

if __name__ == "__main__":
    main()