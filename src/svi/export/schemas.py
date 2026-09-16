"""JSON Schemas for the files under data/site. Single source; `svi build` also writes
them to schemas/*.json so the front end and CI can validate against the same contract."""

from __future__ import annotations

import json
from pathlib import Path

from svi.config import SCHEMA_DIR

_ID = {"type": "string", "pattern": "^[a-z]+-[a-z0-9-]+$"}
_NUM_OR_NULL = {"type": ["number", "null"]}

BENCH_CELL = {
    "type": "object",
    "required": ["fps", "raw_fps", "pct_of_top", "suite_version", "normalized"],
    "properties": {
        "fps": {"type": "number", "exclusiveMinimum": 0},
        "raw_fps": {"type": "number", "exclusiveMinimum": 0},
        "pct_of_top": _NUM_OR_NULL,
        "suite_version": {"type": "string"},
        "normalized": {"type": "boolean"},
    },
    "additionalProperties": False,
}

ZONE_META = {
    "type": "object",
    "required": ["mode", "great_max", "fair_max"],
    "properties": {
        "mode": {"enum": ["absolute", "percentile"]},
        "great_max": {"type": "number"},
        "fair_max": {"type": "number"},
    },
    "additionalProperties": False,
}

TRANSFORM = {
    "type": "object",
    "required": ["resolution", "mode", "from_suite", "to_suite", "method", "params", "n_overlap"],
    "properties": {
        "resolution": {"type": "string"},
        "mode": {"type": "string"},
        "from_suite": {"type": "string"},
        "to_suite": {"type": "string"},
        "method": {"enum": ["linear", "ratio_trimmed", "piecewise"]},
        "params": {"type": "object"},
        "overlap_ids": {"type": "array", "items": _ID},
        "n_overlap": {"type": "integer"},
        "n_used": {"type": "integer"},
        "r2": _NUM_OR_NULL,
        "residual_sd": _NUM_OR_NULL,
        "legacy_range": {"type": "array", "items": {"type": "number"}},
        "dropped_outliers": {"type": "array", "items": _ID},
    },
}

MANIFEST = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "manifest",
    "type": "object",
    "required": [
        "generated_at",
        "run_id",
        "primary_view",
        "views",
        "gpu_count",
        "ranked_counts",
        "zones",
        "normalization",
        "sources",
        "benchmark_suites",
    ],
    "properties": {
        "generated_at": {"type": "string"},
        "run_id": {"type": "string"},
        "primary_view": {"type": "string"},
        "views": {"type": "array", "items": {"type": "string"}},
        "gpu_count": {"type": "integer", "minimum": 0},
        "ranked_counts": {"type": "object", "additionalProperties": {"type": "integer"}},
        "zones": {"type": "object", "additionalProperties": ZONE_META},
        "normalization": {
            "type": "object",
            "required": ["method", "transforms"],
            "properties": {
                "method": {"enum": ["linear", "ratio_trimmed", "piecewise"]},
                "transforms": {"type": "array", "items": TRANSFORM},
            },
        },
        "benchmark_suites": {"type": "object", "additionalProperties": {"type": "string"}},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "url", "kind"],
                "properties": {
                    "name": {"type": "string"},
                    "url": {"type": "string"},
                    "kind": {"enum": ["benchmarks", "prices"]},
                    "fetched_at": {"type": ["string", "null"]},
                },
            },
        },
        "anomalies": {"type": "array"},
        "unresolved": {"type": "array"},
        "needs_review": {"type": "boolean"},
    },
}

GPU = {
    "type": "object",
    "required": [
        "gpu_id",
        "vendor",
        "architecture",
        "series",
        "display_name",
        "release_year",
        "tdp_w",
        "vram_gb",
        "is_active",
        "benchmarks",
        "rankings",
        "current_price",
        "retailer_links",
        "price_stats",
    ],
    "properties": {
        "gpu_id": _ID,
        "component_type": {"type": "string"},
        "vendor": {"enum": ["NVIDIA", "AMD", "Intel"]},
        "architecture": {"type": "string"},
        "series": {"type": "string"},
        "display_name": {"type": "string"},
        "release_year": {"type": "integer"},
        "msrp_usd": _NUM_OR_NULL,
        "tdp_w": {"type": ["integer", "null"]},
        "vram_gb": {"type": ["integer", "null"]},
        "is_active": {"type": "boolean"},
        "benchmarks": {
            "type": "object",
            "additionalProperties": {"type": "object", "additionalProperties": BENCH_CELL},
        },
        "rankings": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["rank", "cost_per_fps", "zone"],
                "properties": {
                    "rank": {"type": "integer", "minimum": 1},
                    "cost_per_fps": {"type": "number"},
                    "zone": {"enum": ["great", "fair", "poor"]},
                },
            },
        },
        "current_price": {
            "type": ["object", "null"],
            "required": ["price", "retailer", "url", "condition", "fetched_at"],
            "properties": {
                "price": {"type": "number"},
                "retailer": {"type": "string"},
                "url": {"type": "string"},
                "condition": {"type": "string"},
                "fetched_at": {"type": "string"},
            },
        },
        "retailer_links": {"type": "object", "additionalProperties": {"type": "string"}},
        "price_stats": {
            "type": "object",
            "properties": {
                "min_90d": _NUM_OR_NULL,
                "median_90d": _NUM_OR_NULL,
                "n_points": {"type": "integer"},
            },
        },
    },
}

GPUS = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "gpus",
    "type": "array",
    "items": GPU,
}

RANKINGS = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "rankings",
    "type": "object",
    "additionalProperties": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["gpu_id", "rank", "fps", "price", "cost_per_fps", "zone", "normalized"],
            "properties": {
                "gpu_id": _ID,
                "rank": {"type": "integer", "minimum": 1},
                "fps": {"type": "number"},
                "price": {"type": "number"},
                "cost_per_fps": {"type": "number"},
                "zone": {"enum": ["great", "fair", "poor"]},
                "normalized": {"type": "boolean"},
            },
        },
    },
}

PRICE_HISTORY = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "price_history",
    "type": "object",
    "additionalProperties": {
        "type": "array",
        "items": {
            "type": "array",
            "prefixItems": [{"type": "string"}, {"type": "number"}, {"type": "string"}],
            "minItems": 3,
            "maxItems": 3,
        },
    },
}

CHANGELOG = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "changelog",
    "type": "array",
    "items": {
        "type": "object",
        "required": ["run_id", "generated_at", "added_gpus", "removed_gpus", "price_changes"],
        "properties": {
            "run_id": {"type": "string"},
            "generated_at": {"type": "string"},
            "added_gpus": {"type": "array", "items": _ID},
            "removed_gpus": {"type": "array", "items": _ID},
            "price_changes": {"type": "array"},
            "benchmark_suite_changed": {"type": "boolean"},
            "unresolved_count": {"type": "integer"},
            "notes": {"type": "array", "items": {"type": "string"}},
        },
    },
}

SCHEMAS = {
    "manifest": MANIFEST,
    "gpus": GPUS,
    "rankings": RANKINGS,
    "price_history": PRICE_HISTORY,
    "changelog": CHANGELOG,
}


def write_schema_files(directory: Path = SCHEMA_DIR) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, schema in SCHEMAS.items():
        (directory / f"{name}.schema.json").write_text(
            json.dumps(schema, indent=2) + "\n", encoding="utf-8"
        )
