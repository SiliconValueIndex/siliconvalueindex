"""Tom's Hardware GPU benchmarks hierarchy.

The page carries two tables (rasterization and ray tracing) with columns
Graphics Card | MSRP | 1080p Ultra | 1440p Ultra | 4K Ultra and cells like
"85.7% (143.4)": percent of the top card and absolute average FPS.

Tom's does not label its test-suite version. We detect a new suite when the
numbers for cards we already track move materially; otherwise a fetch is a
re-observation of the same suite. The parser is a pure function of the HTML so it
can be tested on a saved fixture.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import pandas as pd
from bs4 import BeautifulSoup

from svi.config import Config
from svi.ids import Resolver
from svi.models import UnresolvedName
from svi.scrapers.base import fetch_text, save_snapshot
from svi.seed import BENCHMARK_COLUMNS

SOURCE = "toms_gpu_hierarchy"
_CELL = re.compile(r"(?P<pct>\d+(?:\.\d+)?)\s*%\s*\(\s*(?P<fps>\d+(?:\.\d+)?)\s*\)")
_RES = {"1080p": "1080p", "1440p": "1440p", "4k": "4k"}
_MODE_HINTS = (("ray tracing", "rt"), ("rasterization", "raster"), ("raster", "raster"))


def _mode_for_table(table) -> str | None:
    """Work out raster/rt from the caption or any text that precedes the header."""
    texts = []
    cap = table.find("caption")
    if cap:
        texts.append(cap.get_text(" ", strip=True))
    first = table.find("tr")
    if first:
        texts.append(first.get_text(" ", strip=True))
    prev = table.find_previous(["h2", "h3", "p"])
    if prev:
        texts.append(prev.get_text(" ", strip=True))
    blob = " ".join(texts).lower()
    for hint, mode in _MODE_HINTS:
        if hint in blob:
            return mode
    return None


def _header_map(header_cells: list[str]) -> dict[int, str]:
    """Column index -> resolution key for the FPS columns."""
    out: dict[int, str] = {}
    for i, text in enumerate(header_cells):
        t = text.lower().replace(" ", "")
        for key, res in _RES.items():
            if t.startswith(key):
                out[i] = res
    return out


def _parse_money(text: str) -> float | None:
    m = re.search(r"\d[\d,]*(?:\.\d+)?", text)
    return float(m.group(0).replace(",", "")) if m else None


def parse_hierarchy(html: str) -> tuple[list[dict], list[str]]:
    """Return (rows, warnings). Each row: name, msrp, mode, resolution, fps, pct."""
    soup = BeautifulSoup(html, "lxml")
    rows: list[dict] = []
    warnings: list[str] = []
    seen_modes: set[str] = set()
    for table in soup.find_all("table"):
        trs = table.find_all("tr")
        if len(trs) < 3:
            continue
        header_idx = None
        header: list[str] = []
        for i, tr in enumerate(trs[:3]):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if any("graphics card" in c.lower() for c in cells) and any(
                "1440p" in c.lower() for c in cells
            ):
                header_idx, header = i, cells
                break
        if header_idx is None:
            continue
        res_cols = _header_map(header)
        name_col = next(i for i, c in enumerate(header) if "graphics card" in c.lower())
        msrp_col = next((i for i, c in enumerate(header) if "msrp" in c.lower()), None)
        mode = _mode_for_table(table)
        if mode is None:
            # First benchmark table on the page is rasterization, second is ray tracing.
            mode = "rt" if "raster" in seen_modes else "raster"
            warnings.append(f"table mode inferred as {mode} (no caption)")
        seen_modes.add(mode)
        for tr in trs[header_idx + 1 :]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) <= max(res_cols):
                continue
            name = cells[name_col].strip()
            if not name or name.lower().startswith("row "):
                continue
            msrp = _parse_money(cells[msrp_col]) if msrp_col is not None else None
            for col, res in res_cols.items():
                m = _CELL.search(cells[col])
                if not m:
                    continue
                rows.append(
                    {
                        "name": name,
                        "msrp": msrp,
                        "mode": mode,
                        "resolution": res,
                        "fps": float(m.group("fps")),
                        "pct": float(m.group("pct")),
                    }
                )
    if not rows:
        warnings.append("no benchmark tables recognised")
    return rows, warnings


def detect_suite_version(
    new: pd.DataFrame, existing: pd.DataFrame, now: datetime, *, tolerance: float = 0.03
) -> tuple[str, str]:
    """Reuse the latest stored suite label unless the numbers moved. Returns (label, reason)."""
    if existing.empty:
        return now.strftime("%Y-%m-%d"), "no previous suite"
    latest = sorted(existing["suite_version"].astype(str).unique())[-1]
    prev = existing[existing["suite_version"].astype(str) == latest]
    key = ["gpu_id", "resolution", "mode"]
    joined = new.merge(prev[key + ["fps"]], on=key, suffixes=("", "_prev"))
    if joined.empty:
        return now.strftime("%Y-%m-%d"), f"no overlap with suite {latest}"
    moved = (abs(joined["fps"] - joined["fps_prev"]) / joined["fps_prev"] > tolerance).mean()
    if moved > 0.3:
        return now.strftime(
            "%Y-%m-%d"
        ), f"{moved:.0%} of overlapping cards moved > {tolerance:.0%} vs {latest}"
    return latest, f"{moved:.0%} of cards moved; same suite as {latest}"


def records_from_rows(
    rows: list[dict], resolver: Resolver, *, suite_version: str, now: datetime, snapshot_ref: str
) -> tuple[pd.DataFrame, list[UnresolvedName], dict[str, float]]:
    out: list[dict] = []
    unresolved: dict[str, UnresolvedName] = {}
    msrp: dict[str, float] = {}
    for r in rows:
        hit = resolver.resolve(r["name"], source="toms")
        if isinstance(hit, UnresolvedName):
            unresolved.setdefault(r["name"], hit)
            continue
        if r["msrp"]:
            msrp.setdefault(hit, r["msrp"])
        out.append(
            {
                "gpu_id": hit,
                "component_type": "gpu",
                "source": SOURCE,
                "suite_version": suite_version,
                "resolution": r["resolution"],
                "setting": "ultra",
                "mode": r["mode"],
                "fps": r["fps"],
                "pct_of_top": r["pct"],
                "fetched_at": now,
                "snapshot_ref": snapshot_ref,
            }
        )
    df = pd.DataFrame(out, columns=BENCHMARK_COLUMNS)
    return df, list(unresolved.values()), msrp


def scrape_benchmarks(
    resolver: Resolver,
    cfg: Config,
    *,
    run_id: str,
    now: datetime | None = None,
    existing: pd.DataFrame | None = None,
    html: str | None = None,
) -> tuple[pd.DataFrame, list[UnresolvedName], dict]:
    """Fetch (or use `html`), parse, resolve. Returns (records, unresolved, info).

    info: {suite_version, suite_reason, warnings, msrp, snapshot}
    """
    now = now or datetime.now(UTC)
    if html is None:
        html = fetch_text(cfg.benchmarks.current_url)
        snapshot = save_snapshot(html, "gpu_hierarchy", now)
        snapshot_ref = str(snapshot.relative_to(snapshot.parents[3])).replace("\\", "/")
    else:
        snapshot_ref = f"inline:{run_id}"
    rows, warnings = parse_hierarchy(html)
    # Resolve first with a placeholder suite so the detector can compare by gpu_id.
    provisional, unresolved, msrp = records_from_rows(
        rows, resolver, suite_version="?", now=now, snapshot_ref=snapshot_ref
    )
    suite, reason = detect_suite_version(
        provisional, existing if existing is not None else pd.DataFrame(), now
    )
    records = provisional.assign(suite_version=suite)
    info = {
        "suite_version": suite,
        "suite_reason": reason,
        "warnings": warnings,
        "msrp": msrp,
        "snapshot": snapshot_ref,
        "rows_parsed": len(rows),
    }
    return records, unresolved, info
