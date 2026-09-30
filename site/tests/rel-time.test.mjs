import test from 'node:test';
import assert from 'node:assert/strict';
import { relTime } from '../src/lib/relTime.ts';

const NOW = Date.parse('2026-09-30T12:00:00Z');

test('relative times pick the largest whole unit', () => {
  assert.equal(relTime('2026-09-30T11:59:30Z', NOW), 'just now');
  assert.equal(relTime('2026-09-30T11:57:00Z', NOW), '3 minutes ago');
  assert.equal(relTime('2026-09-30T09:00:00Z', NOW), '3 hours ago');
  assert.equal(relTime('2026-09-29T12:00:00Z', NOW), 'yesterday');
  assert.equal(relTime('2026-03-06T00:00:00Z', NOW), '7 months ago');
});

test('invalid dates are returned unchanged', () => {
  assert.equal(relTime('', NOW), '');
  assert.equal(relTime('not a date', NOW), 'not a date');
});
