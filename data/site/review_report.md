# Refresh report `gh-39039129310`
**Needs review: YES**
- 28 unresolved name(s)
- 2 benchmark anomaly(ies)

## Fetch failures
_none_

## Unresolved names
Add a row to `data/reference/aliases.csv` (alias,gpu_id,source) or a new registry entry.

| source | raw_name | candidates |
|---|---|---|
| newegg | GIGABYTE AORUS GeForce RTX 5060 Graphics AORUS GeForce RTX 5060 ARI |  |
| newegg | ZOTAC Twin Edge OC GeForce RTX 5060 Ti Video Card ZT-B50620H-10A | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE WINDFORCE GeForce RTX 5060 Ti Graphics Card GV-N506TWF2MAX-8GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | ASUS T1 GeForce RTX 5060 Ti Graphics Card T1-RTX5060TI-O8G-GAMING | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | ASUS Dual GeForce RTX 5060 Ti Graphics Card DUAL-RTX5060TI-O8G | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLEMAX OC-8GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE WindForce GeForce RTX 5060 Ti Graphics Card GV-N506TWF2OC-8GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE WindForce GeForce RTX 5060 Ti Graphics Card GV-N506TWF2-8GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLEOC ICE-8GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE Gaming GeForce RTX 5060 Ti Graphics Card GV-N506TGAMING OC-8GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLE OC-8GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE AERO GeForce RTX 5060 Ti Graphics Card GV-N506TAERO OC-8GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | MSI Gaming GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 8G GAMING TRIO OC | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLEOC ICE-16GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE WindForce GeForce RTX 5060 Ti Graphics Card GV-N506TWF2OC-16GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | MSI Ventus GeForce RTX 5060 Ti Graphics Card (RTX 5060 Ti 16G VENTUS 2X OC BLACK PLUS) | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLEMAX OC-16GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | MSI SHADOW GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G SHADOW 2X OC PLUS | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | MSI Ventus GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G VENTUS 2X OC PLUS | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE AORUS GeForce RTX 5060 Ti Graphics card AORUS RTX 5060 TI AI BOX | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | MSI Gaming GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G GAMING OC | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | GIGABYTE Gaming GeForce RTX 5060 Ti Graphics Card GV-N506TGAMING OC-16GD | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | MSI Gaming GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G GAMING TRIO OC | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | MSI Ventus GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G VENTUS 3X OC | nvidia-rtx-5060-ti-8gb (100), nvidia-rtx-5060-ti-16gb (100) |
| newegg | Bitspower NEBULA GeForce RTX 5090 MSI Suprim / Gaming Trio / Vanguard |  |
| newegg | BITSPOWER NEBULA CLASSIC GeForce RTX 5090 VENTUS |  |
| newegg | Bitspower Nebula Classic GeForce RTX 5090 Founders Edition |  |
| newegg | Bitspower NEBULA GeForce RTX 5090 ASUS TUF Gaming |  |

## Active GPUs with no valid current price
These drop out of the rankings. Add a row to `data/reference/price_overrides.csv` if needed.

- `amd-rx-6650-xt`

## Price moves >= 25%
_none_

## Benchmark anomalies
| type | gpu_id | resolution | mode | residual | detail |
|---|---|---|---|---|---|
| overlap_residual | nvidia-rtx-4070-ti-super | 1440p | raster | -30.6 | 2026-03->2026-09-16 fit residual exceeds 2.5 sd (7.0) |
| overlap_residual | nvidia-rtx-4090 | 1440p | raster | 14.5 | 2022->2026-09-16 fit residual exceeds 2.5 sd (3.9) |

## Changes this run
- Added GPUs: none
- Removed GPUs: none
- Price changes >= 5%: 1
- Benchmark suite changed: False

## Ranked counts
- `1080p_raster`: 45
- `1080p_rt`: 45
- `1440p_raster`: 61
- `1440p_rt`: 45
- `4k_raster`: 45
- `4k_rt`: 45

## Notes
- Newegg: 75 valid of 77 observations
- Manual overrides applied: 2
