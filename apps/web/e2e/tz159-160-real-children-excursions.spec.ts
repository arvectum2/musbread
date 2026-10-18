import {expect,test} from "@playwright/test";

test("TZ-159 children interactive tour section contains six real source-backed programs",async({page})=>{
  await page.goto("/guide/children-interactive/");
  const catalog=page.getByRole("region",{name:"Программы по действующему каталогу музея"});
  const cards=catalog.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(6);
  await expect(catalog).toContainText("Лови ритм!");
  await expect(catalog).toContainText("Емелина печка");
  await expect(catalog).toContainText("Возрастные ограничения");
  await expect(catalog.locator('a[href^="https://muzei-xleb.ru/ekskursii/"]')).toHaveCount(6);
  await expect(page.locator("main")).not.toContainText("сведения на действующем сайте не найдены");
});

test("TZ-160 children thematic tour section contains nine real museum programs and source age details",async({page})=>{
  await page.goto("/guide/children-thematic/");
  const cards=page.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(9);
  await expect(cards.nth(4)).toContainText("Нет ничего дороже хлеба");
  await cards.nth(4).locator("summary").click();
  await expect(cards.nth(4)).toContainText(/блокад/i);
  await expect(page.getByRole("region",{name:"Программы по действующему каталогу музея"}))
    .toContainText("часть программ рассчитана на подростков");
  await expect(page.getByRole("region",{name:"Программы по действующему каталогу музея"}).locator("img")).toHaveCount(19);
});

test("children expedition source content remains usable on narrow phones",async({page})=>{
  await page.setViewportSize({width:320,height:680});
  await page.goto("/guide/children-thematic/");
  await expect(page.locator(".official-museum-program-card")).toHaveCount(9);
  const viewport=await page.evaluate(()=>({
    document:document.documentElement.scrollWidth,
    client:document.documentElement.clientWidth,
  }));
  expect(viewport.document).toBeLessThanOrEqual(viewport.client+1);
});
