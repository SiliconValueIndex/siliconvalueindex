# Refresh report `gh-38658277574-reviewed`
**Needs review: YES**
- 30 unresolved name(s)
- 10 price move(s) >= 25%
- 2 benchmark anomaly(ies)

## Fetch failures
_none_

## Unresolved names
Add a row to `data/reference/aliases.csv` (alias,gpu_id,source) or a new registry entry.

| source | raw_name | candidates |
|---|---|---|
| newegg | GIGABYTE AORUS GeForce RTX 5060 Graphics AORUS GeForce RTX 5060 ARI |  |
| newegg | MSI Gaming GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 8G GAMING OC |  |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLEOC ICE-16GD |  |
| newegg | MSI Ventus GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 8G VENTUS 3X OC |  |
| newegg | ZOTAC Twin Edge OC GeForce RTX 5060 Ti Video Card ZT-B50620H-10A |  |
| newegg | GIGABYTE WindForce GeForce RTX 5060 Ti Graphics Card GV-N506TWF2OC-16GD |  |
| newegg | GIGABYTE WINDFORCE GeForce RTX 5060 Ti Graphics Card GV-N506TWF2MAX-8GD |  |
| newegg | MSI Ventus GeForce RTX 5060 Ti Graphics Card (RTX 5060 Ti 16G VENTUS 2X OC BLACK PLUS) |  |
| newegg | ASUS T1 GeForce RTX 5060 Ti Graphics Card T1-RTX5060TI-O8G-GAMING |  |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLEMAX OC-16GD |  |
| newegg | ASUS Dual GeForce RTX 5060 Ti Graphics Card DUAL-RTX5060TI-O8G |  |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLEMAX OC-8GD |  |
| newegg | GIGABYTE Gaming GeForce RTX 5060 Ti Graphics Card GV-N506TGAMING OC-8GD |  |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLEOC ICE-8GD |  |
| newegg | GIGABYTE WindForce GeForce RTX 5060 Ti Graphics Card GV-N506TWF2-8GD |  |
| newegg | MSI Gaming GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G GAMING OC |  |
| newegg | MSI Ventus GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G VENTUS 3X OC |  |
| newegg | GIGABYTE Eagle GeForce RTX 5060 Ti Graphics Card GV-N506TEAGLE OC-8GD |  |
| newegg | GIGABYTE Gaming GeForce RTX 5060 Ti Graphics Card GV-N506TGAMING OC-16GD |  |
| newegg | MSI Gaming GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G GAMING TRIO OC |  |
| newegg | MSI Gaming GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 8G GAMING TRIO OC |  |
| newegg | GIGABYTE WindForce GeForce RTX 5060 Ti Graphics Card GV-N506TWF2OC-8GD |  |
| newegg | MSI Ventus GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G VENTUS 2X OC PLUS |  |
| newegg | GIGABYTE AERO GeForce RTX 5060 Ti Graphics Card GV-N506TAERO OC-8GD |  |
| newegg | MSI SHADOW GeForce RTX 5060 Ti Graphics Card RTX 5060 Ti 16G SHADOW 2X OC PLUS |  |
| newegg | GIGABYTE AORUS GeForce RTX 5060 Ti Graphics card AORUS RTX 5060 TI AI BOX |  |
| newegg | Bitspower NEBULA GeForce RTX 5090 MSI Suprim / Gaming Trio / Vanguard |  |
| newegg | BITSPOWER NEBULA CLASSIC GeForce RTX 5090 VENTUS |  |
| newegg | Bitspower Nebula Classic GeForce RTX 5090 Founders Edition |  |
| newegg | Bitspower NEBULA GeForce RTX 5090 ASUS TUF Gaming |  |

## Active GPUs with no valid current price
These drop out of the rankings. Add a row to `data/reference/price_overrides.csv` if needed.

- `amd-rx-6650-xt`

## Price moves >= 25%
| gpu_id | from | to | pct |
|---|---|---|---|
| nvidia-rtx-3070 | 325.0 | 645.0 | 98.5 |
| amd-rx-7900-xtx | 1066.03 | 1799.0 | 68.8 |
| amd-rx-9060-xt | 345.99 | 509.99 | 47.4 |
| nvidia-rtx-5060-ti-16gb | 549.99 | 799.99 | 45.5 |
| nvidia-rtx-5060-ti-8gb | 379.99 | 529.99 | 39.5 |
| nvidia-rtx-5080 | 1249.99 | 1699.99 | 36.0 |
| nvidia-rtx-3060 | 339.0 | 459.99 | 35.7 |
| nvidia-rtx-2080-ti | 695.0 | 895.0 | 28.8 |
| nvidia-rtx-2060 | 469.0 | 599.0 | 27.7 |
| nvidia-rtx-2070 | 675.0 | 495.0 | -26.7 |

## Benchmark anomalies
| type | gpu_id | resolution | mode | residual | detail |
|---|---|---|---|---|---|
| overlap_residual | nvidia-rtx-4070-ti-super | 1440p | raster | -30.6 | 2026-03->2026-09-16 fit residual exceeds 2.5 sd (7.0) |
| overlap_residual | nvidia-rtx-4090 | 1440p | raster | 14.5 | 2022->2026-09-16 fit residual exceeds 2.5 sd (3.9) |

## Changes this run
- Added GPUs: none
- Removed GPUs: none
- Price changes >= 5%: 19
- Benchmark suite changed: False

## Ranked counts
- `1080p_raster`: 45
- `1080p_rt`: 45
- `1440p_raster`: 61
- `1440p_rt`: 45
- `4k_raster`: 45
- `4k_rt`: 45

## Notes
- Newegg: 83 valid of 85 observations
- Manual overrides applied: 2
