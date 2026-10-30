import {expect,test} from "@playwright/test";

// Each source-heavy Next page once contained hundreds of React Flight inline
// scripts. Build-time batching keeps hydration and cuts HTTP request fanout.
test("large museum source pages hydrate with at most three SRI-pinned local payloads",async({page})=>{
  for(const route of ["/","/news/","/guide/exhibitions-past/"]){
    await page.goto(route,{waitUntil:"networkidle"});
    await expect(page.locator("main")).toBeVisible();
    const scripts=await page.locator("script[src^='/_next/static/musbread-inline/']")
      .evaluateAll(nodes=>nodes.map(n=>({
        source:n.getAttribute("src"),
        integrity:n.getAttribute("integrity"),
        crossorigin:n.getAttribute("crossorigin")
      })));
    expect(scripts.length,route).toBeGreaterThanOrEqual(2);
    expect(scripts.length,route).toBeLessThanOrEqual(3);
    expect(scripts.every(x=>/^\/_next\/static\/musbread-inline\/[a-f0-9]{64}\.js$/.test(x.source||"")
      && /^sha384-[a-zA-Z0-9+/]+=*$/.test(x.integrity||"") && x.crossorigin==="anonymous")).toBe(true);
    const remaining=await page.locator("script:not([src])").evaluateAll(nodes=>
      nodes.some(n=>(n.textContent||"").includes("self.__next_f.push(")));
    expect(remaining,"Executable Next Flight script must not be inline on "+route).toBe(false);
    // Distinct immutable asset must be retrievable with valid application JS MIME.
    const response=await page.request.get(scripts[scripts.length-1].source!);
    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toMatch(/javascript/);
  }
  await page.goto("/events/",{waitUntil:"networkidle"});
  const search=page.getByRole("combobox",{name:"Поиск по событиям"});
  await expect(search).toHaveAttribute("data-ready","true");
  await search.fill("экскурсия");
  await expect(page.getByRole("listbox",{name:"Результаты поиска по событиям"})
    .getByRole("option")).toHaveCount(1);
});
