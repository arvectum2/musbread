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

test("SEO: original museum section URLs serve their own canonical source HTML 200",async({page})=>{
  for(const old of ["/istoriya-zdaniya/","/informaciya-dlya-mgn/","/novosty/","/administraciya/","/kontakty/","/vistavky/proshedshie-vystavki/"]){
    const response=await page.goto(old);
    expect(response?.status(),old).toBe(200);
    await expect(page).toHaveURL(new RegExp(old.replaceAll("/","\\/")+"$"));
    await expect(page.locator("h1").first()).toBeVisible();
    await expect(page.locator("[data-original-museum-section]")).toHaveCount(1);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href","https://muzei-xleb.ru"+old.slice(0,-1));
    await expect(page.locator('meta[http-equiv="refresh"]')).toHaveCount(0);
  }
});

test("SEO: genuine excursion/workshop/exposition source URLs render full 200 article, not old anchor links",async({page})=>{
  for(const [old,selector] of [
    ["/ekskursii/cena-hleba/","[data-original-museum-program]"],
    ["/master-klassy/kukly-kuvadki/","[data-original-museum-program]"],
    ["/ekspozicii/2024-07-09/zal-hleb-v-mirovoy-istorii/","[data-original-museum-room]"],
  ] as const){
    const response=await page.goto(old);
    expect(response?.status()).toBe(200);
    await expect(page.locator(selector)).toHaveCount(1);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href","https://muzei-xleb.ru"+old.slice(0,-1));
    await expect(page.locator('meta[http-equiv="refresh"]')).toHaveCount(0);
    await expect(page.locator("h1")).toBeVisible();
  }
});

test("SEO: recovered legal, video, and donor original sections are self-contained",async({page})=>{
  for(const old of ["/informaciya-dlya-dariteley/","/svedeniya-o-sozdanii-muzeya-i-pereimenovanii-muzeya/","/video/o-muzee/"]){
    const response=await page.goto(old);
    expect(response?.status()).toBe(200);
    await expect(page.locator("[data-original-museum-section]")).toHaveCount(1);
    await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href","https://muzei-xleb.ru"+old.slice(0,-1));
    await expect(page.locator('meta[http-equiv="refresh"]')).toHaveCount(0);
  }
});

test("museum's genuine news-index JPEG hyperlinks are replaced with own local WebP bytes",async({page})=>{
  await page.goto("/novosty/");
  const own=page.locator("[data-original-museum-section] .official-museum-source-photos img");
  await expect(own).toHaveCount(10);
  const paths=await own.evaluateAll(els=>els.map(e=>(e as HTMLImageElement).getAttribute("src")));
  expect(paths.every(p=>/^\/media\/museum-source\/[a-f0-9]{64}\.webp$/.test(p||""))).toBe(true);
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
