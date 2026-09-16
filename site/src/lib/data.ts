// Typed access to the pipeline output in ../../data/site. These imports are resolved
// at build time, so the site is fully static.
import manifestJson from '../../../data/site/manifest.json';
import gpusJson from '../../../data/site/gpus.json';
import rankingsJson from '../../../data/site/rankings.json';
import priceHistoryJson from '../../../data/site/price_history.json';
import changelogJson from '../../../data/site/changelog.json';

export type Vendor = 'NVIDIA' | 'AMD' | 'Intel';
export type Zone = 'great' | 'fair' | 'poor';

export interface BenchCell {
  fps: number;
  raw_fps: number;
  pct_of_top: number | null;
  suite_version: string;
  normalized: boolean;
}
export interface RankCell {
  rank: number;
  cost_per_fps: number;
  zone: Zone;
}
export interface CurrentPrice {
  price: number;
  retailer: string;
  url: string;
  condition: string;
  fetched_at: string;
}
export interface Gpu {
  gpu_id: string;
  component_type: string;
  vendor: Vendor;
  architecture: string;
  series: string;
  display_name: string;
  release_year: number;
  msrp_usd: number | null;
  tdp_w: number | null;
  vram_gb: number | null;
  is_active: boolean;
  benchmarks: Record<string, Record<string, BenchCell>>;
  rankings: Record<string, RankCell>;
  current_price: CurrentPrice | null;
  retailer_links: Record<string, string>;
  price_stats: { min_90d: number | null; median_90d: number | null; n_points: number };
}
export interface RankingRow {
  gpu_id: string;
  rank: number;
  fps: number;
  price: number;
  cost_per_fps: number;
  zone: Zone;
  normalized: boolean;
}
export interface ZoneMeta {
  mode: 'absolute' | 'percentile';
  great_max: number;
  fair_max: number;
}
export interface Transform {
  resolution: string;
  mode: string;
  from_suite: string;
  to_suite: string;
  method: 'linear' | 'ratio_trimmed' | 'piecewise';
  params: Record<string, number | number[]>;
  overlap_ids: string[];
  n_overlap: number;
  n_used: number;
  r2: number | null;
  residual_sd: number | null;
  legacy_range: [number, number];
  dropped_outliers: string[];
  overlap_points: [string, number, number][];
}
export interface Manifest {
  generated_at: string;
  run_id: string;
  primary_view: string;
  views: string[];
  gpu_count: number;
  ranked_counts: Record<string, number>;
  zones: Record<string, ZoneMeta>;
  normalization: { method: string; transforms: Transform[] };
  benchmark_suites: Record<string, string>;
  sources: { name: string; url: string; kind: string; fetched_at: string | null }[];
  anomalies: Record<string, unknown>[];
  unresolved: Record<string, unknown>[];
  needs_review: boolean;
}
export interface ChangelogEntry {
  run_id: string;
  generated_at: string;
  added_gpus: string[];
  removed_gpus: string[];
  price_changes: { gpu_id: string; from: number; to: number; pct: number }[];
  benchmark_suite_changed: boolean;
  unresolved_count: number;
  notes: string[];
}

export const manifest = manifestJson as unknown as Manifest;
export const gpus = gpusJson as unknown as Gpu[];
export const rankings = rankingsJson as unknown as Record<string, RankingRow[]>;
export const priceHistory = priceHistoryJson as unknown as Record<string, [string, number, string][]>;
export const changelog = changelogJson as unknown as ChangelogEntry[];

export const gpuById: Record<string, Gpu> = Object.fromEntries(gpus.map((g) => [g.gpu_id, g]));

export const VIEW_LABELS: Record<string, string> = {
  '1080p': '1080p',
  '1440p': '1440p',
  '4k': '4K',
  raster: 'Rasterization',
  rt: 'Ray tracing',
};

export function splitView(view: string): { resolution: string; mode: string } {
  const i = view.lastIndexOf('_');
  return { resolution: view.slice(0, i), mode: view.slice(i + 1) };
}

export function viewLabel(view: string): string {
  const { resolution, mode } = splitView(view);
  return `${VIEW_LABELS[resolution] ?? resolution}, ${(VIEW_LABELS[mode] ?? mode).toLowerCase()}`;
}

export const money = (n: number, digits = 0) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: digits, minimumFractionDigits: digits });

export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });

export function primaryStats() {
  const rows = rankings[manifest.primary_view] ?? [];
  if (!rows.length) return null;
  const best = rows[0];
  const worst = rows[rows.length - 1];
  return {
    best,
    worst,
    count: rows.length,
    spread: worst.cost_per_fps / best.cost_per_fps,
    priceDate: gpuById[best.gpu_id]?.current_price?.fetched_at ?? manifest.generated_at,
  };
}
