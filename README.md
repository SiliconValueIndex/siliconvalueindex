# SiliconValueIndex

GPU value rankings built on real pricing data and normalized benchmark performance.

I started this because I was trying to pick a GPU for my own build and kept running into the same problem — review sites rank cards by raw performance, not by what you actually get for your money. A card that scores 20% higher but costs 60% more isn't a better buy, it's just a more expensive one. So I built the index I wanted to read.

---

## What it does

Takes benchmark FPS data, normalizes it across generations so old and new cards are comparable, then divides by current market price. The result is a single number: **cost per FPS**. Lower is better. No weighting, no opinion, just math.

Current index: **59 GPUs at 1440p Ultra** — updated monthly.

→ [siliconvalueindex.com](https://siliconvalueindex.com)

---

## Methodology

**Benchmark data** is sourced from Tom's Hardware's GPU Hierarchy — one consistent test suite across all cards.

**The normalization problem:** Tom's updated their benchmark suite in 2022. Modern cards are tested with heavier, more demanding titles, so a legacy card's raw FPS score is inflated relative to a current card tested under the same conditions. Comparing them directly would be misleading.

**The fix:** I identified ~20 GPUs that appear in both the old and new benchmark suites and computed the ratio between their scores. The trimmed mean of those ratios gives a scale factor (~0.703) that converts legacy scores to modern equivalents. If a card appears in both suites, the modern score is used as-is.

**Pricing** is pulled from Newegg monthly — lowest available new price from a reputable AIB, non-OC model. No gray market, no flash sales.

**Cost per FPS** = `current_price / normalized_fps`

---

## Repo structure

```
data/
  raw/benchmarks/       # source benchmark CSVs (Tom's Hardware)
  reference/            # GPU master list with TDP, VRAM, architecture
  processed/            # normalized benchmarks, cleaned pricing
outputs/                # dated rankings CSVs, charts
src/
  processing/           # normalization pipeline
  scoring/              # cost-per-FPS calculation
  visualization/        # chart generation (PNG + HTML)
```

---

## Running it locally

```bash
pip install pandas matplotlib

# Normalize benchmarks + compute rankings
python src/processing/build_benchmarks.py
python src/scoring/cost_per_frame.py

# Generate charts
python src/visualization/generate_charts.py
```

Outputs land in `outputs/` dated to today.

---

## Roadmap

- [ ] 1080p tier (budget card focus)
- [ ] Used market pricing (Post 2)
- [ ] Buy/Wait signal based on historical price distribution
- [ ] Automated price refresh
- [ ] RAM and SSD value indices

---

## Data sources

- Benchmarks: [Tom's Hardware GPU Hierarchy](https://www.tomshardware.com/reviews/gpu-hierarchy,4388.html)
- Pricing: [Newegg](https://www.newegg.com)
