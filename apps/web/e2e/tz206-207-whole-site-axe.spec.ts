import {expect,test} from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import {readdirSync,readFileSync,existsSync} from "node:fs";
import {join,relative} from "node:path";

const out=join(process.cwd(),"out");
function discover(base:string):string[]{
  let paths:string[]=[];
  for(const d of readdirSync(base,{withFileTypes:true})){
    if(d.isDirectory()&&!d.name.startsWith("_"))
      paths=paths.concat(discover(join(base,d.name)));
    else if(d.isFile()&&d.name==="index.html"){
      const rel=relative(out,base).replaceAll("\\","/");
      paths.push("/"+(rel?rel+"/":""));
    }
  }
  return paths;
}
const routes=discover(out).sort();
// HTTP legacy aliases self-redirect immediately. Axe cannot inspect a stable
// DOM while the browser follows meta-refresh, so verify every alias's exact
// safety/target separately, and run full WCAG checks on ALL content documents.
const aliases=routes.filter(route=>/http-equiv=["']refresh["']/i.test(
  readFileSync(join(out,route.slice(1),"index.html"),"utf-8")));
const aliasSet=new Set(aliases);
const contentRoutes=routes.filter(route=>!aliasSet.has(route));
const batchSize=75;
const batches=Array.from({length:Math.ceil(contentRoutes.length/batchSize)},
  (_,n)=>contentRoutes.slice(n*batchSize,(n+1)*batchSize));

test("TZ-206/207: every immediate historical redirect has noindex and a valid local destination",()=>{
  expect(aliases.length).toBeGreaterThan(0);
  for(const route of aliases){
    const html=readFileSync(join(out,route.slice(1),"index.html"),"utf-8");
    expect(html,route).toMatch(/<meta name="robots" content="noindex/);
    const match=html.match(/<meta http-equiv="refresh" content="0;url=(\/[^"]+)"/);
    expect(match,route).not.toBeNull();
    const destination=decodeURIComponent(match![1].split(/[?#]/,1)[0]);
    expect(destination,route).toMatch(/^\/(?:[a-z0-9-]+\/)*$/);
    expect(existsSync(join(out,destination.slice(1),"index.html")),
      "Missing source-verified redirect target: "+route+" -> "+destination).toBe(true);
  }
});

for(const [batchIndex,batch] of batches.entries()){
test('TZ-206/207: no severe axe violations, content batch '+(batchIndex+1)+'/'+batches.length,async({page})=>{
  test.setTimeout(300_000);
  const failures:string[]=[];
  const counts:Record<string,number>={};
  const affected:Record<string,string[]>={};
  for(const route of batch){
    await page.goto(route,{waitUntil:"load"});
    const result=await new AxeBuilder({page})
      .withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa","best-practice"])
      .analyze();
    for(const v of result.violations){
      counts[v.id]=(counts[v.id]??0)+1;
      affected[v.id]??=[];
      if(affected[v.id].length<8)affected[v.id].push(route);
      if(v.impact==="serious"||v.impact==="critical"){
        failures.push(route+": "+v.id+" "+v.impact+" on "+v.nodes.length+" elements "+v.nodes[0]?.target.join(" "));
      }
    }
  }
  console.log("TOTAL AXE ROUTES",batch.length, "VIOLATION COUNTS",JSON.stringify(counts),
    "EXAMPLE AFFECTED",JSON.stringify(affected));
  expect(contentRoutes.length).toBeGreaterThanOrEqual(75);
  expect(failures,"Accessibility regressions: "+failures.slice(0,40).join("\n")).toEqual([]);
});
}

for(const [batchIndex,batch] of batches.entries()){
test('TZ-206: visitor high-contrast at 320px, content batch '+(batchIndex+1)+'/'+batches.length,async({page})=>{
  test.setTimeout(300_000);
  await page.setViewportSize({width:320,height:780});
  await page.goto("/",{waitUntil:"domcontentloaded"});
  await page.getByRole("button",{name:"Для слабовидящих"}).click();
  await expect(page.locator("html")).toHaveAttribute("data-vision-mode","on");
  const failures:string[]=[];
  const violations:Record<string,number>={};
  for(const route of batch){
    await page.goto(route,{waitUntil:"load"});
    await expect(page.locator("html")).toHaveAttribute("data-vision-mode","on");
    const result=await new AxeBuilder({page})
      .withTags(["wcag2a","wcag2aa","wcag21a","wcag21aa","best-practice"])
      .analyze();
    for(const v of result.violations){
      violations[v.id]=(violations[v.id]??0)+1;
      if(v.impact==="critical"||v.impact==="serious"){
        failures.push(route+": "+v.id+" "+v.impact+" on "+v.nodes.length+" elements "+v.nodes[0]?.target.join(" "));
      }
    }
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
    if(overflow>2)failures.push(route+": horizontal overflow "+overflow+"px");
  }
  console.log("HIGH CONTRAST MOBILE ROUTES",routes.length,
    "VIOLATIONS",JSON.stringify(violations));
  expect(contentRoutes.length).toBeGreaterThanOrEqual(75);
  expect(failures,failures.slice(0,45).join("\n")).toEqual([]);
});
}

test("TZ-206/207: real source museum ticket-price table is keyboard scrollable at 320px",async({page})=>{
  await page.setViewportSize({width:320,height:780});
  await page.goto("/guide/tickets-and-benefits/",{waitUntil:"domcontentloaded"});
  await page.getByRole("button",{name:"Для слабовидящих"}).click();
  const table=page.locator(".official-source-content .rich-text table").first();
  await expect(table).toHaveAttribute("tabindex","0");
  await table.focus();
  await expect(table).toBeFocused();
  const state=await table.evaluate(node=>{
    const s=getComputedStyle(node);
    return {width:node.clientWidth,scroll:node.scrollWidth,ring:parseFloat(s.outlineWidth)};
  });
  expect(state.scroll).toBeGreaterThan(state.width);
  expect(state.ring).toBeGreaterThanOrEqual(3);
  await page.keyboard.press("ArrowRight");
  await expect.poll(()=>table.evaluate(node=>node.scrollLeft)).toBeGreaterThan(0);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(2);
});
