import {expect,test} from "@playwright/test";

// TZ-250: measure the section container rather than the paragraph line length.
// A 90% page container can still constrain prose to a readable max-width.
for(const route of ["/", "/news/", "/guide/museum/"]){
 test(`TZ-250: ${route} main content uses >=80% at desktop 1100–3840px`,async({page})=>{
  await page.goto(route,{waitUntil:'networkidle'});
  for(const width of [1100,1440,1920,2560,3840]){
   await page.setViewportSize({width,height:900});
   const data=await page.locator('main > .section, main > .hero, main > article.section').first().evaluate(el=>({
      width:el.getBoundingClientRect().width, viewport:innerWidth,
      overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
   }));
   expect(data.width/data.viewport,`${route} at ${width}px`).toBeGreaterThanOrEqual(0.8);
   expect(data.overflow,`${route} at ${width}px`).toBeLessThanOrEqual(2);
  }
 });
}
