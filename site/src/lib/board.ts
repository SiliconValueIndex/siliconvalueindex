// Client-side behaviour for the rankings board: switch view, filter, sort.
// The server renders the primary view; this re-renders rows from embedded JSON.

interface Row {
  gpu_id: string;
  rank: number;
  fps: number;
  price: number;
  cost_per_fps: number;
  zone: 'great' | 'fair' | 'poor' | 'unplayable';
  normalized: boolean;
  playable: boolean;
}
interface BoardData {
  views: string[];
  primary: string;
  zones: Record<string, { mode: string; great_max: number; fair_max: number; min_fps: number }>;
  rankings: Record<string, Row[]>;
  gpus: Record<string, { name: string; vendor: string; price_date: string | null }>;
}

const LABEL: Record<string, string> = { '1080p': '1080p', '1440p': '1440p', '4k': '4K', raster: 'rasterization', rt: 'ray tracing' };
const money = (n: number, d = 0) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: d, minimumFractionDigits: d });
const fmtDate = (iso: string) => new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' });

export function renderBoard() {
  const dataEl = document.getElementById('svi-board');
  const board = document.getElementById('board');
  const rowsEl = document.getElementById('rows');
  if (!dataEl || !board || !rowsEl) return;
  const data: BoardData = JSON.parse(dataEl.textContent || '{}');

  const params = new URLSearchParams(location.search);
  const state = {
    res: '1440p',
    mode: 'raster',
    vendor: params.get('vendor') ?? '',
    sort: params.get('sort') ?? 'value',
    hideNormalized: params.get('est') === 'hide',
  };
  const initial = params.get('view') ?? data.primary;
  const i = initial.lastIndexOf('_');
  state.res = initial.slice(0, i);
  state.mode = initial.slice(i + 1);
  if (!data.views.includes(`${state.res}_${state.mode}`)) {
    const j = data.primary.lastIndexOf('_');
    state.res = data.primary.slice(0, j);
    state.mode = data.primary.slice(j + 1);
  }

  const sortEl = document.getElementById('sort') as HTMLSelectElement | null;
  const hideEl = document.getElementById('hide-normalized') as HTMLInputElement | null;
  if (sortEl) sortEl.value = state.sort;
  if (hideEl) hideEl.checked = state.hideNormalized;

  function syncButtons() {
    board!.querySelectorAll<HTMLButtonElement>('button[data-res]').forEach((b) => {
      b.setAttribute('aria-pressed', String(b.dataset.res === state.res));
      b.disabled = !data.views.includes(`${b.dataset.res}_${state.mode}`) && !data.views.some((v) => v.startsWith(`${b.dataset.res}_`));
    });
    board!.querySelectorAll<HTMLButtonElement>('button[data-mode]').forEach((b) => {
      b.setAttribute('aria-pressed', String(b.dataset.mode === state.mode));
      b.disabled = !data.views.includes(`${state.res}_${b.dataset.mode}`);
    });
    board!.querySelectorAll<HTMLButtonElement>('button[data-vendor]').forEach((b) => {
      b.setAttribute('aria-pressed', String((b.dataset.vendor ?? '') === state.vendor));
    });
  }

  function render() {
    const view = `${state.res}_${state.mode}`;
    let rows = [...(data.rankings[view] ?? [])];
    const zones = data.zones[view];
    if (state.vendor) rows = rows.filter((r) => data.gpus[r.gpu_id]?.vendor === state.vendor);
    if (state.hideNormalized) rows = rows.filter((r) => !r.normalized);
    const sorters: Record<string, (a: Row, b: Row) => number> = {
      value: (a, b) => a.cost_per_fps - b.cost_per_fps,
      price: (a, b) => a.price - b.price,
      fps: (a, b) => b.fps - a.fps,
      name: (a, b) => data.gpus[a.gpu_id].name.localeCompare(data.gpus[b.gpu_id].name),
    };
    rows.sort(sorters[state.sort] ?? sorters.value);

    const all = data.rankings[view] ?? [];
    const scale = Math.ceil((all.at(-1)?.cost_per_fps ?? 30) / 5) * 5;
    board!.style.setProperty('--g', `${(zones.great_max / scale) * 100}%`);
    board!.style.setProperty('--f', `${(zones.fair_max / scale) * 100}%`);

    let dividerDone = false;
    rowsEl!.innerHTML = rows
      .map((r) => {
        const g = data.gpus[r.gpu_id];
        let divider = '';
        if (!r.playable && !dividerDone && state.sort === 'value') {
          dividerDone = true;
          divider = `<li class="divider">Below ${zones.min_fps} FPS at this setting. Cheap per frame, but not enough frames to play on.</li>`;
        }
        const est = r.normalized ? '<span class="badge" title="FPS estimated from the older benchmark suite">est.</span>' : '';
        return `${divider}<li><a class="row zone-${r.zone}" href="/gpu/${r.gpu_id}/" data-vendor="${g.vendor}" data-normalized="${r.normalized}" style="--w:${(r.cost_per_fps / scale) * 100}%">
<span class="rank num">${r.rank}</span>
<span class="name"><i class="vendor-tick" data-vendor="${g.vendor}"></i>${g.name}${est}</span>
<span class="bar"><span class="fill"></span></span>
<span class="cpf num">${money(r.cost_per_fps, 2)}</span>
<span class="price num">${money(r.price, 0)}</span>
<span class="fps num">${r.fps.toFixed(1)}</span></a></li>`;
      })
      .join('');
    const empty = document.getElementById('empty');
    if (empty) empty.hidden = rows.length > 0;

    const note = document.getElementById('view-note');
    if (note) {
      const date = data.gpus[all[0]?.gpu_id]?.price_date;
      note.textContent = `${all.length} cards at ${LABEL[state.res]}, ${LABEL[state.mode]}.${date ? ` Prices checked ${fmtDate(date)}.` : ''}`;
    }
    const legend = document.getElementById('legend');
    if (legend) {
      const spans = legend.querySelectorAll('span');
      const g0 = money(zones.great_max, 0);
      const f0 = money(zones.fair_max, 0);
      spans[0].lastChild!.textContent = ` Great value, under ${g0} per frame`;
      spans[1].lastChild!.textContent = ` Fair, ${g0} to ${f0}`;
      spans[2].lastChild!.textContent = ` Poor, over ${f0}`;
    }

    const q = new URLSearchParams();
    if (view !== data.primary) q.set('view', view);
    if (state.vendor) q.set('vendor', state.vendor);
    if (state.sort !== 'value') q.set('sort', state.sort);
    if (state.hideNormalized) q.set('est', 'hide');
    const qs = q.toString();
    history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
    syncButtons();
  }

  board.addEventListener('click', (e) => {
    const b = (e.target as HTMLElement).closest('button') as HTMLButtonElement | null;
    if (!b || b.disabled) return;
    if (b.dataset.res) state.res = b.dataset.res;
    else if (b.dataset.mode) state.mode = b.dataset.mode;
    else if (b.dataset.vendor !== undefined) state.vendor = b.dataset.vendor;
    else return;
    render();
  });
  sortEl?.addEventListener('change', () => {
    state.sort = sortEl.value;
    render();
  });
  hideEl?.addEventListener('change', () => {
    state.hideNormalized = hideEl.checked;
    render();
  });

  // Only re-render on load when the URL asked for something other than the server default.
  if (params.toString()) render();
  else syncButtons();
}
