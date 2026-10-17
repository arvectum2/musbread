import {expect,test} from "@playwright/test";

test("TZ-173 sticky desktop megamenu remains available after scrolling",async({page})=>{
 test.setTimeout(60000);
 await page.setViewportSize({width:1440,height:800});
 for(const route of ["/","/news/","/events/","/guide/museum/"]){
  await page.goto(route,{waitUntil:"domcontentloaded"});
  const header=page.locator("header.site-header");
  await expect(header.getByRole("navigation",{name:"Основное меню"})).toBeVisible();
  await page.evaluate(()=>window.scrollTo(0,document.documentElement.scrollHeight));
  await page.waitForTimeout(100);
  const rect=await header.boundingBox();
  expect(rect).not.toBeNull();
  expect(Math.abs(rect!.y),"Sticky navigation on "+route).toBeLessThan(2);
  await expect(header.locator(".main-nav .mega-group").first().locator("summary")).toBeVisible();
 }
});

test("TZ-174 nested desktop and mobile menus open and work by keyboard",async({page})=>{
 await page.setViewportSize({width:1440,height:840});
 await page.goto("/");
 const first=page.locator("nav.main-nav details.mega-group").first();
 await first.locator("summary").focus();
 await page.keyboard.press("Enter");
 await expect(first).toHaveAttribute("open","");
 const target=first.locator(".mega-panel .mega-heading");
 await expect(target).toBeVisible();
 const href=await target.getAttribute("href");
 expect(href).toMatch(/^\/guide\/[a-z0-9-]+\/$/);
 await target.focus();await page.keyboard.press("Enter");
 await expect(page).toHaveURL(new RegExp(href!.replaceAll("/","\\/")+"$"));
 await page.setViewportSize({width:390,height:780});
 await page.goto("/");
 const mobile=page.locator("details.mobile-nav");
 await mobile.locator("summary").first().focus(); await page.keyboard.press("Enter");
 await expect(mobile).toHaveAttribute("open","");
 const nested=mobile.locator("details.mobile-subnav").first();
 await nested.locator("summary").focus(); await page.keyboard.press("Enter");
 await expect(nested).toHaveAttribute("open","");
 await expect(nested.getByRole("link",{name:"Все подразделы"})).toBeVisible();
});

test("TZ-177 autocomplete uses published materials and accessible keyboard selection",async({page})=>{
 await page.setViewportSize({width:1440,height:800});
 await page.goto("/");
 const search=page.locator("header.site-header .global-search");
 const input=search.getByRole("combobox",{name:"Поиск"});
 await input.fill("история");
 const results=search.getByRole("listbox",{name:"Результаты поиска по сайту"});
 await expect(results).toBeVisible();
 const first=results.getByRole("option").first();
 const href=await first.getAttribute("href");
 expect(href).toMatch(/^\/[a-z0-9]/);
 await input.press("ArrowDown");
 await expect(first).toHaveAttribute("aria-selected","true");
 await input.press("Enter");
 await expect(page).toHaveURL(new RegExp(href!.replaceAll("/","\\/")+"$"));
});

test("TZ-120 search is available directly in desktop and mobile header",async({page})=>{
 test.setTimeout(65000);
 for(const width of [1440,768,390,320]){
  await page.setViewportSize({width,height:900});
  for(const route of ["/","/news/","/events/"]){
   await page.goto(route,{waitUntil:"domcontentloaded"});
   const header=page.locator("header.site-header");
   if(width>1000){
    await expect(header.getByRole("button",{name:"Искать по всему сайту"})).toBeVisible();
    await expect(header.getByRole("combobox",{name:"Поиск"})).toBeVisible();
   }else{
    await expect(header.locator("a.mobile-search-action")).toBeVisible();
   }
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
   expect(overflow,route+" at "+width+"px").toBeLessThanOrEqual(2);
  }
 }
 await page.setViewportSize({width:320,height:900});
 await page.goto("/");
 const link=page.locator("header a.mobile-search-action");
 await link.focus(); await expect(link).toBeFocused();
 await page.keyboard.press("Enter");
 await expect(page).toHaveURL(/\/search\/$/);
 await expect(page.getByRole("combobox",{name:"Поиск по сайту"})).toBeVisible();
});
