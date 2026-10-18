import {test,expect} from "@playwright/test";

/** Measures responsive reflow, NOT native browser Page Zoom.
 * Chrome native zoom proof remains scripts/qa_native_chrome_zoom.mjs.
 * Runs identically in Chromium and WebKit. */
const pages=[
  "/", "/guide/museum-contacts/", "/guide/tickets-and-benefits/",
  "/guide/museum-media/", "/guide/science-conferences/",
  "/guide/museum-documents/", "/search/", "/guide/agenda/",
] as const;

// 640px, 480px, 390px and 320px effective CSS widths simulate narrow
// layouts from zoom, but are labelled accurately as responsive tests.
for(const viewport of [1280,768,640,480,390,320]){
  test("responsive reflow at "+viewport+"px across 8 source-backed sections",async({page})=>{
    await page.setViewportSize({width:viewport,height:820});
    for(const path of pages){
      await page.goto(path,{waitUntil:"domcontentloaded"});
      await expect(page.locator("main").first()).toBeVisible();
      const metrics=await page.evaluate(()=>({
        documentOverflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
        viewport:document.documentElement.clientWidth,
        body:document.body.scrollWidth,
      }));
      expect(metrics.documentOverflow,
        "horizontal overflow "+metrics.documentOverflow+"px at "+viewport+"px "+path)
        .toBeLessThanOrEqual(2);
      expect(metrics.body,"body overflow at "+viewport+"px "+path)
        .toBeLessThanOrEqual(metrics.viewport+2);
      await expect(page.locator("h1").first()).toBeVisible();
    }
  });
}

test("two real museum source video paths remain private until click",async({page})=>{
  const vkRequests:string[]=[];
  await page.route(/https:\/\/(vk\.com|vkvideo\.ru)\//,route=>{
    vkRequests.push(route.request().url());return route.abort();
  });
  await page.goto("/guide/museum-media/");
  await expect(page.getByRole("region",{name:"Официальные видео музея"})
    .getByRole("button",{name:"Посмотреть видео"}).first()).toBeVisible();
  await expect(page.locator("iframe")).toHaveCount(0);
  await page.goto("/guide/science-conferences/");
  await expect(page.getByRole("region",{name:"Реальные научные семинары музея"})
    .getByRole("button",{name:/Просмотреть запись/}).first()).toBeVisible();
  await expect(page.locator("iframe")).toHaveCount(0);
  expect(vkRequests).toEqual([]);
});

test("native WebKit/Chromium Tab reaches skip link and source-document links in normal DOM order",async({page})=>{
  await page.goto("/",{waitUntil:"domcontentloaded"});
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link",{name:"Перейти к содержимому"})).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();

  await page.goto("/guide/museum-documents/",{waitUntil:"domcontentloaded"});
  const originals=page.locator(".rich-text a[href]");
  await expect(originals.first()).toHaveAttribute("tabindex","0");
  await expect(originals.nth(1)).toHaveAttribute("tabindex","0");
  await originals.first().focus();
  await page.keyboard.press("Tab");
  await expect(originals.nth(1)).toBeFocused();
  const outline=await originals.nth(1).evaluate(node=>getComputedStyle(node).outlineWidth);
  expect(parseFloat(outline)).toBeGreaterThanOrEqual(3);
});
