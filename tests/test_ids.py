import csv
import re

from svi.ids import (
    REGISTRY_PATH,
    Resolver,
    canonicalize,
    extract_model,
    has_negative_token,
    slugify,
)
from svi.models import UnresolvedName


def test_registry_ids_are_unique_and_well_formed():
    with open(REGISTRY_PATH, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    ids = [r["gpu_id"] for r in rows]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"[a-z]+-[a-z0-9-]+", i) for i in ids)
    # Slugs are derived from vendor + display_name and must stay stable.
    assert all(slugify(r["vendor"], r["display_name"]) == r["gpu_id"] for r in rows)


def test_canonicalize_strips_brands_and_whitespace():
    assert canonicalize("  GeForce RTX 3060 ") == "rtx 3060"
    assert canonicalize("Radeon RX 7900 GRE") == "rx 7900 gre"
    assert canonicalize("Intel Arc B580") == "arc b580"
    assert canonicalize("RTX 4060 Ti 16 GB") == "rtx 4060 ti 16gb"


def test_extract_model():
    assert extract_model("MSI RTX 4070 Ti SUPER 16G Ventus") == {
        "family": "rtx",
        "number": "4070",
        "suffix": "ti super",
        "vram": "",
    }
    assert extract_model("Sapphire Pulse RX 7800XT 16GB")["suffix"] == "xt"
    assert extract_model("ASRock Arc B580 Challenger")["number"] == "b580"
    assert extract_model("Ryzen 7 9800X3D") is None


def test_resolver_exact_alias_regex_and_fuzzy():
    r = Resolver.from_files()
    assert r.resolve("GeForce RTX 4090") == "nvidia-rtx-4090"
    assert r.resolve("Arc B580") == "intel-arc-b580"
    assert r.resolve("ASUS Dual RTX4060-O8G-EVO") == "nvidia-rtx-4060"
    assert r.resolve("GeForce RTX 4060 Ti 16GB") == "nvidia-rtx-4060-ti-16gb"
    # Plain "4060 Ti" maps to the 8GB SKU via the explicit alias, never by guessing.
    assert r.resolve("GeForce RTX 4060 Ti") == "nvidia-rtx-4060-ti-8gb"
    # 4060 must never resolve to 4060 Ti and vice versa.
    assert r.resolve("RTX 4060") == "nvidia-rtx-4060"
    assert r.resolve("RTX 4060 Ti") != "nvidia-rtx-4060"


def test_resolver_reports_unknown_cards():
    r = Resolver.from_files()
    hit = r.resolve("Radeon RX 5700 XT", source="test")
    assert isinstance(hit, UnresolvedName)
    assert hit.source == "test" and hit.candidates


def test_negative_tokens():
    assert has_negative_token("GeForce RTX 5080 Laptop GPU")
    assert has_negative_token("RTX 4090 waterblock bundle")
    assert not has_negative_token("MSI GeForce RTX 4070 Gaming X Trio")
