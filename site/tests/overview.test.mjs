import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { pickVerdict, topList, findMaxBudget, picksHref } from '../src/lib/overview.ts';

const read = (name) => JSON.parse(readFileSync(new URL(`../../data/site/${name}.json`, import.meta.url), 'utf8'));
const rankings = read('rankings');
const gpus = read('gpus');
const manifest = read('manifest');

for (const [view, rows] of Object.entries(rankings)) {
  const playable = rows.filter((r) => r.playable).sort((a, b) => a.rank - b.rank);
  test(`${view}: verdict follows playable rank, including runner-up`, () => {
    assert.equal(pickVerdict(rows, null)?.best ?? null, playable[0] ?? null);
    assert.equal(pickVerdict(rows, null)?.runnerUp ?? null, playable[1] ?? null);
    assert.deepEqual(pickVerdict([...rows].reverse(), null), pickVerdict(rows, null));
    assert.equal(pickVerdict(playable.slice(0, 1), null)?.runnerUp ?? null, null);
  });
  test(`${view}: budgets filter verdict and top list without changing the input`, () => {
    const original = structuredClone(rows);
    const budgets = [300, 400, 500, 700, 1000, ...playable.map((r) => r.price)];
    for (const budget of budgets) {
      const expected = playable.filter((r) => r.price <= budget);
      const verdict = pickVerdict(rows, budget);
      assert.equal(verdict?.best ?? null, expected[0] ?? null);
      assert.equal(verdict?.runnerUp ?? null, expected[1] ?? null);
      for (const n of [0, 1, 3, 5, 100]) {
        const list = topList(rows, budget, n);
        assert.ok(list.length <= n);
        assert.ok(list.every((r) => r.playable && r.price <= budget));
        assert.deepEqual(list, expected.slice(0, n));
      }
    }
    assert.equal(pickVerdict(rows, Math.min(...playable.map((r) => r.price)) - 1), null);
    assert.deepEqual(topList(rows, null), playable.slice(0, 5));
    assert.deepEqual(rows, original);
  });
  test(`${view}: Any handoff admits the same playable cards as Find`, () => {
    const budget = findMaxBudget(gpus);
    const findEligible = rows.filter((r) => r.fps >= manifest.zones[view].min_fps && r.price <= budget).sort((a, b) => a.rank - b.rank);
    assert.deepEqual(topList(rows, null, rows.length), findEligible);
    assert.deepEqual(pickVerdict(rows, null), pickVerdict(findEligible, budget));
    for (const value of [null, 300, 400, 500, 700, 1000]) {
      const url = new URL(picksHref(view, value, gpus), 'https://example.test');
      assert.equal(url.pathname, '/find/');
      assert.equal(url.searchParams.get('budget'), String(value ?? budget));
      assert.equal(url.searchParams.get('res'), view.split('_')[0]);
      assert.equal(url.searchParams.get('mode'), view.split('_')[1]);
    }
  });
}

test('maximum budget covers every current price and is a multiple of 100', () => {
  const max = findMaxBudget(gpus);
  assert.equal(max % 100, 0);
  assert.ok(gpus.every((g) => max >= (g.current_price?.price ?? 0)));
  assert.equal(max, Math.ceil(Math.max(...gpus.map((g) => g.current_price?.price ?? 0)) / 100) * 100);
});

test('empty selections and missing prices are supported', () => {
  assert.equal(pickVerdict([], null), null);
  assert.deepEqual(topList([], 300), []);
  assert.equal(findMaxBudget([{ current_price: null }]), 0);
});
