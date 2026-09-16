"""Typed records shared by scrapers, normalization, scoring and export."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ComponentType = Literal["gpu", "cpu"]
Condition = Literal["new", "open_box", "refurb", "used"]


class GpuRegistryRow(BaseModel):
    """One row of data/reference/gpu_master_list.csv. gpu_id is frozen forever."""

    gpu_id: str = Field(pattern=r"^[a-z]+-[a-z0-9-]+$")
    component_type: ComponentType = "gpu"
    vendor: Literal["NVIDIA", "AMD", "Intel"]
    architecture: str
    series: str
    display_name: str
    release_year: int
    msrp_usd: float | None = None
    tdp_w: int | None = None
    vram_gb: int | None = None
    is_active: bool = True
    notes: str = ""


class BenchmarkRecord(BaseModel):
    """Long-format benchmark observation. One per (gpu, source, suite, resolution, mode)."""

    gpu_id: str
    component_type: ComponentType = "gpu"
    source: str
    suite_version: str
    resolution: str
    setting: str = "ultra"
    mode: str
    fps: float = Field(gt=0)
    pct_of_top: float | None = None
    fetched_at: datetime
    snapshot_ref: str = ""


class PriceRecord(BaseModel):
    """Append-only price observation. Invalid rows are kept with a reason for audit."""

    gpu_id: str
    retailer: str
    sku: str = ""
    title_raw: str = ""
    price: float | None = None
    currency: str = "USD"
    url: str = ""
    condition: Condition = "new"
    in_stock: bool = True
    is_valid: bool = True
    invalid_reason: str = ""
    fetched_at: datetime
    run_id: str = ""


class UnresolvedName(BaseModel):
    """A source name the resolver could not map to a gpu_id. Surfaces in the review report."""

    source: str
    raw_name: str
    canonical: str
    candidates: list[tuple[str, float]] = Field(default_factory=list)
