"""`svi` command line: seed | build | prices-check | schemas."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime


def _parse_now(value: str | None) -> datetime | None:
    if not value:
        return None
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def prices_check(retailer: str, limit: int, gpu_ids: list[str] | None = None) -> int:
    from svi.build import load_registry, select_gpus
    from svi.config import get_config
    from svi.ids import Resolver
    from svi.prices import load_history, validate_observations
    from svi.scrapers.retailers import RetailerSkipped, get_adapter, redact_secrets

    try:
        adapter = get_adapter(retailer)
    except KeyError as exc:
        print(redact_secrets(str(exc.args[0])))
        return 1

    try:
        registry = load_registry()
        registry = select_gpus(registry, gpu_ids).head(limit)
        cfg = get_config()
        now = datetime.now(UTC)
        obs, unresolved = adapter(
            Resolver.from_files(), registry, cfg, run_id="prices-check", now=now
        )
        obs = validate_observations(obs, load_history(), cfg.pricing, now=now)
    except RetailerSkipped as exc:
        print(redact_secrets(str(exc)))
        return 2
    except Exception as exc:
        print(redact_secrets(str(exc)))
        return 1

    columns = ["gpu_id", "retailer", "price", "in_stock", "condition", "is_valid", "invalid_reason"]
    table = obs[columns].copy()
    table["title"] = (
        obs["title_raw"]
        .astype(str)
        .map(lambda title: title if len(title) <= 60 else title[:57] + "...")
    )
    print(table.to_string(index=False))
    print(f"{int(obs['is_valid'].sum())} valid of {len(obs)} observations")
    print(f"{len(unresolved)} unresolved titles")
    for item in unresolved:
        print(f"  {item.raw_name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="svi", description="SiliconValueIndex pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("seed", help="convert the original CSVs into the long-format tables")

    b = sub.add_parser("build", help="normalize, score and export data/site/*.json")
    b.add_argument("--offline", action="store_true", help="skip all network fetches")
    b.add_argument("--skip-benchmarks", action="store_true")
    b.add_argument("--skip-prices", action="store_true")
    b.add_argument("--retailers", default=None, help="comma-separated retailer names")
    b.add_argument("--run-id", default=None)
    b.add_argument("--gpu", action="append", help="limit price fetches to this GPU ID; repeatable")
    b.add_argument("--now", default=None, help="ISO timestamp to evaluate 'now' as (tests)")

    sub.add_parser("schemas", help="write schemas/*.schema.json")

    check = sub.add_parser("prices-check", help="verify retailer prices without writing data")
    check.add_argument("--retailer", required=True)
    check.add_argument("--limit", type=int, default=3)
    check.add_argument("--gpu", action="append", help="active GPU ID to preview; repeatable")

    args = parser.parse_args(argv)

    if args.cmd == "prices-check":
        if args.limit < 0:
            parser.error("--limit must be non-negative")
        return prices_check(args.retailer, args.limit, args.gpu)

    if args.cmd == "seed":
        from svi.seed import run_seed

        print(json.dumps(run_seed(), indent=1, default=str))
        return 0

    if args.cmd == "build":
        from svi.build import run_build

        result = run_build(
            offline=args.offline,
            run_id=args.run_id,
            now=_parse_now(args.now),
            skip_benchmarks=args.skip_benchmarks,
            skip_prices=args.skip_prices,
            retailers=(
                [name.strip() for name in args.retailers.split(",")]
                if args.retailers is not None
                else None
            ),
            gpu_ids=args.gpu,
        )
        print(json.dumps(result, indent=1, default=str))
        return 0

    if args.cmd == "schemas":
        from svi.export.schemas import write_schema_files

        write_schema_files()
        print("wrote schemas/")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
