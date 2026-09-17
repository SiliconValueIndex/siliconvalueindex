// Each SVG link carries the same selected-view record used to plot its point.
export interface ScatterRow {
  gpu_id: string;
  name: string;
  vendor: string;
  price: number;
  fps: number;
  cost_per_fps: number;
  zone: 'great' | 'fair' | 'poor' | 'unplayable';
  playable: boolean;
  normalized: boolean;
}
export interface ScatterZones { great_max: number; fair_max: number; min_fps: number }

const money = (n: number, d = 0) => n.toLocaleString('en-US', {
  style: 'currency', currency: 'USD', maximumFractionDigits: d, minimumFractionDigits: d,
});
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
const nice = (v: number, step: number) => Math.ceil(v / step) * step;
const zoneLabel = { great: 'great value', fair: 'fair value', poor: 'poor value', unplayable: 'below the FPS minimum' };

export function renderScatter(svg: SVGSVGElement, rows: ScatterRow[], zones: ScatterZones, yLabel: string) {
  const W = Math.max(300, Math.round(svg.getBoundingClientRect().width) || 860);
  const compact = W < 600;
  const H = compact ? 360 : 440;
  const L = compact ? 44 : 58, R = 24, T = 50, B = 48;
  const xmax = Math.max(500, nice(Math.max(0, ...rows.map((r) => r.price)) * 1.06, 500));
  const ymax = Math.max(zones.min_fps + 20, nice(Math.max(0, ...rows.map((r) => r.fps)) * 1.15, 20));
  const sx = (p: number) => L + p / xmax * (W - L - R);
  const sy = (f: number) => H - B - f / ymax * (H - T - B);
  const xstep = nice(xmax / (compact ? 3 : 6), 250);
  const ystep = nice(ymax / 4, 10);
  let grid = '';
  for (let p = 0; p <= xmax; p += xstep) {
    grid += `<line class="grid" x1="${sx(p)}" y1="${T}" x2="${sx(p)}" y2="${H - B}"/>`;
    grid += `<text class="tick" x="${sx(p)}" y="${H - B + 22}" text-anchor="middle">${compact && p >= 1000 ? `$${p / 1000}k` : money(p)}</text>`;
  }
  for (let f = 0; f <= ymax; f += ystep) {
    grid += `<line class="grid" x1="${L}" y1="${sy(f)}" x2="${W - R}" y2="${sy(f)}"/>`;
    grid += `<text class="tick" x="${L - 10}" y="${sy(f) + 4}" text-anchor="end">${f}</text>`;
  }
  let iso = '';
  for (const cpf of [zones.great_max, zones.fair_max]) {
    const end = Math.min(xmax, ymax * cpf);
    iso += `<line class="iso" x1="${sx(0)}" y1="${sy(0)}" x2="${sx(end)}" y2="${sy(end / cpf)}"/>`;
  }
  const floorY = sy(zones.min_fps);
  const floor = `<rect class="floor-shade" x="${L}" y="${floorY}" width="${W - L - R}" height="${H - B - floorY}"/>` +
    `<line class="floor" x1="${L}" y1="${floorY}" x2="${W - R}" y2="${floorY}"/>` +
    `<text class="floorlab" x="${W - R - 6}" y="${floorY - 8}" text-anchor="end">${zones.min_fps} FPS minimum</text>`;
  const top = rows.filter((r) => r.playable).slice(0, compact ? 1 : 3).map((r) => r.gpu_id);
  let dots = '', labels = '';
  const labelBoxes: { x: number; y: number; w: number }[] = [];
  for (const r of rows) {
    const x = sx(r.price), y = sy(r.fps);
    const description = `${r.name}: ${money(r.price)}, ${r.fps.toFixed(1)} ${r.normalized ? 'estimated ' : ''}FPS, ${money(r.cost_per_fps, 2)} per FPS, ${zoneLabel[r.zone]}`;
    dots += `<a href="/gpu/${esc(r.gpu_id)}/" class="point-link" data-id="${esc(r.gpu_id)}" data-description="${esc(description)}" aria-label="${esc(description)}"><circle class="dot z-${r.zone}" cx="${x}" cy="${y}" r="${compact ? 5 : 6}"><title>${esc(description)}</title></circle></a>`;
    if (top.includes(r.gpu_id)) {
      const w = r.name.length * 7;
      const lx = Math.min(W - R - w, x + 10);
      let ly = y - 14;
      while (labelBoxes.some((b) => Math.abs(b.y - ly) < 18 && lx < b.x + b.w && lx + w > b.x)) ly -= 19;
      ly = Math.max(T + 14, ly);
      labelBoxes.push({ x: lx, y: ly, w });
      labels += `<line class="label-leader" x1="${x + 3}" y1="${y - 4}" x2="${lx}" y2="${ly + 3}"/><text class="dlabel" x="${lx}" y="${ly}">${esc(r.name)}</text>`;
    }
  }
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML = `<title>${esc(yLabel)} by recorded price</title>` + floor + grid + iso +
    `<text class="axis" x="${L}" y="20">${compact ? 'Average FPS' : esc(yLabel)}</text>` +
    `<text class="axis" x="${W - R}" y="${H - 3}" text-anchor="end">Recorded price (USD)</text>` + dots + labels;
}

export function attachTooltip(svg: SVGSVGElement, tip: HTMLElement) {
  function show(target: Element | null, x: number, y: number) {
    const point = target?.closest<SVGAElement>('.point-link');
    if (!point) { tip.hidden = true; return; }
    tip.textContent = point.dataset.description ?? '';
    tip.hidden = false;
    const box = tip.getBoundingClientRect();
    tip.style.left = `${Math.max(8, Math.min(x + 14, window.innerWidth - box.width - 8))}px`;
    tip.style.top = `${Math.max(8, Math.min(y + 14, window.innerHeight - box.height - 8))}px`;
  }
  svg.addEventListener('mousemove', (e) => show(e.target as Element, e.clientX, e.clientY));
  svg.addEventListener('focusin', (e) => {
    const target = e.target as Element;
    const rect = target.getBoundingClientRect();
    show(target, rect.left, rect.bottom);
  });
  for (const event of ['mouseleave', 'focusout']) svg.addEventListener(event, () => { tip.hidden = true; });
  svg.addEventListener('keydown', (e) => { if (e.key === 'Escape') tip.hidden = true; });
}
