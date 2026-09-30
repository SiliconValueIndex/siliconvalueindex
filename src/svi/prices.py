"""Price history handling: validation of new observations and current-price selection."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

import pandas as pd

from svi.config import PROCESSED_DIR, REFERENCE_DIR, InputError, PricingConfig

PRICES_HISTORY_PATH = PROCESSED_DIR / "prices_history.csv"
PRICE_OVERRIDES_PATH = REFERENCE_DIR / "price_overrides.csv"

# run_id prefix for rows that came from price_overrides.csv, so a corrected
# manual price can replace the one entered earlier for the same card and date.
MANUAL_RUN_PREFIX = "manual-"
_ISO_DATE = "%Y-%m-%d"
_RETAILER_ID = re.compile(r"[a-z0-9]+")

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


def append_history(
    new_rows: pd.DataFrame, path=PRICES_HISTORY_PATH, *, replace_manual: bool = False
) -> pd.DataFrame:
    """Add observations to the append-only history and rewrite the CSV.

    replace_manual: drop earlier manual rows for the same (gpu_id, fetched_at)
    first. Without it, fixing a typo in the sheet on the same day would leave
    both prices in history and the lower, wrong one would win."""
    history = load_history(path)
    if replace_manual and not history.empty:
        key = ["gpu_id", "fetched_at"]
        new_keys = pd.MultiIndex.from_frame(
            new_rows[key].astype({"fetched_at": "datetime64[ns, UTC]"})
        )
        same_key = pd.MultiIndex.from_frame(history[key]).isin(new_keys)
        is_manual = history["run_id"].astype(str).str.startswith(MANUAL_RUN_PREFIX).to_numpy()
        history = history[~(is_manual & same_key)]
    combined = pd.concat([history, new_rows[PRICE_COLUMNS]], ignore_index=True)
    # An empty history has an object column; keep fetched_at datetime for sorting.
    combined["fetched_at"] = pd.to_datetime(combined["fetched_at"], utc=True)
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


def load_overrides(
    path=PRICE_OVERRIDES_PATH, now: datetime | None = None, run_id: str = ""
) -> pd.DataFrame:
    """Manual prices for cards the APIs miss.

    Columns: gpu_id, price, url, retailer, note, checked_on, valid_until.
    Rows without a price are skipped, so the sheet can be filled in gradually.
    checked_on is the date the price was seen; it becomes fetched_at so an old
    entry is not re-dated on every run (and re-runs do not duplicate history).

    Raises InputError listing every malformed row. Manual prices skip the
    automatic sanity checks, so a typo must stop the build rather than be
    silently dropped or published.
    """
    if not path.exists():
        return pd.DataFrame(columns=PRICE_COLUMNS)
    now = now or datetime.now(UTC)
    ov = pd.read_csv(path, dtype=str).fillna("")
    if "checked_on" not in ov:  # sheets written before the column existed
        ov["checked_on"] = ""
    ov = ov[(ov["gpu_id"] != "") & (ov["price"] != "")]
    if ov.empty:
        return pd.DataFrame(columns=PRICE_COLUMNS)
    price = pd.to_numeric(ov["price"], errors="coerce")
    checked_on = pd.to_datetime(ov["checked_on"], format=_ISO_DATE, utc=True, errors="coerce")
    valid_until = pd.to_datetime(ov["valid_until"], format=_ISO_DATE, utc=True, errors="coerce")
    problems = _override_problems(ov, price, checked_on, valid_until, now)
    if problems:
        raise InputError(f"{path.name} has rows to fix:\n" + "\n".join(problems))
    keep = valid_until.isna() | (valid_until >= now)
    ov, price, checked_on = ov[keep], price[keep], checked_on[keep]
    rows = pd.DataFrame(
        {
            "gpu_id": ov["gpu_id"],
            "retailer": ov["retailer"].replace("", "manual"),
            "sku": "",
            "title_raw": ov["note"],
            "price": price,
            "currency": "USD",
            "url": ov["url"],
            "condition": "new",
            "in_stock": True,
            "is_valid": True,
            "invalid_reason": "",
            "fetched_at": checked_on.fillna(now),
            "run_id": MANUAL_RUN_PREFIX + run_id,
        }
    )
    return rows


def _override_problems(ov, price, checked_on, valid_until, now) -> list[str]:
    """One message per malformed field, naming the CSV line (header is line 1)."""
    problems = []
    for i, row in ov.iterrows():
        where = f"  line {i + 2} ({row['gpu_id']}):"
        if not price[i] > 0:
            problems.append(f"{where} price {row['price']!r} must be a plain number like 849.99")
        if row["checked_on"] and pd.isna(checked_on[i]):
            problems.append(f"{where} checked_on {row['checked_on']!r} must be YYYY-MM-DD")
        elif checked_on[i] > now:
            problems.append(f"{where} checked_on {row['checked_on']} is in the future")
        if row["valid_until"] and pd.isna(valid_until[i]):
            problems.append(f"{where} valid_until {row['valid_until']!r} must be YYYY-MM-DD")
        if row["url"] and not row["url"].startswith("https://"):
            problems.append(f"{where} url must start with https://")
        if row["retailer"] and not _RETAILER_ID.fullmatch(row["retailer"]):
            problems.append(
                f"{where} retailer {row['retailer']!r} must be an id like bestbuy, newegg or amazon"
            )
    return problems


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
