"""Load data/reference/config.yaml into typed settings. Single source for thresholds."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
REFERENCE_DIR = DATA_DIR / "reference"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SITE_DATA_DIR = DATA_DIR / "site"
SCHEMA_DIR = REPO_ROOT / "schemas"
CONFIG_PATH = REFERENCE_DIR / "config.yaml"

Resolution = Literal["1080p", "1440p", "4k"]
Mode = Literal["raster", "rt"]
NormalizationMethod = Literal["linear", "ratio_trimmed", "piecewise"]
ZoneMode = Literal["absolute", "percentile"]


class ProjectConfig(BaseModel):
    name: str
    site_url: str
    repo_url: str


class BenchmarksConfig(BaseModel):
    source: str
    current_url: str
    legacy_url: str
    resolutions: list[Resolution]
    modes: list[Mode]
    setting: str = "ultra"
    primary_view: str = "1440p_raster"


class NormalizationConfig(BaseModel):
    method: NormalizationMethod = "linear"
    trim_fraction: float = Field(0.10, ge=0, lt=0.5)
    min_overlap: int = Field(3, ge=2)
    outlier_mad: float = 3.0
    max_extrapolation: float = 0.15


class AbsoluteZones(BaseModel):
    great_max: float
    fair_max: float


class PercentileZones(BaseModel):
    great: float = Field(ge=0, le=1)
    fair: float = Field(ge=0, le=1)


class ZonesConfig(BaseModel):
    default_mode: ZoneMode = "percentile"
    absolute: AbsoluteZones
    percentile: PercentileZones
    per_view: dict[str, ZoneMode] = Field(default_factory=dict)

    def mode_for(self, view: str) -> ZoneMode:
        return self.per_view.get(view, self.default_mode)


class PlayabilityConfig(BaseModel):
    default_min_fps: float = 40.0
    min_fps: dict[str, float] = Field(default_factory=dict)

    def floor_for(self, view: str) -> float:
        return self.min_fps.get(view, self.default_min_fps)


class PricingConfig(BaseModel):
    retailers: list[str]
    currency: str = "USD"
    price_floor_ratio: float = 0.35
    price_ceiling_ratio: float = 3.0
    stale_days: int = 60
    enforce_stale: bool = False
    review_move_pct: float = 25.0
    bestbuy_category_id: str = "abcat0507002"


class GuardsConfig(BaseModel):
    max_gpu_count_drop_pct: float = 10.0


class Config(BaseModel):
    project: ProjectConfig
    benchmarks: BenchmarksConfig
    normalization: NormalizationConfig
    zones: ZonesConfig
    playability: PlayabilityConfig = Field(default_factory=PlayabilityConfig)
    pricing: PricingConfig
    guards: GuardsConfig

    @property
    def views(self) -> list[str]:
        return [f"{r}_{m}" for r in self.benchmarks.resolutions for m in self.benchmarks.modes]


def load_config(path: Path | None = None) -> Config:
    with open(path or CONFIG_PATH, encoding="utf-8") as fh:
        return Config.model_validate(yaml.safe_load(fh))


@lru_cache(maxsize=1)
def get_config() -> Config:
    return load_config()


def view_key(resolution: str, mode: str) -> str:
    return f"{resolution}_{mode}"


def split_view(view: str) -> tuple[str, str]:
    resolution, mode = view.rsplit("_", 1)
    return resolution, mode
