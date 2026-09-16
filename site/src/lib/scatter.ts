// Price-against-FPS scatter, drawn as inline SVG so it re-renders per view without a library.
// Each dot is a card. Diagonals are equal cost per frame; the horizontal rule is the playable floor.

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
export interface ScatterZones {
  great_max: number;
  fair_max: number;
  min_fps: number;
}

const money = (n: number, d = 0) =>
  n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: d, minimumFractionDigits: d });
const esc = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
const nice = (v: number, step: number) => Math.ceil(v / step) * step;

export function renderScatter(svg: SVGSVGElement, rows: ScatterRow[], zones: ScatterZones, yLabel: string) {
  const W = 860;
  const H = 480;
  const L = 66;
  const R = 24;
  const T = 24;
  const B = 44;
  const xmax = nice(Math.max(...rows.map((r) => r.price)) * 1.04, 500);
  const ymax = nice(Math.max(...rows.map((r) => r.fps)) * 1.08, 20);
  const sx = (p: number) => L + (p / xmax) * (W - L - R);
  const sy = (f: number) => H - B - (f / ymax) * (H - T - B);

  const xstep = xmax > 2000 ? 500 : 250;
  const ystep = ymax > 120 ? 40 : 20;
  let grid = '';
  for (let p = 0; p <= xmax; p += xstep) {
    grid += `<line class="grid" x1="${sx(p).toFixed(1)}" y1="${T}" x2="${sx(p).toFixed(1)}" y2="${H - B}"/>`;
    grid += `<text class="tick" x="${sx(p).toFixed(1)}" y="${H - B + 18}" text-anchor="middle">${money(p)}</text>`;
  }
  for (let f = 0; f <= ymax; f += ystep) {
    grid += `<line class="grid" x1="${L}" y1="${sy(f).toFixed(1)}" x2="${W - R}" y2="${sy(f).toFixed(1)}"/>`;
    grid += `<text class="tick" x="${L - 8}" y="${(sy(f) + 4).toFixed(1)}" text-anchor="end">${f}</text>`;
  }

  let iso = '';
  for (const [cpf, label] of [
    [zones.great_max, `${money(zones.great_max)} per frame`],
    [zones.fair_max, `${money(zones.fair_max)} per frame`],
  ] as [number, string][]) {
    const pEnd = Math.min(xmax, ymax * cpf);
    const fEnd = pEnd / cpf;
    iso += `<line class="iso" x1="${sx(0).toFixed(1)}" y1="${sy(0).toFixed(1)}" x2="${sx(pEnd).toFixed(1)}" y2="${sy(fEnd).toFixed(1)}"/>`;
    iso += `<text class="isolab" x="${(sx(pEnd) - 4).toFixed(1)}" y="${(sy(fEnd) - 6).toFixed(1)}" text-anchor="end">${label}</text>`;
  }
  const floorY = sy(zones.min_fps);
  const floor =
    `<line class="floor" x1="${L}" y1="${floorY.toFixed(1)}" x2="${W - R}" y2="${floorY.toFixed(1)}"/>` +
    `<text class="floorlab" x="${L + 6}" y="${(floorY - 6).toFixed(1)}">Playable above ${zones.min_fps} FPS</text>`;

  const top = rows.filter((r) => r.playable).slice(0, 5).map((r) => r.gpu_id);
  let dots = '';
  let labels = '';
  for (const r of rows) {
    const x = sx(r.price).toFixed(1);
    const y = sy(r.fps).toFixed(1);
    dots += `<a href="/gpu/${r.gpu_id}/"><circle class="dot z-${r.zone}" cx="${x}" cy="${y}" r="5.5" data-id="${r.gpu_id}"><title>${esc(r.name)}: ${money(r.price)}, ${r.fps.toFixed(1)} FPS, ${money(r.cost_per_fps, 2)} per frame</title></circle></a>`;
    if (top.includes(r.gpu_id)) {
      labels += `<text class="dlabel" x="${(Number(x) + 8).toFixed(1)}" y="${(Number(y) + 4).toFixed(1)}">${esc(r.name)}</text>`;
    }
  }
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  svg.innerHTML =
    grid +
    iso +
    floor +
    `<text class="axis" x="${((L + W - R) / 2).toFixed(0)}" y="${H - 4}" text-anchor="middle">Current price</text>` +
    `<text class="axis" transform="translate(18 ${((T + H - B) / 2).toFixed(0)}) rotate(-90)" text-anchor="middle">${esc(yLabel)}</text>` +
    dots +
    labels;
}

export function attachTooltip(svg: SVGSVGElement, tip: HTMLElement, rows: ScatterRow[]) {
  const byId = new Map(rows.map((r) => [r.gpu_id, r]));
  const word = { great: 'great value', fair: 'fair value', poor: 'poor value', unplayable: 'below the playable floor' };
  svg.addEventListener('mousemove', (e) => {
    const t = (e.target as Element).closest('circle') as SVGCircleElement | null;
    const r = t && byId.get(t.dataset.id || '');
    if (!r) {
      tip.hidden = true;
      return;
    }
    tip.hidden = false;
    tip.style.left = `${e.clientX + 14}px`;
    tip.style.top = `${e.clientY + 14}px`;
    tip.innerHTML = `<b>${esc(r.name)}</b>${r.normalized ? ' <span class="badge">est.</span>' : ''}<br>${money(r.price)}, ${r.fps.toFixed(1)} FPS<br>${money(r.cost_per_fps, 2)} per frame, ${word[r.zone]}`;
  });
  svg.addEventListener('mouseleave', () => {
    tip.hidden = true;
  });
}
