"""End-to-end pipeline: (scrape) -> normalize -> score -> export -> report."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import pandas as pd

from svi.config import PROCESSED_DIR, SITE_DATA_DIR, Config, get_config
from svi.export.review_report import ReviewInputs, build_report, write_report
from svi.export.schemas import write_schema_files
from svi.export.site_json import (
    BuildContext,
    build_changelog_entry,
    build_gpus,
    build_rankings,
    write_site,
)
from svi.ids import REGISTRY_PATH, Resolver
from svi.normalize.benchmarks import build_effective_benchmarks
from svi.prices import (
    append_history,
    daily_lows,
    load_history,
    load_overrides,
    select_current_prices,
    validate_observations,
)
from svi.scoring.cost_per_fps import score_all_views
from svi.seed import BENCHMARK_COLUMNS, BENCHMARKS_PATH, write_benchmarks

BENCHMARKS_PATH = BENCHMARKS_PATH  # re-export for callers


def load_registry() -> pd.DataFrame:
    reg = pd.read_csv(REGISTRY_PATH, dtype=str).fillna("")
    reg["msrp_usd"] = pd.to_numeric(reg["msrp_usd"], errors="coerce")
    return reg


def load_benchmarks() -> pd.DataFrame:
    if not BENCHMARKS_PATH.exists():
        return pd.DataFrame(columns=BENCHMARK_COLUMNS)
    df = pd.read_csv(BENCHMARKS_PATH, dtype={"suite_version": str, "snapshot_ref": str})
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True)
    return df


def append_benchmarks(new_rows: pd.DataFrame) -> pd.DataFrame:
    existing = load_benchmarks()
    new_rows = new_rows.copy()
    new_rows["fetched_at"] = pd.to_datetime(new_rows["fetched_at"], utc=True)
    combined = pd.concat([existing, new_rows[BENCHMARK_COLUMNS]], ignore_index=True)
    combined = combined.drop_duplicates(
        subset=["gpu_id", "source", "suite_version", "resolution", "setting", "mode", "fps"],
        keep="last",
    )
    write_benchmarks(combined.sort_values(["suite_version", "resolution", "mode", "gpu_id"]))
    return load_benchmarks()


def run_build(
    *,
    offline: bool = True,
    run_id: str | None = None,
    now: datetime | None = None,
    skip_benchmarks: bool = False,
    skip_prices: bool = False,
    cfg: Config | None = None,
) -> dict:
    cfg = cfg or get_config()
    now = now or datetime.now(UTC)
    run_id = run_id or now.strftime("%Y%m%dT%H%M%SZ")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    registry = load_registry()
    resolver = Resolver.from_files()
    active_ids = registry.loc[registry["is_active"].str.lower() == "true", "gpu_id"].tolist()

    unresolved: list[dict] = []
    fetch_failures: list[str] = []
    source_fetched: dict[str, str | None] = {}
    notes: list[str] = []

    benchmarks = load_benchmarks()
    history = load_history()

    if not offline and not skip_benchmarks:
        from svi.scrapers.toms_hardware import scrape_benchmarks

        try:
            records, unres, info = scrape_benchmarks(
                resolver, cfg, run_id=run_id, now=now, existing=benchmarks
            )
            unresolved += [u.model_dump() for u in unres]
            if records.empty:
                raise RuntimeError("parser returned no rows")
            benchmarks = append_benchmarks(records)
            source_fetched["toms"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            notes.append(
                f"Tom's Hardware: {info['rows_parsed']} cells parsed, "
                f"suite {info['suite_version']} ({info['suite_reason']})"
            )
            notes += [f"Tom's Hardware parser: {w}" for w in info["warnings"]]
            # Fill launch prices the registry does not carry, without editing the registry.
            missing = registry["msrp_usd"].isna()
            registry.loc[missing, "msrp_usd"] = registry.loc[missing, "gpu_id"].map(info["msrp"])
        except Exception as exc:  # degrade: keep previous benchmarks
            fetch_failures.append(f"toms_hardware: {exc}")

    if not offline and not skip_prices:
        from svi.scrapers.bestbuy import scrape_prices

        try:
            obs, unres = scrape_prices(resolver, registry, cfg, run_id=run_id, now=now)
            unresolved += [u.model_dump() for u in unres]
            obs = validate_observations(obs, history, cfg.pricing, now=now)
            history = append_history(obs)
            source_fetched["bestbuy"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            notes.append(f"Best Buy: {int(obs['is_valid'].sum())} valid of {len(obs)} observations")
        except Exception as exc:
            fetch_failures.append(f"bestbuy: {exc}")

    overrides = load_overrides(now=now)
    if not overrides.empty:
        overrides["run_id"] = run_id
        history = append_history(overrides)
        source_fetched["manual"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        notes.append(f"Manual overrides applied: {len(overrides)}")

    if benchmarks.empty:
        raise RuntimeError("No benchmark data available. Run `svi seed` or an online build first.")

    effective, transforms, anomalies = build_effective_benchmarks(benchmarks, cfg.normalization)
    effective = effective[effective["gpu_id"].isin(active_ids)]
    current = select_current_prices(history, cfg.pricing, now=now)
    current = current[current["gpu_id"].isin(active_ids)]
    rankings, zone_meta = score_all_views(effective, current, cfg.zones, cfg.views)

    ctx = BuildContext(
        cfg=cfg,
        run_id=run_id,
        generated_at=now,
        registry=registry,
        effective=effective,
        transforms=transforms,
        rankings=rankings,
        zone_meta=zone_meta,
        current_prices=current,
        daily_lows=daily_lows(history),
        anomalies=anomalies,
        unresolved=unresolved,
        source_fetched=source_fetched,
        notes=notes,
    )
    entry = build_changelog_entry(ctx, build_gpus(ctx), build_rankings(ctx), SITE_DATA_DIR)
    report_md, needs_review, reasons = build_report(
        ReviewInputs(
            cfg=cfg,
            run_id=run_id,
            unresolved=unresolved,
            anomalies=anomalies,
            registry=registry,
            current_prices=current,
            rankings=rankings,
            changelog_entry=entry,
            fetch_failures=fetch_failures,
            notes=notes,
        )
    )
    summary = write_site(ctx, needs_review)
    write_report(report_md)
    write_schema_files()

    if gh_out := os.environ.get("GITHUB_OUTPUT"):
        with open(gh_out, "a", encoding="utf-8") as fh:
            fh.write(f"needs_review={'true' if needs_review else 'false'}\n")
            fh.write(f"run_id={run_id}\n")
    if gh_sum := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(gh_sum, "a", encoding="utf-8") as fh:
            fh.write(report_md)

    return {
        "run_id": run_id,
        "needs_review": needs_review,
        "reasons": reasons,
        "fetch_failures": fetch_failures,
        **summary,
    }
