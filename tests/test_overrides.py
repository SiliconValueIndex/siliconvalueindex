from datetime import UTC, datetime

import pandas as pd

from svi import prices
from svi.build import load_registry
from svi.prices import PRICE_OVERRIDES_PATH, load_overrides

NOW = datetime(2026, 9, 29, 12, tzinfo=UTC)
HEADER = "gpu_id,price,url,retailer,note,checked_on,valid_until\n"


def write(tmp_path, body, header=HEADER):
    path = tmp_path / "overrides.csv"
    path.write_text(header + body, encoding="utf-8")
    return path


def test_blank_price_rows_are_skipped(tmp_path):
    path = write(tmp_path, "nvidia-rtx-5070,,,,RTX 5070,,\nnvidia-rtx-5080,999.99,,bestbuy,,,\n")
    rows = load_overrides(path, now=NOW)
    assert list(rows["gpu_id"]) == ["nvidia-rtx-5080"]
    assert rows["retailer"].iloc[0] == "bestbuy"


def test_checked_on_becomes_fetched_at(tmp_path):
    path = write(tmp_path, "nvidia-rtx-5070,549.99,,newegg,,2026-09-20,\n")
    rows = load_overrides(path, now=NOW)
    assert rows["fetched_at"].iloc[0] == pd.Timestamp("2026-09-20", tz="UTC")


def test_missing_checked_on_falls_back_to_now(tmp_path):
    path = write(
        tmp_path,
        "nvidia-rtx-5070,549.99,,,,\n",
        header="gpu_id,price,url,retailer,note,valid_until\n",
    )
    rows = load_overrides(path, now=NOW)
    assert rows["fetched_at"].iloc[0] == NOW
    assert rows["retailer"].iloc[0] == "manual"


def test_expired_rows_are_dropped(tmp_path):
    path = write(tmp_path, "nvidia-rtx-5070,549.99,,,,2026-09-01,2026-09-15\n")
    assert load_overrides(path, now=NOW).empty


def test_rerunning_a_dated_override_does_not_duplicate_history(tmp_path):
    path = write(tmp_path, "nvidia-rtx-5070,549.99,,newegg,,2026-09-20,\n")
    history = tmp_path / "history.csv"
    prices.append_history(load_overrides(path, now=NOW), path=history)
    later = datetime(2026, 10, 6, tzinfo=UTC)
    combined = prices.append_history(load_overrides(path, now=later), path=history)
    assert len(combined) == 1


def test_committed_overrides_reference_active_gpus():
    ids = set(pd.read_csv(PRICE_OVERRIDES_PATH, dtype=str)["gpu_id"].dropna())
    registry = load_registry()
    active = set(registry.loc[registry["is_active"] == "true", "gpu_id"])
    assert ids <= active, sorted(ids - active)
