import test from 'node:test';
import assert from 'node:assert/strict';
import { retailerLink } from '../src/lib/retailerLinks.ts';

test('Newegg search and product destinations retain their exact query through tracking', () => {
  for (const destination of [
    'https://www.newegg.com/p/pl?d=RTX+5070+Ti&N=100007709',
    'https://www.newegg.com/p/16J-01MS-01223?item=9SIBFM7J944394',
    'https://newegg.com/p/pl?d=Radeon%20RX%207700%20XT',
  ]) {
    const result = retailerLink(destination);
    const link = new URL(result.href);
    assert.equal(link.origin + link.pathname, 'https://click.linksynergy.com/deeplink');
    assert.equal(link.searchParams.get('id'), 'vnDw7makTWM');
    assert.equal(link.searchParams.get('mid'), '44583');
    assert.equal(link.searchParams.get('murl'), destination);
    assert.equal(link.searchParams.has('offerid'), false);
    assert.equal(result.affiliate, true);
    assert.match(result.rel, /sponsored/);
  }
});

test('other retailers, lookalikes, malformed URLs and existing trackers remain unchanged', () => {
  for (const destination of [
    'https://www.amazon.com/s?k=GPU', 'https://www.bestbuy.com/site/searchpage.jsp?st=GPU',
    'https://www.newegg.ca/p/pl?d=GPU', 'https://www.newegg.com.example.com/',
    'https://www.newegg.com@evil.example/', 'https://user@www.newegg.com/',
    'http://www.newegg.com/', 'not a URL',
    'https://click.linksynergy.com/deeplink?id=existing&mid=44583',
  ]) {
    assert.deepEqual(retailerLink(destination), { href: destination, rel: 'nofollow noopener', affiliate: false });
  }
});
