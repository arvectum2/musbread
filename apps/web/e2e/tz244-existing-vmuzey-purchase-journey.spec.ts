import {expect,test} from '@playwright/test';

/** TZ-244, ONLY the existing user journey. Real purchase/payment, fares and
 * final host are third-party and cannot be asserted here. Mock only external
 * response, never create a fake payment path on the museum's own domain. */
const V = 'https://vmuzey.com/museum/sankt-peterburgskiy-muzey-hleba';
const externalPreview='<!doctype html><html lang="ru"><head><title>QA: имитация ответа внешнего оператора, НЕ продажа</title></head><body><h1>Контроль внешней навигации</h1></body></html>';

for (const spec of [
 {label:'desktop header',width:1440,source:'/',selector:'.header-controls .header-action'},
 {label:'mobile header',width:390,source:'/',selector:'.mobile-nav a[href^="https://vmuzey.com/"]'},
 {label:'tickets and benefits page',width:768,source:'/guide/tickets-and-benefits/',selector:'main a[href^="https://vmuzey.com/"]'},
]) {
 test(`TZ-244: approved existing ticket user journey opens external Vmuzey - ${spec.label}`,async({page})=>{
  await page.setViewportSize({width:spec.width,height:840});
  // No real operator HTTP or payment is performed by this fixture.
  await page.context().route('https://vmuzey.com/**', async route=>{
   await route.fulfill({status:200,contentType:'text/html; charset=utf-8',body:externalPreview});
  });
  await page.goto(spec.source,{waitUntil:'domcontentloaded'});
  if(spec.label==='mobile header') await page.locator('.mobile-nav > summary').click();
  const link=page.locator(spec.selector).first();
  await expect(link).toHaveAttribute('href',V);
  await expect(link).toHaveAttribute('target','_blank');
  await expect(link).toHaveAttribute('rel',/noopener/);
  const [popup]=await Promise.all([page.waitForEvent('popup'),link.click()]);
  await popup.waitForLoadState('domcontentloaded');
  await expect(popup).toHaveURL(V);
  await expect(popup.getByRole('heading',{name:'Контроль внешней навигации'})).toBeVisible();
  // Visitor's original museum page stays available, never redirects into checkout.
  await expect(page).toHaveURL(new RegExp(spec.source==='/'?'/$':spec.source.replaceAll('/','\\/')+'$'));
  await popup.close();
 });
}
