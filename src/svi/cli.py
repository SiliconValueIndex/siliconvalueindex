"""`svi` command line: seed | build | schemas."""

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="svi", description="SiliconValueIndex pipeline")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("seed", help="convert the original CSVs into the long-format tables")

    b = sub.add_parser("build", help="normalize, score and export data/site/*.json")
    b.add_argument("--offline", action="store_true", help="skip all network fetches")
    b.add_argument("--skip-benchmarks", action="store_true")
    b.add_argument("--skip-prices", action="store_true")
    b.add_argument("--run-id", default=None)
    b.add_argument("--now", default=None, help="ISO timestamp to evaluate 'now' as (tests)")

    sub.add_parser("schemas", help="write schemas/*.schema.json")

    args = parser.parse_args(argv)

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
