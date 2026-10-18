import {expect,test} from "@playwright/test";

test("TZ-155 overview excursion displays full original description",async({page})=>{
  await page.goto("/guide/excursion-overview/");
  const source=page.getByRole("region",{name:"Содержание действующего сайта музея"});
  await expect(source).toContainText("происхождении зерновых культур");
  await expect(source).toContainText("хлеб для космонавтов");
  await expect(page.getByRole("link",{name:/исходную страницу/})).toHaveAttribute("href",
    "https://muzei-xleb.ru/obzornaya-ekskursiya");
  await expect(source.locator(".official-museum-source-photos img")).toHaveCount(4);
});

test("TZ-156 six genuine interactive excursion cards with their full original text",async({page})=>{
  await page.goto("/guide/excursion-interactive/");
  const catalog=page.getByRole("region",{name:"Программы по действующему каталогу музея"});
  const cards=catalog.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(6);
  await expect(cards.first()).toContainText("Лови ритм!");
  await cards.first().locator("summary").click();
  await expect(cards.first().locator(".official-museum-program-body")).toContainText("ритм");
  await expect(catalog.locator('a[href^="https://muzei-xleb.ru/ekskursii/"]')).toHaveCount(6);
  await expect(catalog.locator("img")).toHaveCount(9);
  await expect(page.getByRole("region",{name:"Содержание действующего сайта музея"})).toHaveCount(0);
});

test("TZ-157 nine thematic cards without source duplicate",async({page})=>{
  await page.goto("/guide/excursion-thematic/");
  const catalog=page.getByRole("region",{name:"Программы по действующему каталогу музея"});
  const cards=catalog.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(9);
  await expect(catalog).toContainText("Рожь vs пшеница");
  const links=await catalog.locator('a[href^="https://muzei-xleb.ru/ekskursii/"]').evaluateAll(
    els=>els.map(a=>(a as HTMLAnchorElement).href));
  expect(links).toHaveLength(9);
  expect(new Set(links).size).toBe(9);
});

test("source theatrical programs have two genuine museum photos",async({page})=>{
  await page.goto("/guide/excursion-theatrical/");
  const catalog=page.getByRole("region",{name:"Программы по действующему каталогу музея"});
  await expect(catalog.locator(".official-museum-program-card")).toHaveCount(2);
  await expect(catalog).toContainText("Колобок");
  await expect(catalog.locator("img")).toHaveCount(2);
});

test("real excursion program descriptions fit 320px viewport",async({page})=>{
  await page.setViewportSize({width:320,height:690});
  await page.goto("/guide/excursion-thematic/");
  const cards=page.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(9);
  await cards.last().locator("summary").click();
  await expect(cards.last().locator(".official-museum-program-body")).toBeVisible();
  const size=await page.evaluate(()=>({
    scroll:document.documentElement.scrollWidth,
    viewport:document.documentElement.clientWidth,
  }));
  expect(size.scroll).toBeLessThanOrEqual(size.viewport+1);
});
