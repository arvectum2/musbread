import {expect,test} from '@playwright/test';
import {museumReference} from '../src/data/museum-reference';

/** Source-backed link only: checkout belongs to the existing external provider.
 * Never scrape user payments, introduce a fake API or replace museum tariffs.
 */
const original = 'https://vmuzey.com/museum/sankt-peterburgskiy-muzey-hleba';

test('TZ-079/198: desktop and mobile buy ticket links remain on the official Vmuzey service',async({page})=>{
  expect(museumReference.ticketUrl).toBe(original);
  await page.goto('/');
  const desktop=page.locator('.header-controls a.header-action');
  await expect(desktop).toHaveAttribute('href',original);
  await expect(desktop).toHaveAttribute('target','_blank');
  await expect(desktop).toHaveAttribute('rel',/noopener/);
  await expect(desktop).toHaveAttribute('rel',/noreferrer/);
  await expect(desktop).toContainText('Купить билет');
  await page.setViewportSize({width:390,height:844});
  await page.locator('.mobile-nav > summary').click();
  const mobile=page.locator('.mobile-nav a').filter({hasText:'Купить билет'});
  await expect(mobile).toHaveAttribute('href',original);
  await expect(mobile).toHaveAttribute('target','_blank');
  await expect(mobile).toHaveAttribute('rel',/noopener/);
});

test('TZ-205: tickets and benefits page preserves existing link, no local payment promises',async({page})=>{
  await page.goto('/guide/tickets-and-benefits/');
  const buy=page.getByRole('link',{name:/Купить билет на действующей площадке/});
  await expect(buy).toHaveAttribute('href',original);
  await expect(buy).toHaveAttribute('target','_blank');
  await expect(buy).toHaveAttribute('rel',/noopener/);
  await expect(page.locator('main')).toContainText(/билет/i);
  // A functional third-party link, not a simulated checkout built by us.
  await expect(page.locator('form[action*="pay"],iframe[src*="payment"],button[data-test="charge"]')).toHaveCount(0);
});
