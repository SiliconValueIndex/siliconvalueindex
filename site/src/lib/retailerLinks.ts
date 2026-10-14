// Launch visibility only; retailer URLs and price-source data remain intact.
// Add 'amazon' or 'bestbuy' here to restore their shopping buttons.
export const visibleRetailers = new Set(['newegg']);

// Public Rakuten tracking identifiers, supplied by the site owner.
// SID is an account identifier, not the case-sensitive affiliate ID used here.
const affiliateId = 'vnDw7makTWM';
const neweggMid = '44583';

export function retailerLink(destination: string) {
  const direct = { href: destination, rel: 'nofollow noopener', affiliate: false };
  let url: URL;
  try { url = new URL(destination); } catch { return direct; }
  // Only US Newegg destinations belong to this advertiser. Never wrap other
  // retailers, lookalike hosts, or existing affiliate links.
  if (url.protocol !== 'https:' || !['newegg.com', 'www.newegg.com'].includes(url.hostname) || url.username || url.password || url.port) return direct;
  const link = new URL('https://click.linksynergy.com/deeplink');
  link.searchParams.set('id', affiliateId);
  link.searchParams.set('mid', neweggMid);
  link.searchParams.set('murl', destination);
  return { href: link.href, rel: 'sponsored nofollow noopener', affiliate: true };
}
