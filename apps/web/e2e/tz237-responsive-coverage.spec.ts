import {expect,test} from "@playwright/test";
import {readdirSync} from "node:fs";
import path from "node:path";

const root=path.resolve(__dirname,"../out");
function pages(dir:string):string[]{
  return readdirSync(dir,{withFileTypes:true}).flatMap(item=>{
    const abs=path.join(dir,item.name);
    if(item.isDirectory()) return pages(abs);
    if(item.name!=="index.html") return [];
    const rel=path.relative(root,abs).replaceAll(path.sep,"/");
    if(rel==="en/museum/not-translated/index.html") return [];
    return [rel==="index.html"?"/":"/"+rel.replace(/\/index\.html$/,"")+"/"];
  });
}
const routes=pages(root).sort();

/** TZ-237: other regression already covers 320/1440 px. This census tests
 * actual intermediate mobile, tablet and laptop CSS viewports for EVERY
 * publicly generated route, not a curated sample of a few pages. */
test("TZ-237: 390/768/1024 px full published route responsive census",async({page})=>{
  test.setTimeout(180_000);
  expect(routes.length).toBeGreaterThanOrEqual(78);
  for(const width of [390,768,1024]){
    await page.setViewportSize({width,height:850});
    for(const route of routes){
      await page.goto(route,{waitUntil:"domcontentloaded"});
      await expect(page.locator("header.site-header"),"header "+route).toHaveCount(1);
      await expect(page.locator("main"),"main "+route).toHaveCount(1);
      await expect(page.locator("footer.site-footer"),"footer "+route).toHaveCount(1);
      const over=await page.evaluate(()=>({
        scroll:document.documentElement.scrollWidth,
        viewport:document.documentElement.clientWidth,
        body:document.body.scrollWidth,
      }));
      expect(over.scroll-over.viewport,
        "horizontal overflow at "+route+" viewport "+width+" "+JSON.stringify(over))
        .toBeLessThanOrEqual(2);
      if(width<=768){
        await expect(page.locator(".mobile-nav > summary")).toBeVisible();
        await expect(page.locator(".main-nav")).toBeHidden();
      }else{
        await expect(page.locator(".main-nav")).toBeVisible();
        await expect(page.locator(".mobile-nav")).toBeHidden();
      }
    }
  }
});

test("TZ-237: responsive interactions remain operable on phone/tablet/laptop breakpoints",async({page})=>{
  for(const width of [320,390,768,1024,1440]){
    await page.setViewportSize({width,height:850});
    await page.goto("/",{waitUntil:"networkidle"});
    const mobile=width<=768;
    if(mobile){
      const nav=page.locator(".mobile-nav > summary");
      await nav.focus();
      await page.keyboard.press("Enter");
      await expect(page.locator(".mobile-nav")).toHaveAttribute("open","");
      await expect(page.locator(".mobile-nav").getByRole("link",{name:"Контакты"})).toBeVisible();
      await nav.focus();
      await page.keyboard.press("Enter");
      await expect(page.locator(".mobile-nav")).not.toHaveAttribute("open","");
    }else{
      const group=page.locator(".main-nav .mega-group > summary").first();
      await group.focus();
      await page.keyboard.press("Space");
      await expect(page.locator(".main-nav .mega-group").first()).toHaveAttribute("open","");
    }
    await page.goto("/events/",{waitUntil:"networkidle"});
    const region=page.getByRole("region",{name:"Список мероприятий"});
    const all=region.getByRole("button",{name:/^Все/});
    await all.click();
    await expect(all).toHaveAttribute("aria-pressed","true");
    // Event search stays available even when compact global header search
    // is intentionally hidden on a narrow mobile screen.
    const search=page.getByRole("combobox",{name:"Поиск по событиям"});
    await expect(search).toBeVisible();
    await expect(page.getByRole("link",{name:/Перейти к содержимому/})).toHaveCount(1);
  }
});
