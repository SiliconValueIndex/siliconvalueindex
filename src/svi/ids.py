"""Stable gpu_id slugs and resolution of free-text names to gpu_ids.

Resolution order:
1. canonicalize the text (strip brand words, whitespace, VRAM spelling)
2. exact match against the alias table (display names + aliases.csv)
3. regex extraction of the model token (family, number, suffixes, VRAM) matched
   against the registry; ambiguous VRAM variants are reported, never guessed
4. fuzzy match (rapidfuzz) accepted only when the extracted model number agrees
Anything else is returned as an UnresolvedName for the review report.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from rapidfuzz import fuzz, process

from svi.config import REFERENCE_DIR
from svi.models import UnresolvedName

REGISTRY_PATH = REFERENCE_DIR / "gpu_master_list.csv"
ALIASES_PATH = REFERENCE_DIR / "aliases.csv"

_BRAND_WORDS = re.compile(r"\b(geforce|radeon|nvidia|amd|intel)\b", re.I)
_VRAM = re.compile(r"\b(\d{1,2})\s*gb\b", re.I)
_WS = re.compile(r"\s+")
_MODEL = re.compile(
    r"\b(?P<family>rtx|gtx|rx|arc)\s*"
    r"(?P<number>[ab]\d{3}|\d{4})"
    r"(?P<suffix>(?:\s*(?:ti|super|xt|xtx|gre)\b)*)",
    re.I,
)
# Words in retailer titles that signal a listing we never want to price.
NEGATIVE_TOKENS = (
    "bundle",
    "laptop",
    "notebook",
    "waterblock",
    "water block",
    "backplate",
    "cable",
    "bracket",
    "riser",
    "mining",
    "renewed",
    "refurbished",
    "pre-owned",
    "used",
)


def canonicalize(text: str) -> str:
    """Lower-case, drop brand words, normalise VRAM tokens and whitespace."""
    t = _BRAND_WORDS.sub(" ", text.lower())
    t = _VRAM.sub(lambda m: f"{m.group(1)}gb", t)
    t = t.replace("-", " ")
    return _WS.sub(" ", t).strip()


def slugify(vendor: str, display_name: str) -> str:
    body = canonicalize(display_name)
    body = re.sub(r"[^a-z0-9 ]", "", body)
    return f"{vendor.lower()}-{body.replace(' ', '-')}"


def extract_model(text: str) -> dict[str, str] | None:
    """Pull (family, number, suffix, vram) out of arbitrary text, or None."""
    canon = canonicalize(text)
    m = _MODEL.search(canon)
    if not m:
        return None
    suffix = _WS.sub(" ", m.group("suffix")).strip()
    vram = _VRAM.search(canon)
    return {
        "family": m.group("family").lower(),
        "number": m.group("number").lower(),
        "suffix": suffix.lower(),
        "vram": f"{vram.group(1)}gb" if vram else "",
    }


def has_negative_token(text: str) -> bool:
    t = text.lower()
    return any(tok in t for tok in NEGATIVE_TOKENS)


@dataclass
class Resolver:
    """Maps names to gpu_ids using the registry plus an alias table."""

    display_names: dict[str, str]  # gpu_id -> display_name
    aliases: dict[str, str] = field(default_factory=dict)  # canonical alias -> gpu_id
    fuzzy_threshold: float = 92.0

    @classmethod
    def from_files(
        cls, registry_path: Path = REGISTRY_PATH, aliases_path: Path = ALIASES_PATH
    ) -> Resolver:
        display: dict[str, str] = {}
        with open(registry_path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                display[row["gpu_id"]] = row["display_name"]
        aliases: dict[str, str] = {}
        if aliases_path.exists():
            with open(aliases_path, newline="", encoding="utf-8") as fh:
                for row in csv.DictReader(fh):
                    aliases[canonicalize(row["alias"])] = row["gpu_id"]
        return cls(display_names=display, aliases=aliases)

    def __post_init__(self) -> None:
        self._lookup: dict[str, str] = {}
        for gpu_id, name in self.display_names.items():
            self._lookup[canonicalize(name)] = gpu_id
        self._lookup.update(self.aliases)
        self._models: dict[str, dict[str, str]] = {}
        for gpu_id, name in self.display_names.items():
            model = extract_model(name)
            if model:
                self._models[gpu_id] = model

    def resolve(self, raw_name: str, source: str = "") -> str | UnresolvedName:
        canon = canonicalize(raw_name)
        if canon in self._lookup:
            return self._lookup[canon]

        model = extract_model(raw_name)
        if model:
            hits = [
                gid
                for gid, m in self._models.items()
                if m["family"] == model["family"]
                and m["number"] == model["number"]
                and m["suffix"] == model["suffix"]
            ]
            if model["vram"]:
                vram_hits = [gid for gid in hits if self._models[gid]["vram"] == model["vram"]]
                if vram_hits:
                    hits = vram_hits
            if len(hits) == 1:
                return hits[0]
            if len(hits) > 1:
                # VRAM variants the text does not disambiguate. Prefer the variant whose
                # registry name carries no VRAM token (the plain SKU); otherwise report.
                plain = [gid for gid in hits if not self._models[gid]["vram"]]
                if len(plain) == 1:
                    return plain[0]
                return UnresolvedName(
                    source=source,
                    raw_name=raw_name,
                    canonical=canon,
                    candidates=[(gid, 100.0) for gid in hits],
                )

        choices = list(self._lookup.keys())
        best = process.extract(canon, choices, scorer=fuzz.token_set_ratio, limit=3)
        candidates = [(self._lookup[c], float(score)) for c, score, _ in best]
        if best:
            top_alias, top_score, _ = best[0]
            top_id = self._lookup[top_alias]
            if top_score >= self.fuzzy_threshold and model and top_id in self._models:
                if self._models[top_id]["number"] == model["number"]:
                    return top_id
        return UnresolvedName(
            source=source, raw_name=raw_name, canonical=canon, candidates=candidates
        )
