from __future__ import annotations

from pathlib import Path
import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[2]

MODERN_PATH = REPO_ROOT / "data" / "raw" / "benchmarks" / "toms_modern_2026_1440p.csv"
LEGACY_PATH = REPO_ROOT / "data" / "raw" / "benchmarks" / "toms_legacy_2022_1440p.csv"
OUT_PATH = REPO_ROOT / "data" / "processed" / "benchmarks_normalized.csv"


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["gpu_model"] = df["gpu_model"].astype(str).str.strip()
    df["raw_fps_1440p"] = pd.to_numeric(df["raw_fps_1440p"], errors="coerce")
    # Keep only rows with a GPU name and FPS
    df = df.dropna(subset=["gpu_model", "raw_fps_1440p"])
    return df


def compute_scale_factor(modern: pd.DataFrame, legacy: pd.DataFrame) -> float:
    overlap = sorted(set(modern["gpu_model"]).intersection(set(legacy["gpu_model"])))
    if len(overlap) < 3:
        raise ValueError(f"Not enough overlap GPUs to normalize safely (found {len(overlap)}).")

    m = modern[modern["gpu_model"].isin(overlap)][["gpu_model", "raw_fps_1440p"]].rename(
        columns={"raw_fps_1440p": "modern_fps"}
    )
    l = legacy[legacy["gpu_model"].isin(overlap)][["gpu_model", "raw_fps_1440p"]].rename(
        columns={"raw_fps_1440p": "legacy_fps"}
    )

    joined = m.merge(l, on="gpu_model", how="inner")
    joined["ratio"] = joined["modern_fps"] / joined["legacy_fps"]

    # Robust-ish: trim extreme ratios (top/bottom 10%) to reduce noise
    joined = joined.sort_values("ratio").reset_index(drop=True)
    n = len(joined)
    lo = int(n * 0.10)
    hi = int(n * 0.90)
    trimmed = joined.iloc[lo:hi] if hi > lo else joined

    scale = float(trimmed["ratio"].mean())
    return scale


def main() -> None:
    modern = _clean(pd.read_csv(MODERN_PATH))
    legacy = _clean(pd.read_csv(LEGACY_PATH))

    scale = compute_scale_factor(modern, legacy)
    print(f"Normalization scale factor (legacy → modern): {scale:.4f}")

    modern_out = modern.assign(
        benchmark_group="modern",
        normalized_fps_1440p=modern["raw_fps_1440p"].round(1),
        source=modern.get("source", pd.Series([""] * len(modern))),
        last_updated=modern.get("last_updated", pd.Series([""] * len(modern))),
    )

    legacy_out = legacy.assign(
        benchmark_group="legacy",
        normalized_fps_1440p=(legacy["raw_fps_1440p"] * scale).round(1),
        source=legacy.get("source", pd.Series([""] * len(legacy))),
        last_updated=legacy.get("last_updated", pd.Series([""] * len(legacy))),
    )

    out = pd.concat([modern_out, legacy_out], ignore_index=True)

    # Remove duplicates if a GPU exists in both: prefer modern row for normalized output
    out["priority"] = out["benchmark_group"].map({"modern": 0, "legacy": 1}).fillna(9)
    out = out.sort_values(["gpu_model", "priority"]).drop_duplicates(subset=["gpu_model"], keep="first")
    out = out.drop(columns=["priority"])

    out = out[["gpu_model", "benchmark_group", "raw_fps_1440p", "normalized_fps_1440p", "source", "last_updated"]]
    out = out.sort_values("gpu_model").reset_index(drop=True)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote: {OUT_PATH} ({len(out)} rows)")


if __name__ == "__main__":
    main()