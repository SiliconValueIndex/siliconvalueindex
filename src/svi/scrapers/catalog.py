"""Read Rakuten's full Newegg Product Catalog over pinned SFTP."""

from __future__ import annotations

import csv
import gzip
import os
import tempfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from svi.ids import extract_model

HOST = "aftp.linksynergy.com"
HOST_KEY = "aftp.linksynergy.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINwrS54V0yc+9UnhjYlffU8qjCl9Z30AH4oHQQ8+mVTo"


def parse_catalog(lines, *, mid="44583"):
    """Validate a full pipe-delimited catalog; retain GPU candidates only."""
    from svi.scrapers.rakuten import excluded_product

    reader = csv.reader(lines, delimiter="|")
    header = next(reader, [])
    if len(header) != 4 or header[:2] != ["HDR", mid]:
        raise ValueError("Catalog header is missing or advertiser does not match")
    created = datetime.strptime(header[3], "%m/%d/%Y %H:%M:%S").replace(tzinfo=UTC)
    count = 0
    trailer = False
    availability = Counter()
    items = []
    for row in reader:
        if not row:
            continue
        if trailer:
            raise ValueError("Unexpected content after catalog trailer")
        if row[0] == "TRL":
            if len(row) != 2 or int(row[1]) != count:
                raise ValueError("Catalog trailer count does not match")
            trailer = True
            continue
        if len(row) < 28:
            raise ValueError("Incomplete catalog product record")
        count += 1
        status = row[22].strip().lower()
        availability[status or "unknown"] += 1
        title = row[1]
        if extract_model(title) and not excluded_product(title):
            items.append(
                dict(
                    sku=row[2],
                    productname=title,
                    price=row[13],
                    saleprice=row[12],
                    currency=row[25].strip().upper(),
                    linkurl=row[5],
                    availability=status,
                )
            )
    if not trailer or not count:
        raise ValueError("Catalog is empty or missing its completeness trailer")
    return items, {
        "created_at": created.isoformat(),
        "products": count,
        "availability": dict(availability),
        "gpu_candidates": len(items),
    }


def fetch_catalog():
    import paramiko

    username = os.environ.get("RAKUTEN_SFTP_USERNAME", "").strip()
    password = os.environ.get("RAKUTEN_SFTP_PASSWORD", "")
    sid = os.environ.get("RAKUTEN_SID", "").strip()
    if not username or not password or not sid.isdigit():
        raise RuntimeError("Missing Rakuten SFTP credentials or valid SID")
    client = paramiko.SSHClient()
    entry = paramiko.hostkeys.HostKeyEntry.from_line(HOST_KEY)
    client.get_host_keys().add(HOST, entry.key.get_name(), entry.key)
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(
            HOST,
            username=username,
            password=password,
            timeout=30,
            auth_timeout=30,
            banner_timeout=30,
            look_for_keys=False,
            allow_agent=False,
        )
        with client.open_sftp() as sftp, tempfile.TemporaryDirectory() as folder:
            sftp.get_channel().settimeout(120)
            path = Path(folder) / "catalog.txt.gz"
            sftp.get(f"44583_{sid}_mp.txt.gz", str(path), max_concurrent_prefetch_requests=32)
            with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
                return parse_catalog(stream)
    except Exception as exc:
        # Do not expose usernames, passwords, private paths or server responses.
        raise RuntimeError(f"Rakuten catalog fetch failed ({type(exc).__name__})") from None
    finally:
        client.close()


if __name__ == "__main__":
    import json

    items, summary = fetch_catalog()
    print(json.dumps(summary))
    Path("catalog-check.json").write_text(
        json.dumps({"summary": summary, "items": items}), encoding="utf-8"
    )
