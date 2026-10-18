import {test,expect} from "@playwright/test";

test("original Drupal news detail redirects to the SAME genuine article, never a generic news list",async({page})=>{
  await page.goto("/novosty/2025-09-22/vystavka-v-serdce-azii/");
  await expect(page).toHaveURL(/\/news\/museum-news-2025-09-22-vystavka-v-serdce-azii\/$/);
  await expect(page.locator("h1")).toContainText("Выставка");
  await expect(page.locator("[data-official-original-news]")).toHaveCount(1);
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

test("original real museum exhibition article redirects to its precise new card",async({page})=>{
  await page.goto("/vistavky/2025-09-22/v-serdce-azii/");
  await expect(page).toHaveURL(/\/guide\/exhibitions-past\/#museum-exhibit-2025-09-22-v-serdce-azii$/);
  await expect(page.locator("#museum-exhibit-2025-09-22-v-serdce-azii")).toContainText("В сердце Азии");
});
