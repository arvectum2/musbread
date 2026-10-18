import {test,expect} from "@playwright/test";

test("SEO: original museum news URL returns its OWN full article, not a meta-refresh",async({page})=>{
  const old="/novosty/2025-09-22/vystavka-v-serdce-azii/";
  const res=await page.goto(old);
  expect(res?.status()).toBe(200);
  await expect(page).toHaveURL(new RegExp(old.replaceAll("/","\\/")+"$"));
  await expect(page.locator("h1")).toContainText("Выставка");
  await expect(page.locator("[data-official-original-news]")).toHaveCount(1);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://muzei-xleb.ru/novosty/2025-09-22/vystavka-v-serdce-azii");
  await expect(page.locator('meta[http-equiv="refresh"]')).toHaveCount(0);
});

test("legacy building-history and accessible-museum URLs work after DNS moves to our static site",async({page})=>{
  for(const [oldPath,newPath] of [
    ["/istoriya-zdaniya/","/guide/building-history/"],
    ["/informaciya-dlya-mgn/","/guide/accessible-museum/"],
    ["/novosty/","/news/"],
  ]){
    await page.goto(oldPath);
    await expect(page).toHaveURL(new RegExp(newPath.replaceAll("/","\\/")+"$"));
    await expect(page.locator("h1").first()).toBeVisible();
  }
});

test("SEO: original museum exhibition URL is standalone 200 and has its full preserved museum text",async({page})=>{
  const original="/vistavky/2025-09-22/v-serdce-azii/";
  const response=await page.goto(original);
  expect(response?.status()).toBe(200);
  await expect(page.locator("[data-original-museum-exhibition]")).toHaveCount(1);
  await expect(page.locator("h1")).toContainText("В сердце Азии");
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://muzei-xleb.ru/vistavky/2025-09-22/v-serdce-azii");
  await expect(page.locator('meta[http-equiv="refresh"]')).toHaveCount(0);
  await expect(page.locator("main")).toContainText("В сердце Азии");
});
