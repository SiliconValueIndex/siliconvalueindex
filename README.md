# SiliconValueIndex

GPU value rankings built on real retail prices and benchmark FPS.

I started this because I was trying to pick a GPU for my own build and kept running into the same problem: review sites rank cards by raw performance, not by what you actually get for your money. A card that scores 20% higher but costs 60% more isn't a better buy, it's just a more expensive one. So I built the index I wanted to read.

→ [siliconvalueindex.com](https://siliconvalueindex.com)

## What it does

For every card and every view (resolution and rendering mode):

**cost per FPS = current price ÷ average FPS**

Lower is better. No weighting, no opinion. The site has a filterable ranking board, a page per card with specs, price history and retailer links, a side-by-side compare tool, and a methodology page that shows its working.

## How it is built

Two parts, one contract.

- `src/svi/` is a Python pipeline. It scrapes benchmarks and prices, resolves retailer and reviewer names to stable `gpu_id`s, normalizes FPS across Tom's Hardware test-suite versions, scores every view, and writes `data/site/*.json` validated against `schemas/`.
- `site/` is an Astro static site that imports those JSON files at build time. No server, no database.

```
data/
  reference/   gpu_master_list.csv (registry, frozen gpu_ids), aliases.csv,
               price_overrides.csv, config.yaml (every threshold lives here)
  raw/         benchmark CSVs and price snapshots as fetched
  processed/   benchmarks.csv (long format), prices_history.csv (append-only)
  site/        manifest, gpus, rankings, price_history, changelog, review_report.md
schemas/       JSON Schema for each site file
src/svi/       config, ids (name resolution), normalize, scoring, prices, export, cli
site/          Astro pages: /, /gpu/<id>/, /compare/, /methodology/, /data/
tests/         pytest; tests/golden holds the live-site numbers the seed must reproduce
```

## Methodology in short

- **Benchmarks** come from Tom's Hardware's GPU hierarchy: rasterization and ray tracing at 1080p, 1440p and 4K ultra.
- **Older cards.** Tom's replaces its game suite periodically and does not retest every card. For cards that only exist in an older suite we fit a straight line from old-suite FPS to current-suite FPS on the cards present in both, and translate along it. Those cards are marked "est." everywhere. The fit, its parameters and the excluded outliers are published in `manifest.json` and drawn on the methodology page. The original single-ratio method is kept as `ratio_trimmed` in `config.yaml` for regression tests.
- **Prices** are the lowest valid price for a new, in-stock unit. Rejected listings (bundles, laptops, refurbished, prices outside 35% to 300% of the recent median) are kept in the history with a reason. Every price carries its retailer and date.
- **Zones.** The 1440p rasterization board uses fixed thresholds ($8 and $12 per frame). Other views use percentile bands because a frame costs different amounts at different resolutions.

## Running it locally

```bash
pip install -e ".[dev]"
svi seed              # once: convert the original CSVs into the new tables
svi build --offline   # normalize, score, export data/site, write the review report
pytest

cd site
npm ci
npm run dev           # http://localhost:4321
```

`svi build` without `--offline` also fetches Tom's Hardware and Best Buy (needs `BESTBUY_API_KEY` in the environment).

## Automated refresh

`.github/workflows/refresh-data.yml` runs the pipeline on a schedule. A clean run commits the new data to `main` and the site redeploys. If anything needs a human (a name that could not be matched, a card with no valid price, a price move over 25%, a benchmark suite change, a fetch failure) the run opens a pull request with the review report as its body. Fixing it is a one-line edit to `aliases.csv`, `price_overrides.csv` or the registry.

## Roadmap

- CPU value index (Tom's CPU hierarchy has the same shape)
- "Pick a game, get a CPU and GPU" builder
- Used-market pricing
- Buy or wait signal from price history

## Data sources

- Benchmarks: [Tom's Hardware GPU Hierarchy](https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html)
- Prices: Best Buy Products API, manual overrides; Newegg and Amazon as search links
