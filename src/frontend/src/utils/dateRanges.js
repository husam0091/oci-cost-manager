// Billing ranges represent calendar dates in the user's timezone, not UTC instants.
export const toIsoDate = (value) => {
  if (typeof value === 'string') return value;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) throw new RangeError('Invalid calendar date');
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
};

export function getDateRangeForPreset(mode, now = new Date()) {
  const year = now.getFullYear();

  if (mode === 'prev_month') {
    const start = new Date(year, now.getMonth() - 1, 1);
    const end = new Date(year, now.getMonth(), 0);
    return { start: toIsoDate(start), end: toIsoDate(end) };
  }

  if (mode === 'ytd') {
    const start = new Date(year, 0, 1);
    return { start: toIsoDate(start), end: toIsoDate(now) };
  }

  if (mode === 'yearly' || mode === 'prev_year') {
    const prevYear = year - 1;
    const start = new Date(prevYear, 0, 1);
    const end = new Date(prevYear, 11, 31);
    return { start: toIsoDate(start), end: toIsoDate(end) };
  }

  return null;
}
