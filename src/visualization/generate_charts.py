"""
generate_charts.py
SiliconValueIndex — GPU Value Rankings
Generates both a high-res PNG (Reddit) and interactive HTML (landing page).

Usage (from repo root):
    python src/visualization/generate_charts.py

Outputs (auto-dated):
    outputs/silicon_value_index_YYYY-MM-DD.png
    outputs/gpu_rankings_chart_YYYY-MM-DD.html

Dependencies:
    pip install matplotlib pandas
"""

import os
import glob
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
from datetime import date

# ── Config ────────────────────────────────────────────────────────────────────

TODAY       = date.today().isoformat()
OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "outputs")
PNG_OUT     = os.path.join(OUTPUTS_DIR, f"silicon_value_index_{TODAY}.png")
HTML_OUT    = os.path.join(OUTPUTS_DIR, f"gpu_rankings_chart_{TODAY}.html")

VENDOR_COLORS = {"NVIDIA": "#76b900", "AMD": "#ED1C24", "Intel": "#0071C5"}
BG    = "#0d1117"
PANEL = "#161b22"
TEXT  = "#e6edf3"
GRID  = "#21262d"
MUTED = "#8b949e"

FOOTER = ("Benchmarks via Tom's Hardware GPU Hierarchy  ·  "
          "Normalized & scored by SiliconValueIndex  ·  siliconvalueindex.com")

# ── Load latest rankings CSV ──────────────────────────────────────────────────

def detect_vendor(name):
    n = name.upper()
    if any(x in n for x in ["RTX", "GTX", "NVIDIA"]):
        return "NVIDIA"
    if any(x in n for x in ["RX ", "RADEON", "VEGA"]):
        return "AMD"
    if any(x in n for x in ["ARC", "INTEL"]):
        return "Intel"
    return "Other"

def load_rankings():
    pattern = os.path.join(OUTPUTS_DIR, "gpu_rankings_new_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No gpu_rankings_new_*.csv found in {OUTPUTS_DIR}")
    latest = files[-1]
    print(f"Loading: {latest}")
    df = pd.read_csv(latest)
    # Normalise column names to what the rest of the script uses
    df = df.rename(columns={
        "gpu_model":         "gpu",
        "new_cost_per_fps":  "cost_per_fps",
        "Link":              "newegg_url",
    })
    df = df.dropna(subset=["cost_per_fps", "new_price"]).copy()
    df["vendor"] = df["gpu"].apply(detect_vendor)
    df = df.sort_values("cost_per_fps").reset_index(drop=True)
    return df

# ── PNG ───────────────────────────────────────────────────────────────────────

def generate_png(df):
    rcParams['text.antialiased'] = True

    names  = df["gpu"].tolist()
    values = df["cost_per_fps"].tolist()
    colors = [VENDOR_COLORS.get(v, "#888888") for v in df["vendor"]]

    fig, ax = plt.subplots(figsize=(22, 32))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(PANEL)

    ax.axvspan(0,  8,  alpha=0.08, color="#2ea043", zorder=0)
    ax.axvspan(8,  12, alpha=0.05, color="#d29922", zorder=0)
    ax.axvspan(12, 30, alpha=0.05, color="#f85149", zorder=0)

    ax.text(4,  -1.4, "GREAT VALUE", color="#2ea043", fontsize=9, fontweight="bold", ha="center", alpha=0.8)
    ax.text(10, -1.4, "FAIR VALUE",  color="#d29922", fontsize=9, fontweight="bold", ha="center", alpha=0.8)
    ax.text(22, -1.4, "POOR VALUE",  color="#f85149", fontsize=9, fontweight="bold", ha="center", alpha=0.8)

    y_pos = np.arange(len(names))
    ax.barh(y_pos, values, color=colors, height=0.68, zorder=2, edgecolor="none")

    for i, val in enumerate(values):
        ax.text(val + 0.25, i, f"${val:.2f}", va="center", ha="left",
                color=TEXT, fontsize=8.5, fontweight="500")

    for x in [8, 12]:
        ax.axvline(x=x, color=GRID, linewidth=1.5, linestyle="--", alpha=0.7, zorder=1)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, color=TEXT, fontsize=10.5)
    ax.invert_yaxis()
    ax.set_xlabel("Cost Per FPS ($/FPS) — Lower is Better", color=MUTED, fontsize=12, labelpad=14)
    ax.tick_params(colors=TEXT, labelsize=10)
    ax.spines[:].set_visible(False)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="x", colors=MUTED)
    ax.set_xlim(0, 31)

    month_label = date.today().strftime("%B %Y").upper()
    fig.text(0.5, 0.975, f"GPU VALUE INDEX — {month_label}",
             ha="center", va="top", fontsize=24, color=TEXT, fontweight="bold", fontfamily="monospace")
    fig.text(0.5, 0.96,
             f"Cost per Normalized FPS  ·  {len(df)} GPUs  ·  1440p Ultra  ·  Prices via Newegg  ·  {month_label}",
             ha="center", va="top", fontsize=10.5, color=MUTED)

    ax.legend(
        handles=[mpatches.Patch(color=c, label=v) for v, c in VENDOR_COLORS.items()],
        loc="lower right", framealpha=0.2, facecolor=PANEL,
        edgecolor=GRID, labelcolor=TEXT, fontsize=11
    )

    fig.text(0.5, 0.008, FOOTER, ha="center", va="bottom",
             fontsize=8.5, color="#484f58", style="italic")

    plt.tight_layout(rect=[0, 0.015, 1, 0.955])
    plt.savefig(PNG_OUT, dpi=300, bbox_inches="tight", facecolor=BG)
    plt.close()
    print(f"PNG saved: {PNG_OUT}")

# ── HTML ──────────────────────────────────────────────────────────────────────

def generate_html(df):
    names   = df["gpu"].tolist()
    values  = df["cost_per_fps"].tolist()
    vendors = df["vendor"].tolist()
    links   = df["newegg_url"].tolist() if "newegg_url" in df.columns else [""] * len(df)

    month_label = date.today().strftime("%B %Y").upper()
    best      = min(values)
    worst     = max(values)
    best_gpu  = names[values.index(best)]
    worst_gpu = names[values.index(worst)]
    spread    = f"{worst/best:.1f}×"

    import json
    labels_js  = json.dumps(names)
    values_js  = json.dumps([round(v, 3) for v in values])
    vendors_js = json.dumps(vendors)
    links_js   = json.dumps(links)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SiliconValueIndex — GPU Value Rankings {month_label}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap');
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --bg: #0d1117; --panel: #161b22; --border: #21262d;
    --text: #e6edf3; --muted: #8b949e;
    --good: #2ea043; --fair: #d29922; --poor: #f85149; --accent: #58a6ff;
  }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Inter', sans-serif; padding: 28px 24px; }}
  .header {{ text-align: center; margin-bottom: 24px; }}
  .header h1 {{ font-family: 'JetBrains Mono', monospace; font-size: clamp(1.3rem, 2.5vw, 2rem); font-weight: 700; letter-spacing: 0.05em; margin-bottom: 6px; }}
  .header h1 span {{ color: var(--accent); }}
  .header p {{ font-size: 0.82rem; color: var(--muted); }}
  .stats {{ display: flex; justify-content: center; gap: 28px; margin-bottom: 20px; flex-wrap: wrap; }}
  .stat {{ text-align: center; }}
  .stat-value {{ font-family: 'JetBrains Mono', monospace; font-size: 1.4rem; font-weight: 700; color: var(--accent); }}
  .stat-label {{ font-size: 0.72rem; color: var(--muted); margin-top: 2px; text-transform: uppercase; letter-spacing: 0.04em; }}
  .legend {{ display: flex; justify-content: center; gap: 20px; margin-bottom: 14px; flex-wrap: wrap; }}
  .legend-item {{ display: flex; align-items: center; gap: 7px; font-size: 0.8rem; color: var(--muted); font-family: 'JetBrains Mono', monospace; }}
  .legend-dot {{ width: 11px; height: 11px; border-radius: 3px; }}
  .zones {{ display: flex; justify-content: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
  .zone {{ padding: 3px 12px; border-radius: 20px; font-size: 0.72rem; font-family: 'JetBrains Mono', monospace; font-weight: 600; letter-spacing: 0.04em; }}
  .zone-good {{ background: rgba(46,160,67,0.15); color: var(--good); border: 1px solid rgba(46,160,67,0.3); }}
  .zone-fair {{ background: rgba(210,153,34,0.15); color: var(--fair); border: 1px solid rgba(210,153,34,0.3); }}
  .zone-poor {{ background: rgba(248,81,73,0.15); color: var(--poor); border: 1px solid rgba(248,81,73,0.3); }}
  .chart-wrapper {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 20px; max-width: 1100px; margin: 0 auto; position: relative; }}
  .click-hint {{ text-align: center; font-size: 0.76rem; color: var(--muted); margin-bottom: 12px; }}
  .click-hint span {{ color: var(--accent); }}
  .footer {{ text-align: center; margin-top: 16px; font-size: 0.72rem; color: #484f58; font-style: italic; }}
</style>
</head>
<body>
<div class="header">
  <h1>GPU VALUE INDEX — <span>{month_label}</span></h1>
  <p>Cost per Normalized FPS · {len(df)} GPUs · 1440p Ultra · Prices via Newegg</p>
</div>
<div class="stats">
  <div class="stat"><div class="stat-value">${best:.2f}</div><div class="stat-label">Best Value ({best_gpu})</div></div>
  <div class="stat"><div class="stat-value">${worst:.2f}</div><div class="stat-label">Worst Value ({worst_gpu})</div></div>
  <div class="stat"><div class="stat-value">{len(df)}</div><div class="stat-label">GPUs Ranked</div></div>
  <div class="stat"><div class="stat-value">{spread}</div><div class="stat-label">Value Spread</div></div>
</div>
<div class="legend">
  <div class="legend-item"><div class="legend-dot" style="background:#76b900"></div>NVIDIA</div>
  <div class="legend-item"><div class="legend-dot" style="background:#ED1C24"></div>AMD</div>
  <div class="legend-item"><div class="legend-dot" style="background:#0071C5"></div>Intel</div>
</div>
<div class="zones">
  <div class="zone zone-good">● GREAT VALUE &lt;$8/FPS</div>
  <div class="zone zone-fair">● FAIR VALUE $8–$12/FPS</div>
  <div class="zone zone-poor">● POOR VALUE &gt;$12/FPS</div>
</div>
<div class="click-hint">Click a <span>GPU name</span> or bar to open its Newegg listing</div>
<div class="chart-wrapper">
  <canvas id="chart"></canvas>
</div>
<div class="footer">Benchmarks via Tom&#39;s Hardware GPU Hierarchy &middot; Normalized &amp; scored by SiliconValueIndex &middot; siliconvalueindex.com</div>

<script>
const labels  = {labels_js};
const values  = {values_js};
const vendors = {vendors_js};
const links   = {links_js};

const vendorColors = {{ NVIDIA: "#76b900", AMD: "#ED1C24", Intel: "#0071C5" }};
function barColor(cpf, vendor) {{
  const base = vendorColors[vendor] || "#888";
  if (cpf < 8)  return base;
  if (cpf < 12) return base + "cc";
  return base + "88";
}}
const colors = values.map((v, i) => barColor(v, vendors[i]));

const dpr = window.devicePixelRatio || 1;
const ROW_HEIGHT   = 22;
const CHART_HEIGHT = labels.length * ROW_HEIGHT + 60;
const canvas  = document.getElementById('chart');
const wrapper = canvas.parentElement;

canvas.style.width   = '100%';
canvas.style.height  = CHART_HEIGHT + 'px';
wrapper.style.height = (CHART_HEIGHT + 40) + 'px';

const logicalWidth = wrapper.clientWidth - 40;
canvas.width  = logicalWidth * dpr;
canvas.height = CHART_HEIGHT * dpr;
const ctx = canvas.getContext('2d');
ctx.scale(dpr, dpr);

const zonePlugin = {{
  id: 'zones',
  beforeDraw(chart) {{
    const {{ ctx, chartArea: {{ left, right, top, bottom }}, scales: {{ x }} }} = chart;
    [{{from:0,to:8,color:'rgba(46,160,67,0.07)'}},{{from:8,to:12,color:'rgba(210,153,34,0.06)'}},{{from:12,to:30,color:'rgba(248,81,73,0.06)'}}]
    .forEach(z => {{
      const x1 = Math.max(x.getPixelForValue(z.from), left);
      const x2 = Math.min(x.getPixelForValue(z.to), right);
      ctx.fillStyle = z.color;
      ctx.fillRect(x1, top, x2 - x1, bottom - top);
    }});
    [8,12].forEach(v => {{
      const px = x.getPixelForValue(v);
      ctx.strokeStyle = 'rgba(33,38,45,0.9)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([5,4]);
      ctx.beginPath(); ctx.moveTo(px, top); ctx.lineTo(px, bottom); ctx.stroke();
      ctx.setLineDash([]);
    }});
  }}
}};

const chart = new Chart(ctx, {{
  type: 'bar',
  data: {{ labels, datasets: [{{ data: values, backgroundColor: colors, borderRadius: 3, borderSkipped: false }}] }},
  options: {{
    indexAxis: 'y',
    responsive: false,
    maintainAspectRatio: false,
    devicePixelRatio: dpr,
    animation: {{ duration: 700, easing: 'easeOutQuart' }},
    layout: {{ padding: {{ left: 8, right: 36, top: 4, bottom: 4 }} }},
    plugins: {{
      legend: {{ display: false }},
      tooltip: {{
        backgroundColor: '#161b22', borderColor: '#21262d', borderWidth: 1,
        titleColor: '#e6edf3', bodyColor: '#8b949e',
        titleFont: {{ family: 'JetBrains Mono', size: 13, weight: '600' }},
        bodyFont: {{ family: 'Inter', size: 12 }},
        padding: 12,
        callbacks: {{
          title: ctx => ctx[0].label,
          label: ctx => {{
            const cpf = ctx.parsed.x;
            const zone = cpf < 8 ? '✓ GREAT VALUE' : cpf < 12 ? '~ FAIR VALUE' : '✗ POOR VALUE';
            return [`$${{cpf.toFixed(2)}} per FPS  ·  ${{zone}}`, 'Click to view on Newegg →'];
          }}
        }}
      }}
    }},
    scales: {{
      x: {{
        min: 0, max: 29,
        grid: {{ color: '#21262d', lineWidth: 0.8 }},
        ticks: {{ color: '#8b949e', font: {{ family: 'JetBrains Mono', size: 11 }}, callback: v => `$${{v}}` }},
        title: {{ display: true, text: 'Cost Per FPS ($/FPS) — Lower is Better', color: '#8b949e', font: {{ family: 'Inter', size: 12 }}, padding: {{ top: 10 }} }},
        border: {{ color: '#21262d' }}
      }},
      y: {{
        grid: {{ display: false }},
        border: {{ color: '#21262d' }},
        afterFit(scale) {{ scale.width = 155; }},
        ticks: {{ color: '#58a6ff', font: {{ family: 'Inter', size: 12 }}, autoSkip: false, maxRotation: 0, padding: 8 }}
      }}
    }},
    onClick(event, elements) {{
      if (elements.length > 0) {{
        const idx = elements[0].index;
        if (links[idx]) window.open(links[idx], '_blank');
      }}
    }},
    onHover(event, elements) {{
      event.native.target.style.cursor = elements.length > 0 ? 'pointer' : 'default';
    }}
  }},
  plugins: [zonePlugin]
}});

canvas.addEventListener('click', function(e) {{
  const rect = this.getBoundingClientRect();
  const clickX = e.clientX - rect.left;
  const yAxis = chart.scales.y;
  if (clickX < yAxis.right) {{
    const clickY = e.clientY - rect.top;
    for (let i = 0; i < labels.length; i++) {{
      const tickY = yAxis.getPixelForValue(i);
      if (Math.abs(clickY - tickY) < 11 && links[i]) {{
        window.open(links[i], '_blank');
        break;
      }}
    }}
  }}
}});
</script>
</body>
</html>"""

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML saved: {HTML_OUT}")

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    df = load_rankings()
    generate_png(df)
    generate_html(df)
    print("Done.")
