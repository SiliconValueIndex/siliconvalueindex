# Refresh report `seed-parity`
**Needs review: YES**
- 1 benchmark anomaly(ies)

## Fetch failures
_none_

## Unresolved names
Add a row to `data/reference/aliases.csv` (alias,gpu_id,source) or a new registry entry.

_none_

## Active GPUs with no valid current price
These drop out of the rankings. Add a row to `data/reference/price_overrides.csv` if needed.

_none_

## Price moves >= 25%
_none_

## Benchmark anomalies
| type | gpu_id | resolution | mode | residual | detail |
|---|---|---|---|---|---|
| overlap_residual | nvidia-rtx-4070-ti-super | 1440p | raster | 24.6 | 2022->2026-03 fit residual exceeds 2.5 sd (7.7) |

## Changes this run
- Added GPUs: none
- Removed GPUs: none
- Price changes >= 5%: 0
- Benchmark suite changed: False

## Ranked counts
- `1440p_raster`: 59
