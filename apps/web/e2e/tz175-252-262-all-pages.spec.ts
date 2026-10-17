import {test, expect} from "@playwright/test";
import {readdirSync} from "node:fs";
import path from "node:path";

const root=path.resolve(__dirname,"../out");
function getPages(dir:string):string[]{
  return readdirSync(dir,{withFileTypes:true}).flatMap(item=>{
    const abs=path.join(dir,item.name);
    if(item.isDirectory()) return getPages(abs);
    if(item.name!=="index.html") return [];
    const rel=path.relative(root,abs).replaceAll(path.sep,"/");
    if(rel==="en/museum/not-translated/index.html") return []; // 404/noindex sentinel, no approved translation
    const route=rel==="index.html"?"/":"/"+rel.replace(/\/index\.html$/,"")+"/";
    return [route];
  });
}
const routes=getPages(root).sort();

test("TZ-175/252/262: all public static pages at desktop and mobile width",async ({page})=>{
  test.setTimeout(150_000);
  expect(routes.length).toBeGreaterThanOrEqual(75);
  for(const viewport of [{width:1440,height:900},{width:320,height:740}]){
    await page.setViewportSize(viewport);
    for(const route of routes){
      await page.goto(route,{waitUntil:"domcontentloaded"});
      await expect(page.locator("header.site-header"),"header "+route).toHaveCount(1);
      await expect(page.locator("main"),"main "+route).toHaveCount(1);
      await expect(page.locator("footer.site-footer"),"footer "+route).toHaveCount(1);
      if(route!=="/"){
        const crumbs=page.getByRole("navigation",{name:"Хлебные крошки"});
        await expect(crumbs,"breadcrumbs "+route).toHaveCount(1);
        await expect(crumbs.locator('[aria-current="page"]')).toHaveCount(1);
      }
      const width=await page.evaluate(()=>({scroll:document.documentElement.scrollWidth,viewport:document.documentElement.clientWidth}));
      if(width.scroll>width.viewport+2){
        const offenders=await page.evaluate(()=>[...document.querySelectorAll("body *")].filter(node=>{
          const b=node.getBoundingClientRect();
          return b.right>document.documentElement.clientWidth+2 || b.left < -2;
        }).slice(0,12).map(node=>({tag:node.tagName,css:(node as HTMLElement).className,
          text:node.textContent?.slice(0,90),rect:node.getBoundingClientRect().toJSON()})));
        const oversized=await page.evaluate(()=>[...document.querySelectorAll("body *")].filter(node=>
          node.scrollWidth>document.documentElement.clientWidth+2 || node.scrollWidth>node.clientWidth+3
        ).slice(0,24).map(node=>({tag:node.tagName,css:String((node as HTMLElement).className).slice(0,60),
          scroll:node.scrollWidth,client:node.clientWidth,offset:node.getBoundingClientRect().right})));
        throw new Error("horizontal overflow at "+route+" viewport "+viewport.width+
          " scroll="+width.scroll+" offenders="+JSON.stringify(offenders)+
          " oversized="+JSON.stringify(oversized));
      }
    }
  }
});
