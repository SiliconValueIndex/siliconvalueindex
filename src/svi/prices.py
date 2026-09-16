"""Price history handling: validation of new observations and current-price selection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from svi.config import PROCESSED_DIR, REFERENCE_DIR, PricingConfig

PRICES_HISTORY_PATH = PROCESSED_DIR / "prices_history.csv"
PRICE_OVERRIDES_PATH = REFERENCE_DIR / "price_overrides.csv"

PRICE_COLUMNS = [
    "gpu_id",
    "retailer",
    "sku",
    "title_raw",
    "price",
    "currency",
    "url",
    "condition",
    "in_stock",
    "is_valid",
    "invalid_reason",
    "fetched_at",
    "run_id",
]


def load_history(path=PRICES_HISTORY_PATH) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=PRICE_COLUMNS)
    df = pd.read_csv(path, dtype={"sku": str, "invalid_reason": str, "url": str, "title_raw": str})
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True)
    for col in ("in_stock", "is_valid"):
        df[col] = df[col].astype(str).str.lower().isin(["true", "1", "yes"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    return df.fillna({"sku": "", "invalid_reason": "", "url": "", "title_raw": ""})


def append_history(new_rows: pd.DataFrame, path=PRICES_HISTORY_PATH) -> pd.DataFrame:
    history = load_history(path)
    combined = pd.concat([history, new_rows[PRICE_COLUMNS]], ignore_index=True)
    combined = combined.drop_duplicates(subset=["gpu_id", "retailer", "sku", "fetched_at", "price"])
    combined = combined.sort_values(["fetched_at", "gpu_id"]).reset_index(drop=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = combined.copy()
    out["fetched_at"] = out["fetched_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.to_csv(path, index=False, lineterminator="\n")
    return combined


def validate_observations(
    obs: pd.DataFrame, history: pd.DataFrame, cfg: PricingConfig, now: datetime | None = None
) -> pd.DataFrame:
    """Set is_valid/invalid_reason on fresh observations using stock, condition and a
    sanity band around each GPU's trailing 90-day median price."""
    now = now or datetime.now(UTC)
    out = obs.copy()
    out["is_valid"] = True
    out["invalid_reason"] = ""

    def flag(mask: pd.Series, reason: str) -> None:
        sel = mask & out["is_valid"]
        out.loc[sel, "is_valid"] = False
        out.loc[sel, "invalid_reason"] = reason

    flag(out["price"].isna() | (out["price"] <= 0), "no_price")
    flag(~out["in_stock"].astype(bool), "not_in_stock")
    flag(out["condition"] != "new", "not_new")

    if not history.empty:
        recent = history[history["is_valid"] & (history["fetched_at"] >= now - timedelta(days=90))]
        med = recent.groupby("gpu_id")["price"].median().rename("median_90d")
        out = out.merge(med, on="gpu_id", how="left")
        flag(out["price"] < out["median_90d"] * cfg.price_floor_ratio, "price_below_floor")
        flag(out["price"] > out["median_90d"] * cfg.price_ceiling_ratio, "price_above_ceiling")
        out = out.drop(columns=["median_90d"])
    return out


def load_overrides(path=PRICE_OVERRIDES_PATH, now: datetime | None = None) -> pd.DataFrame:
    """Manual prices for cards the APIs miss. Columns: gpu_id, price, url, retailer, note, valid_until."""
    if not path.exists():
        return pd.DataFrame(columns=PRICE_COLUMNS)
    now = now or datetime.now(UTC)
    ov = pd.read_csv(path, dtype=str).fillna("")
    ov = ov[ov["gpu_id"] != ""]
    if ov.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    valid_until = pd.to_datetime(ov["valid_until"].replace("", None), utc=True, errors="coerce")
    ov = ov[valid_until.isna() | (valid_until >= now)]
    rows = pd.DataFrame(
        {
            "gpu_id": ov["gpu_id"],
            "retailer": ov["retailer"].replace("", "manual"),
            "sku": "",
            "title_raw": ov["note"],
            "price": pd.to_numeric(ov["price"], errors="coerce"),
            "currency": "USD",
            "url": ov["url"],
            "condition": "new",
            "in_stock": True,
            "is_valid": True,
            "invalid_reason": "",
            "fetched_at": now,
            "run_id": "override",
        }
    )
    return rows


def select_current_prices(
    history: pd.DataFrame, cfg: PricingConfig, now: datetime | None = None
) -> pd.DataFrame:
    """Lowest valid price per GPU from the most recent run-window, plus 90-day stats.

    Columns: gpu_id, price, retailer, url, condition, fetched_at, min_90d, median_90d, n_points
    """
    now = now or datetime.now(UTC)
    if history.empty:
        return pd.DataFrame(
            columns=[
                "gpu_id",
                "price",
                "retailer",
                "url",
                "condition",
                "fetched_at",
                "min_90d",
                "median_90d",
                "n_points",
            ]
        )
    valid = history[history["is_valid"] & history["price"].notna()]
    fresh = valid
    if cfg.enforce_stale:
        fresh = valid[valid["fetched_at"] >= now - timedelta(days=cfg.stale_days)]
    # For each GPU use only observations from its latest fetch day so an old low price
    # cannot outlive newer, higher observations.
    latest_day = fresh.groupby("gpu_id")["fetched_at"].transform("max").dt.floor("D")
    latest = fresh[fresh["fetched_at"].dt.floor("D") == latest_day]
    current = latest.sort_values(["gpu_id", "price"]).drop_duplicates("gpu_id", keep="first")
    current = current[["gpu_id", "price", "retailer", "url", "condition", "fetched_at"]]

    window = valid[valid["fetched_at"] >= now - timedelta(days=90)]
    stats = window.groupby("gpu_id")["price"].agg(
        min_90d="min", median_90d="median", n_points="count"
    )
    return current.merge(stats, on="gpu_id", how="left").reset_index(drop=True)


def daily_lows(history: pd.DataFrame) -> pd.DataFrame:
    """One lowest valid price per GPU per day for price-history charts."""
    if history.empty:
        return pd.DataFrame(columns=["gpu_id", "date", "price", "retailer"])
    valid = history[history["is_valid"] & history["price"].notna()].copy()
    valid["date"] = valid["fetched_at"].dt.strftime("%Y-%m-%d")
    lows = valid.sort_values(["gpu_id", "date", "price"]).drop_duplicates(["gpu_id", "date"])
    return lows[["gpu_id", "date", "price", "retailer"]].reset_index(drop=True)
