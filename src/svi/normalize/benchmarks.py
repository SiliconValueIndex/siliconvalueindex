"""Cross-suite normalization of benchmark FPS.

Tom's Hardware re-benchmarks with a heavier game suite every couple of years. A card
that only exists in an older suite needs its FPS translated into the current suite's
scale before it can be compared. We fit that translation on the cards present in both.

Methods (config.normalization.method):
- ratio_trimmed: single trimmed-mean ratio current/legacy (the original 2026-03 method)
- linear:        robust OLS current = a * legacy + b after MAD outlier removal (default)
- piecewise:     tercile-binned median ratios, interpolated by legacy fps
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from svi.config import NormalizationConfig


@dataclass
class SuiteTransform:
    resolution: str
    mode: str
    from_suite: str
    to_suite: str
    method: str
    params: dict = field(default_factory=dict)
    overlap_ids: list[str] = field(default_factory=list)
    n_overlap: int = 0
    n_used: int = 0
    r2: float | None = None
    residual_sd: float | None = None
    legacy_min: float = 0.0
    legacy_max: float = 0.0
    dropped_outliers: list[str] = field(default_factory=list)
    overlap_points: list[list] = field(default_factory=list)  # [gpu_id, legacy, current]

    def to_dict(self) -> dict:
        return {
            "resolution": self.resolution,
            "mode": self.mode,
            "from_suite": self.from_suite,
            "to_suite": self.to_suite,
            "method": self.method,
            "params": {
                k: (round(v, 5) if isinstance(v, float) else v) for k, v in self.params.items()
            },
            "overlap_ids": self.overlap_ids,
            "n_overlap": self.n_overlap,
            "n_used": self.n_used,
            "r2": None if self.r2 is None else round(self.r2, 4),
            "residual_sd": None if self.residual_sd is None else round(self.residual_sd, 3),
            "legacy_range": [round(self.legacy_min, 1), round(self.legacy_max, 1)],
            "dropped_outliers": self.dropped_outliers,
            "overlap_points": self.overlap_points,
        }


def _mad_mask(values: np.ndarray, k: float) -> np.ndarray:
    """True for values within k robust standard deviations of the median."""
    med = np.median(values)
    mad = np.median(np.abs(values - med)) * 1.4826
    if mad == 0:
        return np.ones_like(values, dtype=bool)
    return np.abs(values - med) <= k * mad


def fit_suite_transform(
    overlap: pd.DataFrame,
    cfg: NormalizationConfig,
    *,
    resolution: str,
    mode: str,
    from_suite: str,
    to_suite: str,
    method: str | None = None,
) -> SuiteTransform:
    """Fit a transform on a frame with columns gpu_id, legacy_fps, current_fps."""
    method = method or cfg.method
    df = overlap.dropna(subset=["legacy_fps", "current_fps"]).copy()
    df = df[(df["legacy_fps"] > 0) & (df["current_fps"] > 0)]
    if len(df) < cfg.min_overlap:
        raise ValueError(
            f"Not enough overlap GPUs to normalize {resolution}/{mode} "
            f"({len(df)} < {cfg.min_overlap})"
        )
    df["ratio"] = df["current_fps"] / df["legacy_fps"]
    t = SuiteTransform(
        resolution=resolution,
        mode=mode,
        from_suite=from_suite,
        to_suite=to_suite,
        method=method,
        overlap_ids=sorted(df["gpu_id"]),
        n_overlap=len(df),
        legacy_min=float(df["legacy_fps"].min()),
        legacy_max=float(df["legacy_fps"].max()),
        overlap_points=[
            [g, float(lf), float(cf)]
            for g, lf, cf in zip(df["gpu_id"], df["legacy_fps"], df["current_fps"], strict=True)
        ],
    )

    if method == "ratio_trimmed":
        ordered = df.sort_values("ratio").reset_index(drop=True)
        n = len(ordered)
        lo, hi = int(n * cfg.trim_fraction), int(n * (1 - cfg.trim_fraction))
        trimmed = ordered.iloc[lo:hi] if hi > lo else ordered
        scale = float(trimmed["ratio"].mean())
        t.params = {"scale": scale}
        t.n_used = len(trimmed)
        t.dropped_outliers = sorted(set(ordered["gpu_id"]) - set(trimmed["gpu_id"]))
        pred = df["legacy_fps"] * scale
    elif method == "linear":
        # Fit once on everything, drop points whose residual is far outside the
        # robust spread, refit. Residual-based (not ratio-based) so a legitimate
        # intercept does not make high-end cards look like outliers.
        a0, b0 = np.polyfit(df["legacy_fps"], df["current_fps"], deg=1)
        resid0 = (df["current_fps"] - (a0 * df["legacy_fps"] + b0)).to_numpy()
        keep = _mad_mask(resid0, cfg.outlier_mad)
        used = df[keep]
        if len(used) < cfg.min_overlap:
            used = df
            keep = np.ones(len(df), dtype=bool)
        a, b = np.polyfit(used["legacy_fps"], used["current_fps"], deg=1)
        t.params = {"a": float(a), "b": float(b)}
        t.n_used = int(len(used))
        t.dropped_outliers = sorted(df.loc[~keep, "gpu_id"])
        pred = a * df["legacy_fps"] + b
    elif method == "piecewise":
        ordered = df.sort_values("legacy_fps").reset_index(drop=True)
        bins = np.array_split(ordered, 3)
        centers = [float(b["legacy_fps"].median()) for b in bins]
        ratios = [float(b["ratio"].median()) for b in bins]
        t.params = {"centers": centers, "ratios": ratios}
        t.n_used = len(df)
        pred = df["legacy_fps"] * np.interp(df["legacy_fps"], centers, ratios)
    else:
        raise ValueError(f"Unknown normalization method: {method}")

    resid = df["current_fps"] - pred
    ss_res = float((resid**2).sum())
    ss_tot = float(((df["current_fps"] - df["current_fps"].mean()) ** 2).sum())
    t.r2 = 1 - ss_res / ss_tot if ss_tot > 0 else None
    t.residual_sd = float(resid.std(ddof=1)) if len(resid) > 1 else None
    return t


def apply_transform(
    t: SuiteTransform, legacy_fps: pd.Series, cfg: NormalizationConfig
) -> pd.Series:
    """Translate legacy-suite fps into the current suite's scale."""
    x = legacy_fps.astype(float)
    if t.method == "ratio_trimmed":
        out = x * t.params["scale"]
    elif t.method == "linear":
        a, b = t.params["a"], t.params["b"]
        out = a * x + b
        # Outside the fitted range (plus tolerance) a line with an intercept can go
        # badly wrong, so fall back to the ratio observed at the nearest endpoint.
        span = t.legacy_max - t.legacy_min
        lo = t.legacy_min - cfg.max_extrapolation * span
        hi = t.legacy_max + cfg.max_extrapolation * span
        lo_ratio = (a * t.legacy_min + b) / t.legacy_min
        hi_ratio = (a * t.legacy_max + b) / t.legacy_max
        out = out.where(x >= lo, x * lo_ratio).where(x <= hi, x * hi_ratio)
    elif t.method == "piecewise":
        out = x * np.interp(x, t.params["centers"], t.params["ratios"])
    else:
        raise ValueError(t.method)
    return out.clip(lower=0.1).round(1)


def _suite_order(suites: pd.Series) -> list[str]:
    """Suite versions sort as ISO-ish strings: '2022' < '2026-03' < '2026-09-16'."""
    return sorted(suites.dropna().unique().tolist())


def build_effective_benchmarks(
    benchmarks: pd.DataFrame, cfg: NormalizationConfig
) -> tuple[pd.DataFrame, list[SuiteTransform], list[dict]]:
    """Collapse long-format observations to one effective fps per (gpu, resolution, mode).

    Returns (effective, transforms, anomalies). Effective columns:
    gpu_id, resolution, mode, fps, raw_fps, suite_version, normalized, pct_of_top
    """
    required = {"gpu_id", "suite_version", "resolution", "mode", "fps"}
    missing = required - set(benchmarks.columns)
    if missing:
        raise ValueError(f"benchmarks missing columns: {sorted(missing)}")

    out_frames: list[pd.DataFrame] = []
    transforms: list[SuiteTransform] = []
    anomalies: list[dict] = []

    for (resolution, mode), grp in benchmarks.groupby(["resolution", "mode"], sort=True):
        suites = _suite_order(grp["suite_version"])
        current = suites[-1]
        # Latest observation per gpu within each suite (a suite can be re-fetched).
        grp = grp.sort_values("fetched_at") if "fetched_at" in grp else grp
        latest = grp.drop_duplicates(subset=["gpu_id", "suite_version"], keep="last")
        cur = latest[latest["suite_version"] == current][["gpu_id", "fps"]].copy()
        cur = cur.rename(columns={"fps": "current_fps"})
        eff = cur.assign(
            fps=cur["current_fps"],
            raw_fps=cur["current_fps"],
            suite_version=current,
            normalized=False,
        )[["gpu_id", "fps", "raw_fps", "suite_version", "normalized"]]
        covered = set(eff["gpu_id"])

        for legacy_suite in reversed(suites[:-1]):
            leg = latest[latest["suite_version"] == legacy_suite][["gpu_id", "fps"]]
            leg = leg.rename(columns={"fps": "legacy_fps"})
            overlap = leg.merge(cur, on="gpu_id", how="inner")
            missing_rows = leg[~leg["gpu_id"].isin(covered)]
            if missing_rows.empty:
                continue
            t = fit_suite_transform(
                overlap,
                cfg,
                resolution=resolution,
                mode=mode,
                from_suite=legacy_suite,
                to_suite=current,
            )
            transforms.append(t)
            if t.residual_sd:
                pred = apply_transform(t, overlap["legacy_fps"], cfg)
                resid = overlap["current_fps"] - pred
                for gid, r in zip(overlap["gpu_id"], resid, strict=True):
                    if abs(r) > 2.5 * t.residual_sd:
                        anomalies.append(
                            {
                                "type": "overlap_residual",
                                "gpu_id": gid,
                                "resolution": resolution,
                                "mode": mode,
                                "residual": round(float(r), 1),
                                "detail": f"{legacy_suite}->{current} fit residual "
                                f"exceeds 2.5 sd ({t.residual_sd:.1f})",
                            }
                        )
            translated = missing_rows.assign(
                fps=apply_transform(t, missing_rows["legacy_fps"], cfg),
                raw_fps=missing_rows["legacy_fps"],
                suite_version=legacy_suite,
                normalized=True,
            )[["gpu_id", "fps", "raw_fps", "suite_version", "normalized"]]
            eff = pd.concat([eff, translated], ignore_index=True)
            covered |= set(translated["gpu_id"])

        eff["resolution"] = resolution
        eff["mode"] = mode
        top = eff["fps"].max()
        eff["pct_of_top"] = (eff["fps"] / top * 100).round(1) if top > 0 else np.nan
        out_frames.append(eff)

    effective = pd.concat(out_frames, ignore_index=True) if out_frames else pd.DataFrame()
    cols = [
        "gpu_id",
        "resolution",
        "mode",
        "fps",
        "raw_fps",
        "suite_version",
        "normalized",
        "pct_of_top",
    ]
    return (
        effective[cols]
        .sort_values(["resolution", "mode", "fps"], ascending=[True, True, False])
        .reset_index(drop=True),
        transforms,
        anomalies,
    )
