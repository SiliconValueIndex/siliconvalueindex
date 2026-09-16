# Refresh report `scrape-2026-09-16`
**Needs review: YES**
- GPU set changed
- benchmark suite version changed
- 2 benchmark anomaly(ies)

## Fetch failures
_none_

## Unresolved names
Add a row to `data/reference/aliases.csv` (alias,gpu_id,source) or a new registry entry.

_none_

## Active GPUs with no valid current price
These drop out of the rankings. Add a row to `data/reference/price_overrides.csv` if needed.

- `amd-rx-6650-xt`
- `nvidia-rtx-3050`
- `nvidia-rtx-5050`

## Price moves >= 25%
_none_

## Benchmark anomalies
| type | gpu_id | resolution | mode | residual | detail |
|---|---|---|---|---|---|
| overlap_residual | nvidia-rtx-4070-ti-super | 1440p | raster | -30.6 | 2026-03->2026-09-16 fit residual exceeds 2.5 sd (7.0) |
| overlap_residual | nvidia-rtx-4090 | 1440p | raster | 14.5 | 2022->2026-09-16 fit residual exceeds 2.5 sd (3.9) |

## Changes this run
- Added GPUs: amd-rx-6650-xt, nvidia-rtx-3050, nvidia-rtx-5050
- Removed GPUs: none
- Price changes >= 5%: 0
- Benchmark suite changed: True

## Ranked counts
- `1080p_raster`: 43
- `1080p_rt`: 43
- `1440p_raster`: 59
- `1440p_rt`: 43
- `4k_raster`: 43
- `4k_rt`: 43

## Notes
- Tom's Hardware: 288 cells parsed, suite 2026-09-16 (94% of overlapping cards moved > 3% vs 2026-03)
