"""Human-readable review report. Anything listed under "Needs review" makes the
refresh workflow open a pull request instead of committing straight to main."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from svi.config import SITE_DATA_DIR, Config

REPORT_PATH = SITE_DATA_DIR / "review_report.md"


@dataclass
class ReviewInputs:
    cfg: Config
    run_id: str
    unresolved: list[dict]
    anomalies: list[dict]
    registry: pd.DataFrame
    current_prices: pd.DataFrame
    rankings: dict[str, pd.DataFrame]
    changelog_entry: dict
    fetch_failures: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _table(rows: list[dict], cols: list[str]) -> str:
    if not rows:
        return "_none_\n"
    head = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    body = "".join("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |\n" for r in rows)
    return head + body


def build_report(inp: ReviewInputs) -> tuple[str, bool, list[str]]:
    """Return (markdown, needs_review, reasons)."""
    reasons: list[str] = []
    active = inp.registry[inp.registry["is_active"].astype(str).str.lower() == "true"]
    priced = set(inp.current_prices["gpu_id"])
    missing_price = sorted(set(active["gpu_id"]) - priced)

    big_moves = [
        c
        for c in inp.changelog_entry.get("price_changes", [])
        if abs(c["pct"]) >= inp.cfg.pricing.review_move_pct
    ]
    if inp.fetch_failures:
        reasons.append(f"{len(inp.fetch_failures)} source fetch failure(s)")
    if inp.unresolved:
        reasons.append(f"{len(inp.unresolved)} unresolved name(s)")
    if inp.changelog_entry.get("added_gpus") or inp.changelog_entry.get("removed_gpus"):
        reasons.append("GPU set changed")
    if inp.changelog_entry.get("benchmark_suite_changed"):
        reasons.append("benchmark suite version changed")
    if big_moves:
        reasons.append(f"{len(big_moves)} price move(s) >= {inp.cfg.pricing.review_move_pct:g}%")
    if inp.anomalies:
        reasons.append(f"{len(inp.anomalies)} benchmark anomaly(ies)")

    md = [f"# Refresh report `{inp.run_id}`\n"]
    md.append("**Needs review: " + ("YES" if reasons else "no") + "**\n")
    if reasons:
        md.append("\n".join(f"- {r}" for r in reasons) + "\n")

    md.append("\n## Fetch failures\n")
    md.append(
        "\n".join(f"- {f}" for f in inp.fetch_failures) + "\n" if inp.fetch_failures else "_none_\n"
    )

    md.append("\n## Unresolved names\n")
    md.append(
        "Add a row to `data/reference/aliases.csv` (alias,gpu_id,source) "
        "or a new registry entry.\n\n"
    )
    md.append(
        _table(
            [
                {
                    "source": u.get("source", ""),
                    "raw_name": u.get("raw_name", ""),
                    "candidates": ", ".join(
                        f"{c[0]} ({c[1]:.0f})" for c in u.get("candidates", [])
                    ),
                }
                for u in inp.unresolved
            ],
            ["source", "raw_name", "candidates"],
        )
    )

    md.append("\n## Active GPUs with no valid current price\n")
    md.append(
        "These drop out of the rankings. "
        "Add a row to `data/reference/price_overrides.csv` if needed.\n\n"
    )
    md.append("\n".join(f"- `{g}`" for g in missing_price) + "\n" if missing_price else "_none_\n")

    md.append(f"\n## Price moves >= {inp.cfg.pricing.review_move_pct:g}%\n")
    md.append(_table(big_moves, ["gpu_id", "from", "to", "pct"]))

    md.append("\n## Benchmark anomalies\n")
    md.append(_table(inp.anomalies, ["type", "gpu_id", "resolution", "mode", "residual", "detail"]))

    md.append("\n## Changes this run\n")
    ce = inp.changelog_entry
    md.append(f"- Added GPUs: {', '.join(ce.get('added_gpus', [])) or 'none'}\n")
    md.append(f"- Removed GPUs: {', '.join(ce.get('removed_gpus', [])) or 'none'}\n")
    md.append(f"- Price changes >= 5%: {len(ce.get('price_changes', []))}\n")
    md.append(f"- Benchmark suite changed: {ce.get('benchmark_suite_changed', False)}\n")

    md.append("\n## Ranked counts\n")
    md.append("\n".join(f"- `{v}`: {len(df)}" for v, df in inp.rankings.items()) + "\n")

    if inp.notes:
        md.append("\n## Notes\n")
        md.append("\n".join(f"- {n}" for n in inp.notes) + "\n")

    return "".join(md), bool(reasons), reasons


def write_report(markdown: str, path=REPORT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
