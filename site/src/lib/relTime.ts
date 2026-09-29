// "3 hours ago" for price timestamps. The site is static, so pages render the
// absolute date and this rewrites it in the browser; without JS the date stays.

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 365 * 86400],
  ['month', 30 * 86400],
  ['day', 86400],
  ['hour', 3600],
  ['minute', 60],
];
const rtf = new Intl.RelativeTimeFormat('en-US', { numeric: 'auto' });

export function relTime(iso: string, now = Date.now()): string {
  const seconds = (new Date(iso).getTime() - now) / 1000;
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit);
  }
  return 'just now';
}

export function applyRelativeTimes(root: ParentNode = document) {
  root.querySelectorAll<HTMLTimeElement>('time[data-relative]').forEach((el) => {
    if (!el.title) el.title = el.textContent ?? '';
    el.textContent = relTime(el.dateTime);
  });
}
