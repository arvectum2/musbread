import {expect,test} from "@playwright/test";
import archive from "../src/data/official-museum-news-archive.json";

test("museum's original /novosty root links to all twenty-seven historic ?page=N sources",async({page})=>{
 const response=await page.goto("/novosty/");
 expect(response?.status()).toBe(200);
 await expect(page.locator("h1")).toHaveText("Новости");
 await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href","https://muzei-xleb.ru/novosty");
 const links=await page.locator('nav[aria-label="Страницы архива новостей музея"] a').evaluateAll(items=>items.map(x=>x.getAttribute("href")));
 expect(links).toEqual(Array.from({length:27},(_,i)=>`/novosty?page=${i+1}`));
 await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content",/noindex/);
});

test("each old paginated index is locally materialized with original articles and correct canonical",async({page})=>{
 for(const n of [1,3,13,27]){
  const response=await page.goto(`/__museum_legacy_pager/page-${n}.html`);
  expect(response?.status(),`Old page index ${n} source-backed HTML file`).toBe(200);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href","https://muzei-xleb.ru/novosty");
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content","noindex,nofollow");
  const links=await page.locator('article[data-original-museum-archive-item]').evaluateAll(items=>
    items.map(x=>x.getAttribute("data-original-museum-archive-item")));
  expect(links).toEqual(archive.indices[n-1].article_paths);
  await expect(page.locator('nav[aria-label="Страницы архива новостей"] strong[aria-current="page"]')).toHaveText(String(n+1));
  await expect(page.locator("h1")).toHaveText("Новости");
 }
});
