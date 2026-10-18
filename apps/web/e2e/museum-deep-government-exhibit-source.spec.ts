import {expect,test} from "@playwright/test";
import oldArticles from "../src/data/official-deep-museum-pages.json";
import photos from "../src/data/official-historical-exhibition-image-assets.json";

test("old government task years and original seminar articles stay standalone with original canonical and H1",async({page})=>{
 for(const route of ["/gosudarstvennoe-zadanie/2023/","/gosudarstvennoe-zadanie/2024/","/gosudarstvennoe-zadanie/2025/",
  "/seminar-kupcy-hlebotorgovcy-v-peterburge-6-noyabrya-2025-g/"]){
  const response=await page.goto(route);
  expect(response?.status(),route).toBe(200);
  await expect(page.locator("[data-original-museum-section]")).toHaveCount(1);
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href","https://muzei-xleb.ru"+route.slice(0,-1));
  await expect(page.locator('meta[http-equiv="refresh"]')).toHaveCount(0);
  await expect(page.locator("h1")).not.toBeEmpty();
 }
});

test("archived 2019 Petersburg tea exhibition keeps its old independent page and four real self-hosted photos",async({page})=>{
 const item=oldArticles.pages.find(i=>i.path.startsWith("/vistavky/2019-06-21/"));
 expect(item).toBeTruthy();
 const response=await page.goto(item!.path+"/");
 expect(response?.status()).toBe(200);
 await expect(page.locator("[data-original-museum-exhibition]")).toHaveCount(1);
 await expect(page.locator("h1")).toContainText("Петербургское чаепитие");
 await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href",item!.source_url);
 await expect(page.locator('meta[http-equiv="refresh"]')).toHaveCount(0);
 const imgs=page.locator(".official-museum-source-photos img");
 await expect(imgs).toHaveCount(4);
 const srcs=await imgs.evaluateAll(els=>els.map(x=>x.getAttribute("src")));
 expect(srcs.every(x=>/^\/media\/museum-source\/[a-f0-9]{64}\.webp$/.test(x||""))).toBe(true);
 expect(photos.count).toBe(4);
});

test("original museum government PDF URLs remain fetchable as genuine PDF byte streams",async({page})=>{
 for(const name of ["20240826123831-gz_2024_1.pdf","20240829122031-otchet_o_vypolnenii_gos_zadaniya_za_2023.pdf",
  "20250704154330-otchet_gos_zadanie_2_kv_2025.pdf"]){
  const result=await page.request.get(`/sites/default/files/page/${name}`);
  expect(result.status()).toBe(200);
  expect(result.headers()["content-type"]).toContain("application/pdf");
  expect((await result.body()).subarray(0,4).toString()).toBe("%PDF");
 }
});
