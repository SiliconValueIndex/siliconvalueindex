import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { renderScatter, attachTooltip } from '../src/lib/scatter.ts';

const read = (name) => JSON.parse(readFileSync(new URL(`../../data/site/${name}.json`, import.meta.url), 'utf8'));
const rankings = read('rankings');
const manifest = read('manifest');
const gpus = new Map(read('gpus').map((g) => [g.gpu_id, g]));
const dollars = (value) => value.toLocaleString('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 });

test('each view embeds its own FPS and value in every plotted link', () => {
  const svg = { innerHTML: '', setAttribute() {}, getBoundingClientRect: () => ({ width: 860 }) };
  for (const [view, entries] of Object.entries(rankings)) {
    const rows = entries.map((r) => ({ ...r, name: gpus.get(r.gpu_id).display_name }));
    renderScatter(svg, rows, manifest.zones[view], view);
    assert.equal((svg.innerHTML.match(/class="point-link"/g) ?? []).length, rows.length);
    for (const r of rows) {
      const link = svg.innerHTML.match(new RegExp(`<a[^>]*data-id="${r.gpu_id}"[^>]*>`))?.[0];
      assert.ok(link?.includes(`${r.fps.toFixed(1)} ${r.normalized ? 'estimated ' : ''}FPS`), `${view}: ${r.gpu_id} FPS`);
      assert.ok(link?.includes(`${dollars(r.cost_per_fps)} per FPS`), `${view}: ${r.gpu_id} value`);
    }
  }
});

test('tooltip reads the newly rendered point, rather than a stale cross-view GPU map', () => {
  const handlers = {};
  const svg = { addEventListener: (event, callback) => { handlers[event] = callback; } };
  const tip = { hidden: true, style: {}, textContent: '', getBoundingClientRect: () => ({ width: 290, height: 90 }) };
  const previousWindow = globalThis.window;
  globalThis.window = { innerWidth: 390, innerHeight: 844 };
  try {
    attachTooltip(svg, tip);
    for (const [fps, value] of [[41.9, 8.09], [9.5, 35.68]]) {
      const point = { dataset: { description: `RTX 3060: ${fps} FPS, $${value} per FPS` } };
      handlers.mousemove({ target: { closest: () => point }, clientX: 380, clientY: 830 });
      assert.equal(tip.textContent, point.dataset.description);
      assert.equal(tip.hidden, false);
      assert.ok(parseFloat(tip.style.left) + 290 <= 382);
      assert.ok(parseFloat(tip.style.top) + 90 <= 836);
    }
    handlers.keydown({ key: 'Escape' });
    assert.equal(tip.hidden, true);
  } finally { globalThis.window = previousWindow; }
});

test('an empty or narrow plot retains finite dimensions', () => {
  const svg = { innerHTML: '', setAttribute() {}, getBoundingClientRect: () => ({ width: 320 }) };
  renderScatter(svg, [], { great_max: 8, fair_max: 12, min_fps: 45 }, 'Empty view');
  assert.doesNotMatch(svg.innerHTML, /NaN|Infinity/);
});
