import csv
import io

import pytest

from svi.scrapers.catalog import parse_catalog


def catalog(status="in-stock", mid="44583", count=1):
    row = [""] * 38
    row[0:3] = ["123", "MSI GeForce RTX 4070 12GB Graphics Card", "sku-1"]
    row[5] = "https://www.newegg.com/p/test"
    row[12], row[13], row[22], row[25] = "499.99", "599.99", status, "USD"
    stream = io.StringIO()
    writer = csv.writer(stream, delimiter="|")
    writer.writerow(["HDR", mid, "Newegg", "10/15/2026 12:00:00"])
    writer.writerow(row)
    writer.writerow(["TRL", count])
    return stream.getvalue()


@pytest.mark.parametrize("status", ["in-stock", "out-of-stock", "preorder", "backorder", ""])
def test_catalog_preserves_availability(status):
    items, summary = parse_catalog(io.StringIO(catalog(status)))
    assert len(items) == 1
    assert items[0]["availability"] == status
    assert items[0]["saleprice"] == "499.99"
    assert summary["products"] == 1
    assert summary["created_at"] == "2026-10-15T12:00:00+00:00"


def test_catalog_requires_correct_merchant_and_complete_trailer():
    with pytest.raises(ValueError, match="advertiser"):
        parse_catalog(io.StringIO(catalog(mid="999")))
    with pytest.raises(ValueError, match="count"):
        parse_catalog(io.StringIO(catalog(count=2)))
    with pytest.raises(ValueError, match="trailer"):
        parse_catalog(io.StringIO(catalog().split("TRL")[0]))


def test_catalog_rejects_trailing_records():
    with pytest.raises(ValueError, match="after"):
        parse_catalog(io.StringIO(catalog() + "TRL|1\n"))
