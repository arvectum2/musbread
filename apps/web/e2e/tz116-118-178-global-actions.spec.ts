import {expect,test} from "@playwright/test";

const routes=[
 "/","/news/","/events/","/search/","/guide/museum/",
 "/guide/visitors/","/guide/plan-visit/","/guide/agenda-workshops/",
 "/guide/museum-contacts/","/guide/children/","/guide/science/",
 "/guide/accessible-museum/",
];
test("TZ-116/118/178: real global booking CTA and access route on representative public pages",async({page})=>{
 test.setTimeout(95_000);
 for(const width of [320,768,1440]){
  await page.setViewportSize({width,height:900});
  for (const route of routes){
   await page.goto(route,{waitUntil:"domcontentloaded"});
   const head=page.locator("header.site-header");
   const book=head.locator("a.header-action");
   await expect(book).toHaveAttribute("href","https://vmuzey.com/museum/sankt-peterburgskiy-muzey-hleba");
   await expect(book).toHaveAttribute("rel",/noopener/);
   await expect(book).toHaveAttribute("target","_blank");
   const access=head.getByRole("link",{name:"Доступная среда: условия посещения"});
   await expect(access).toHaveAttribute("href","/guide/accessible-museum/");
   await expect(book).toBeVisible();
   await expect(access).toBeVisible();
   expect(await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)).toBeLessThanOrEqual(2);
  }
 }
});
test("TZ-178: translated public entry still contains external Russian booking CTA",async({page})=>{
 await page.goto("/en/museum/not-translated/",{waitUntil:"domcontentloaded"});
 const link=page.locator("header.site-header a.header-action");
 await expect(link).toHaveAttribute("href","https://vmuzey.com/museum/sankt-peterburgskiy-muzey-hleba");
 await expect(link).toHaveAttribute("rel",/noopener/);
 await expect(link).toBeVisible();
});
