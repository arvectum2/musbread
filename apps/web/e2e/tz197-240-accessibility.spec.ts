import {expect,test} from "@playwright/test";

const routes=["/","/search/","/guide/museum/","/guide/accessible-museum/","/news/","/events/"];

test("TZ-207: keyboard skip link focuses main content, even from top of homepage",async({page})=>{
 await page.goto("/",{waitUntil:"networkidle"});
 await page.keyboard.press("Tab");
 const skip=page.getByRole("link",{name:"Перейти к содержимому"});
 await expect(skip).toBeFocused();
 await expect(skip).toBeVisible();
 await page.keyboard.press("Enter");
 await expect(page.locator("#main")).toBeFocused();
 await page.keyboard.press("Tab");
 const focused=await page.evaluate(()=>document.activeElement?.tagName);
 expect(focused).toMatch(/A|BUTTON|SUMMARY|INPUT/);
});

test("TZ-207: menu, search selection and large text can all be operated without a mouse",async({page})=>{
 await page.goto("/",{waitUntil:"networkidle"});
 const summary=page.locator('.main-nav .mega-group').first().locator('summary');
 await summary.focus(); await page.keyboard.press('Enter');
 await expect(page.locator('.main-nav .mega-group').first()).toHaveAttribute('open','');
 await page.keyboard.press('Tab');
 await expect(page.locator('.main-nav .mega-group').first().getByRole('link',{name:/Все подразделы/})).toBeFocused();
 await summary.focus(); await page.keyboard.press('Enter');
 await expect(page.locator('.main-nav .mega-group').first()).not.toHaveAttribute('open','');
 const input=page.getByRole('navigation',{name:'Основное меню'}).getByRole('link',{name:'Новости'});
 await input.focus();await page.keyboard.press('Enter');
 await expect(page).toHaveURL(/\/news\/$/);
 await page.goto('/');
 const vision=page.getByRole('button',{name:'Для слабовидящих'});
 await vision.focus(); await page.keyboard.press('Space');
 await expect(page.locator('html')).toHaveAttribute('data-vision-mode','on');
 const search=page.getByRole('combobox',{name:'Поиск'});
 await search.focus(); await search.fill('история');
 await expect(page.getByRole('listbox',{name:'Результаты поиска по сайту'})).toBeVisible();
 await page.keyboard.press('ArrowDown');
 await expect(search).toHaveAttribute('aria-activedescendant',/list-0$/);
 await page.keyboard.press('Escape');
 await expect(search).toHaveAttribute('aria-expanded','false');
 await search.press('Enter');
 await expect(page).toHaveURL(/\/search\/\?q=/);
});

test("TZ-207: mobile nested menu opens by Enter and focus reaches nested section",async({page})=>{
 await page.setViewportSize({width:390,height:800});
 await page.goto('/',{waitUntil:'networkidle'});
 const menu=page.locator('.mobile-nav > summary');
 await menu.focus();await page.keyboard.press('Enter');
 await expect(page.locator('.mobile-nav')).toHaveAttribute('open','');
 const group=page.locator('.mobile-subnav').first().locator('summary');
 await group.focus(); await page.keyboard.press('Enter');
 await expect(page.locator('.mobile-subnav').first()).toHaveAttribute('open','');
 const section=page.locator('.mobile-subnav').first().getByRole('link',{name:'Все подразделы'});
 await section.focus();await page.keyboard.press('Enter');
 await expect(page).toHaveURL(/\/guide\/museum\/$/);
});

// Browser's actual Page Zoom shrinks the layout viewport and reevaluates CSS
// media queries. A document.style.zoom override does NOT: do not test it.
// These tests cover equivalent CSS viewport widths, not a branded-browser
// native-zoom compatibility claim (which still requires external QA).
for (const route of routes){
 test(`TZ-238/240: ${route} responsive reflow at CSS widths equivalent to 100–200% zoom`,async({page})=>{
  await page.goto(route,{waitUntil:'networkidle'});
  for(const physicalWidth of [640,768,1280]){
   for(const factor of [1,1.25,1.5,1.75,2]){
    const width=Math.floor(physicalWidth/factor);
    await page.setViewportSize({width,height:880});
    const measurements=await page.evaluate(()=>({
      scroll:document.documentElement.scrollWidth,
      client:document.documentElement.clientWidth,
      body:document.body.scrollWidth,
    }));
    expect(measurements.scroll-measurements.client,
      `${route}, screen ${physicalWidth}, zoom-equiv ${factor}, CSS viewport ${width}, ${JSON.stringify(measurements)}`)
      .toBeLessThanOrEqual(2);
    await expect(page.getByRole('button',{name:/Для слабовидящих|Обычная версия/})).toBeVisible();
   }
  }
 });
}

test('TZ-206: stored high contrast and enlarged text survive routing and narrow 200% equivalent viewport',async({page})=>{
 await page.setViewportSize({width:320,height:900});
 await page.goto('/',{waitUntil:'networkidle'});
 await page.getByRole('button',{name:'Для слабовидящих'}).click();
 await expect(page.locator('html')).toHaveAttribute('data-vision-mode','on');
 const colors=await page.locator('body').evaluate(el=>({background:getComputedStyle(el).backgroundColor,color:getComputedStyle(el).color}));
 expect(colors).toEqual({background:'rgb(255, 255, 255)',color:'rgb(17, 17, 17)'});
 await expect(page.getByRole('link',{name:'Доступная среда: условия посещения'})).toBeVisible();
 const d=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
 expect(d,'zoom equivalent 200% on 640px base viewport with high contrast').toBeLessThanOrEqual(2);
 await page.goto('/search/');
 await expect(page.locator('html')).toHaveAttribute('data-vision-mode','on');
 await expect(page.getByRole('button',{name:'Обычная версия'})).toHaveAttribute('aria-pressed','true');
});
