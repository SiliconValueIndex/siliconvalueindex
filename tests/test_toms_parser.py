from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

from svi.ids import Resolver
from svi.scrapers.toms_hardware import (
    detect_suite_version,
    parse_hierarchy,
    records_from_rows,
    scrape_benchmarks,
)

FIXTURE = Path(__file__).parent / "fixtures" / "toms_gpu_hierarchy_current_2026-09-16.html"
HTML = FIXTURE.read_text(encoding="utf-8")


def test_parse_both_tables_three_resolutions():
    rows, warnings = parse_hierarchy(HTML)
    assert not warnings
    modes = {r["mode"] for r in rows}
    assert modes == {"raster", "rt"}
    assert {r["resolution"] for r in rows} == {"1080p", "1440p", "4k"}
    names = {r["name"] for r in rows if r["mode"] == "raster"}
    assert len(names) == 48
    top = next(
        r
        for r in rows
        if r["name"] == "GeForce RTX 5090" and r["mode"] == "raster" and r["resolution"] == "1440p"
    )
    assert top["fps"] == 167.3 and top["pct"] == 100.0 and top["msrp"] == 1999.99
    rt = next(
        r
        for r in rows
        if r["name"] == "GeForce RTX 4090" and r["mode"] == "rt" and r["resolution"] == "4k"
    )
    assert rt["fps"] == 52.2


def test_cell_regex_tolerates_spacing():
    head = "<tr><th>Graphics Card</th><th>MSRP</th><th>1080p Ultra</th><th>1440p Ultra</th><th>4K Ultra</th></tr>"  # noqa: E501
    row = "<tr><td>GeForce RTX 4070</td><td>$549.99</td><td>54.7 % ( 111.5 )</td><td>46.5%(77.8)</td><td>n/a</td></tr>"  # noqa: E501
    filler = "<tr><td>Row 2 - Cell 0</td><td></td><td></td><td></td><td></td></tr>"
    html = f"<table>{head}{row}{filler}</table>"
    rows, warnings = parse_hierarchy(html)
    assert [r["resolution"] for r in rows] == ["1080p", "1440p"]
    assert rows[0]["fps"] == 111.5 and rows[1]["fps"] == 77.8
    assert "inferred" in warnings[0]


def test_records_resolve_names_and_collect_unresolved():
    rows, _ = parse_hierarchy(HTML)
    resolver = Resolver.from_files()
    now = datetime(2026, 9, 16, tzinfo=UTC)
    df, unresolved, msrp = records_from_rows(
        rows, resolver, suite_version="t", now=now, snapshot_ref="x"
    )
    assert (df["gpu_id"] == "nvidia-rtx-4090").sum() == 6  # 2 modes x 3 resolutions
    assert msrp["nvidia-rtx-4090"] == 1599.99
    unresolved_names = {u.raw_name for u in unresolved}
    # Cards Tom's tests that the registry does not track yet must be reported, never dropped.
    assert all(u.candidates for u in unresolved)
    assert df["gpu_id"].is_unique is False
    assert not (set(df["gpu_id"]) & {u.raw_name for u in unresolved})
    assert len(unresolved_names) == len(unresolved)


def test_suite_detection():
    now = datetime(2026, 9, 16, tzinfo=UTC)
    prev = pd.DataFrame(
        {
            "gpu_id": ["a", "b", "c"],
            "resolution": ["1440p"] * 3,
            "mode": ["raster"] * 3,
            "fps": [100.0, 50.0, 25.0],
            "suite_version": ["2026-03"] * 3,
        }
    )
    same = prev.assign(fps=[101.0, 50.5, 25.0])
    label, reason = detect_suite_version(same, prev, now)
    assert label == "2026-03"
    changed = prev.assign(fps=[120.0, 60.0, 30.0])
    label, reason = detect_suite_version(changed, prev, now)
    assert label == "2026-09-16" and "moved" in reason
    label, _ = detect_suite_version(changed, pd.DataFrame(), now)
    assert label == "2026-09-16"


def test_scrape_offline_from_html():
    from svi.config import get_config

    resolver = Resolver.from_files()
    now = datetime(2026, 9, 16, tzinfo=UTC)
    records, unresolved, info = scrape_benchmarks(
        resolver, get_config(), run_id="t", now=now, existing=pd.DataFrame(), html=HTML
    )
    assert info["rows_parsed"] == 48 * 2 * 3
    assert (records["suite_version"] == "2026-09-16").all()
    assert set(records["mode"]) == {"raster", "rt"}
