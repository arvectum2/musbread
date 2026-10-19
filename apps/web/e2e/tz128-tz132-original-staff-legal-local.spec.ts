import {expect,test} from '@playwright/test';

test('TZ-132: administration page renders actual museum staff, roles and office phones without fabricated photos',async({page})=>{
 await page.goto('/guide/museum-team/',{waitUntil:'domcontentloaded'});
 const team=page.getByRole('region',{name:'Руководство и администрация музея'});
 await expect(team).toBeVisible();
 const records=team.locator('li');
 await expect(records).toHaveCount(5);
 await expect(records.first()).toContainText('Елизавета Вилорьевна Тапакова-Боярская');
 await expect(records.last()).toContainText('Оксана Владимировна Кутовая');
 await expect(team.locator('a[href^="tel:+7812"]')).toHaveCount(5);
 // Official administration page does not provide photos; never fabricate portraits.
 await expect(team.locator('img')).toHaveCount(0);
 await expect(team.locator('a[href="https://muzei-xleb.ru/administraciya"]')).toHaveCount(1);
});

test('TZ-128: footer legal policies, cookie and tariffs open copied LOCAL museum pages; no old-host dependency',async({page})=>{
 await page.goto('/',{waitUntil:'domcontentloaded'});
 const footer=page.locator('footer.site-footer');
 const privacy=footer.getByRole('link',{name:/Политика конфиденциальности и обработки ПДн/});
 const cookies=footer.getByRole('link',{name:/Информация об использовании cookie/});
 const prices=footer.getByRole('link',{name:'Цены и льготы'});
 await expect(privacy).toHaveAttribute('href','/guide/museum-privacy/');
 await expect(cookies).toHaveAttribute('href','/guide/museum-cookie/');
 await expect(prices).toHaveAttribute('href','/guide/tickets-and-benefits/');
 for(const route of ['/guide/museum-privacy/','/guide/museum-cookie/','/guide/tickets-and-benefits/']){
  await page.goto(route,{waitUntil:'domcontentloaded'});
  await expect(page.locator('main h1')).toBeVisible();
  await expect(page.locator('main')).toContainText(/музе|cookie|билет/i);
 }
});
