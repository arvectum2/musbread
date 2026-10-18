import {expect,test} from "@playwright/test";

test("after museum domain cutover images load from our static site without retired Drupal",async({page})=>{
  const oldImageRequests:string[]=[];
  await page.route(/https:\/\/muzei-xleb\.ru\/sites\/default\/files\//,route=>{
    oldImageRequests.push(route.request().url());
    return route.abort();
  });
  await page.goto("/guide/museum-exposition/");
  const room=page.getByRole("region",{name:"Залы постоянной экспозиции"})
    .locator(".exposition-card").first();
  await room.getByText("Фотографии зала").click();
  const img=room.locator(".official-museum-source-photos img").first();
  const src=await img.getAttribute("src");
  expect(src).toMatch(/^\/media\/museum-source\/[a-f0-9]{64}\.webp$/);
  const localFile=await page.request.get(src!);
  expect(localFile.status()).toBe(200);
  expect(localFile.headers()["content-type"]).toContain("image/webp");
  await expect.poll(()=>img.evaluate(e=>(e as HTMLImageElement).naturalWidth),{timeout:8000})
    .toBeGreaterThan(0);
  expect(oldImageRequests).toEqual([]);
});

test("gallery documents never issue external museum image URLs on new domain",async({page})=>{
  for(const route of [
    "/guide/exhibitions-current/", "/guide/exhibitions-past/",
    "/guide/exhibitions-virtual/", "/guide/children-workshops/",
    "/guide/excursion-interactive/", "/guide/building-history/",
    "/guide/excursion-overview/", "/guide/accessible-museum/", "/news/",
  ]){
    await page.goto(route);
    const old=await page.locator('img[src^="https://muzei-xleb.ru/"]').count();
    expect(old,`Found retiring museum host image at ${route}`).toBe(0);
    const images=await page.locator(".official-museum-source-photos img").count();
    expect(images,`Missing old museum original gallery at ${route}`).toBeGreaterThan(0);
    const srcs=await page.locator(".official-museum-source-photos img").evaluateAll(
      elements=>elements.map(e=>e.getAttribute("src")));
    expect(srcs.every(s=>/^\/media\/museum-source\/[a-f0-9]{64}\.webp$/.test(s||""))).toBe(true);
  }
});


test("legacy museum JPG anchors in accessible guide and building history resolve locally",async({page})=>{
  for(const [route,count] of [
    ["/guide/accessible-museum/",7],
    ["/guide/building-history/",15],
  ] as const){
    await page.goto(route);
    const original=page.getByRole("region",{name:"Содержание действующего сайта музея"});
    await expect(original.locator(".official-museum-source-photos img")).toHaveCount(count);
    const photoAnchors=original.locator(".rich-text a[href^='/media/museum-source/']");
    await expect(photoAnchors).toHaveCount(count);
    await expect(original.locator('a[href^="http://muzei-xleb.ru/sites/default/files/"]')).toHaveCount(0);
    await expect(original.locator('a[href^="https://muzei-xleb.ru/sites/default/files/"]')).toHaveCount(0);
    const path=await photoAnchors.first().getAttribute("href");
    const response=await page.request.get(path!);
    expect(response.status()).toBe(200);
    expect(response.headers()["content-type"]).toContain("image/webp");
  }
});
