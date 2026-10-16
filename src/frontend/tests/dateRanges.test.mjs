import test from 'node:test';
import assert from 'node:assert/strict';
import { getDateRangeForPreset, toIsoDate } from '../src/utils/dateRanges.js';

for (const zone of ['Asia/Riyadh', 'UTC', 'America/New_York']) {
  test(`calendar boundaries stay correct in ${zone}`, () => {
    const old = process.env.TZ; process.env.TZ = zone;
    try {
      assert.equal(toIsoDate(new Date(2026, 9, 1)), '2026-10-01');
      assert.deepEqual(getDateRangeForPreset('prev_month', new Date(2026, 0, 15)), { start: '2025-12-01', end: '2025-12-31' });
      assert.deepEqual(getDateRangeForPreset('prev_month', new Date(2024, 2, 15)), { start: '2024-02-01', end: '2024-02-29' });
      assert.deepEqual(getDateRangeForPreset('ytd', new Date(2026, 9, 16)), { start: '2026-01-01', end: '2026-10-16' });
      assert.deepEqual(getDateRangeForPreset('prev_year', new Date(2026, 9, 16)), { start: '2025-01-01', end: '2025-12-31' });
      assert.equal(toIsoDate('2026-10-01'), '2026-10-01');
      assert.throws(() => toIsoDate(new Date(NaN)), RangeError);
    } finally { if (old === undefined) delete process.env.TZ; else process.env.TZ = old; }
  });
}
