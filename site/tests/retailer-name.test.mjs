import test from 'node:test';
import assert from 'node:assert/strict';
import { retailerName } from '../src/lib/data.ts';

test('retailer names format known ids and preserve unknown ids', () => {
  for (const [id, name] of Object.entries({ bestbuy: 'Best Buy', newegg: 'Newegg', amazon: 'Amazon', manual: 'listed retailer' })) {
    assert.equal(retailerName(id), name);
  }
  for (const id of ['unknown-retailer', '', 'constructor', '__proto__']) {
    assert.equal(retailerName(id), id);
  }
});
