// Exercise the actual client module and Compare script without Astro's native
// compiler. These DOM stubs are regression checks, not a browser/visual proof.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

const moduleSource = readFileSync(new URL('../src/lib/compareSelection.ts', import.meta.url), 'utf8');
const page = readFileSync(new URL('../src/pages/compare.astro', import.meta.url), 'utf8');
const pageSource = page.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const data = JSON.parse(readFileSync(new URL('../../data/site/gpus.json', import.meta.url), 'utf8'));
const payload = {
  views: [], viewLabels: {}, counts: {},
  gpus: data.map(g => ({ id: g.gpu_id, name: g.display_name, vendor: g.vendor, rankings: g.rankings })),
};
const [a, b, c, d, e] = payload.gpus.map(g => g.id);

function storage() {
  let value = null;
  return {
    getItem: () => value,
    setItem: (_key, next) => { value = next; },
    corrupt: (next) => { value = next; },
  };
}
function execute(source, context) {
  const js = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  vm.runInNewContext(js, context);
}
function selection(localStorage) {
  const exports = {};
  execute(moduleSource, { exports, localStorage });
  return exports;
}
const plain = value => JSON.parse(JSON.stringify(value));

function visit(url, localStorage) {
  const location = new URL(url, 'https://siliconvalueindex.com');
  const elements = new Map();
  for (const id of ['pick', 'chips', 'out', 'hint', 'svi-compare']) {
    elements.set(id, { value: '', innerHTML: '', hidden: false, handlers: {}, addEventListener(type, fn) { this.handlers[type] = fn; } });
  }
  elements.get('svi-compare').textContent = JSON.stringify(payload);
  execute(pageSource, {
    exports: {},
    require: name => {
      assert.equal(name, '../lib/compareSelection');
      return selection(localStorage);
    },
    URLSearchParams, location,
    history: { replaceState: (_state, _title, next) => { location.href = new URL(next, location).href; } },
    document: { getElementById: id => elements.get(id) },
  });
  return {
    get url() { return location.href; },
    get ids() { return (location.searchParams.get('ids') ?? '').split(',').filter(Boolean); },
    get empty() { return !elements.get('hint').hidden && elements.get('out').innerHTML === ''; },
    remove(id) { elements.get('chips').handlers.click({ target: { closest: () => ({ dataset: { remove: id } }) } }); },
    add(id, type = 'change') {
      elements.get('pick').value = payload.gpus.find(g => g.id === id).name;
      elements.get('pick').handlers[type]({ key: 'Enter', preventDefault() {} });
    },
  };
}

test('selection keeps insertion order, caps at four, and toggles/removes without reordering', () => {
  const saved = storage();
  const picks = selection(saved);
  for (const id of [a, b, c, d]) picks.toggle(id);
  assert.deepEqual(plain(picks.get()), [a, b, c, d]);
  picks.add(a);
  picks.add(e);
  assert.deepEqual(plain(selection(saved).get()), [b, c, d, e]);
  picks.toggle(c);
  assert.deepEqual(plain(picks.get()), [b, d, e]);
  picks.clear();
  assert.deepEqual(plain(picks.get()), []);
});

test('corrupt, unavailable, and write-blocked storage never throw', () => {
  const saved = storage();
  const picks = selection(saved);
  for (const value of ['{', '{}', 'null', '7']) {
    saved.corrupt(value);
    assert.deepEqual(plain(picks.get()), []);
  }
  saved.corrupt(JSON.stringify([a, a, null, 42, '../bad', b]));
  assert.deepEqual(plain(picks.get()), [a, b]);
  const blocked = selection({ getItem() { throw Error('blocked'); }, setItem() { throw Error('blocked'); } });
  for (const action of [() => blocked.get(), () => blocked.add(a), () => blocked.toggle(a), () => blocked.clear()]) {
    assert.deepEqual(plain(action()), []);
  }
  assert.deepEqual(plain(selection(undefined).get()), []);
});

test('only an absent ids parameter falls back to storage; explicit links survive fresh page contexts', () => {
  const saved = storage();
  selection(saved).add(a);
  selection(saved).add(b);
  assert.deepEqual(visit('/compare/', saved).ids, [a, b]);
  for (const query of ['?ids=', '?ids=doesnotexist']) {
    const first = visit(`/compare/${query}`, saved);
    assert.equal(first.empty, true);
    assert.equal(new URL(first.url).search, '?ids=');
    assert.equal(visit(first.url, saved).empty, true); // Reload: a fresh script context.
    assert.equal(visit(first.url, saved).empty, true); // Copy/paste into another context.
    assert.deepEqual(plain(selection(saved).get()), [a, b]);
  }
  assert.deepEqual(visit(`/compare/?ids=${c},${d}`, saved).ids, [c, d]);
  assert.deepEqual(visit(`/compare/?ids=unknown,${c},${c},${d},${a},${b},${e}`, saved).ids, [c, d, a, b]);
});

test('Compare edits sync to the next storage visit and an emptied URL stays explicit', () => {
  const saved = storage();
  selection(saved).add(e);
  const page = visit(`/compare/?ids=${a},${b}`, saved);
  page.remove(a);
  assert.deepEqual(plain(selection(saved).get()), [b]);
  assert.deepEqual(visit('/compare/', saved).ids, [b]);
  page.add(c, 'keydown');
  page.add(d);
  assert.deepEqual(plain(selection(saved).get()), [b, c, d]);
  for (const id of [b, c, d]) page.remove(id);
  assert.equal(new URL(page.url).search, '?ids=');
  selection(saved).add(e); // Another page changes storage before this link is reopened.
  assert.equal(visit(page.url, saved).empty, true);
  assert.deepEqual(visit('/compare/', saved).ids, [e]);
});

test('rankings reads stored picks on initial load, every render, and restored-page navigation', () => {
  const saved = storage();
  const picks = selection(saved);
  const source = readFileSync(new URL('../src/lib/board.ts', import.meta.url), 'utf8');
  const manifest = JSON.parse(readFileSync(new URL('../../data/site/manifest.json', import.meta.url), 'utf8'));
  const rankings = JSON.parse(readFileSync(new URL('../../data/site/rankings.json', import.meta.url), 'utf8'));
  const ids = rankings[manifest.primary_view].slice(0, 5).map(row => row.gpu_id);
  const elements = new Map();
  const events = {};
  function button(id) {
    return { dataset: { compare: id }, attributes: {}, icon: {}, disabled: true,
      setAttribute(key, value) { this.attributes[key] = value; },
      querySelector() { return this.icon; }, closest() { return this; } };
  }
  const rows = {
    buttons: ids.map(button),
    querySelectorAll() { return this.buttons; },
    set innerHTML(html) { this.buttons = [...html.matchAll(/data-compare="([^"]+)"/g)].map(match => button(match[1])); },
  };
  const board = {
    style: { setProperty() {} }, handlers: {}, querySelectorAll: () => [],
    addEventListener(type, fn) { this.handlers[type] = fn; },
  };
  const sort = { value: '', handlers: {}, addEventListener(type, fn) { this.handlers[type] = fn; } };
  elements.set('svi-board', { textContent: JSON.stringify({
    views: manifest.views, primary: manifest.primary_view, zones: manifest.zones, rankings,
    gpus: Object.fromEntries(data.map(g => [g.gpu_id, { name: g.display_name, vendor: g.vendor }])),
  }) });
  elements.set('board', board);
  elements.set('rows', rows);
  elements.set('sort', sort);
  elements.set('compare-selection', {});
  elements.set('compare-count', {});
  picks.add(ids[0]);
  const exports = {};
  execute(source, {
    exports, require: () => picks, URLSearchParams,
    location: { search: '', pathname: '/rankings/' }, history: { replaceState() {} },
    window: { addEventListener(type, fn) { events[type] = fn; } },
    document: { getElementById: id => elements.get(id) ?? null },
  });
  exports.renderBoard();
  const selected = () => rows.buttons.filter(b => b.attributes['aria-pressed'] === 'true').map(b => b.dataset.compare);
  assert.deepEqual(selected(), [ids[0]]);
  picks.toggle(ids[0]);
  picks.add(ids[1]);
  sort.value = 'price';
  sort.handlers.change();
  assert.deepEqual(selected(), [ids[1]]);
  for (const id of ids.slice(2)) board.handlers.click({ target: rows.buttons.find(b => b.dataset.compare === id) });
  assert.equal(elements.get('compare-count').textContent, '4 selected');
  assert.equal(elements.get('compare-selection').href, `/compare/?ids=${ids.slice(1).join(',')}`);
  picks.clear();
  events.pageshow();
  assert.deepEqual(selected(), []);
  assert.equal(elements.get('compare-selection').hidden, true);
});
