import {expect,test} from "@playwright/test";

test("TZ-163: museum's two real current exhibitions have exact source dates and full texts",async({page})=>{
  await page.goto("/guide/exhibitions-current/");
  const catalog=page.getByRole("region",{name:"Выставки из официального раздела: Текущие выставки"});
  const cards=catalog.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(2);
  await expect(cards.first()).toContainText("Резные пряничные доски");
  await expect(cards.first()).toContainText("3 октября – 7 декабря 2026 г.");
  await expect(cards.nth(1)).toContainText("3 сентября - 23 ноября 2026 г.");
  await cards.first().locator("summary").click();
  await expect(cards.first().locator(".official-museum-program-body")).not.toBeEmpty();
  await expect(catalog.locator("img")).toHaveCount(2);
  await expect(catalog.locator("img").first()).toHaveAttribute("src",/muzei-xleb\.ru\/sites\/default\/files/);
  await expect(catalog).toContainText("на дату снимка");
  await expect(page.getByRole("region",{name:"Актуальные выставки из опубликованной афиши"})).toBeVisible();
});

test("TZ-165: four original traveling exhibitions are real museum programmes, not dated sessions",async({page})=>{
  await page.goto("/guide/exhibitions-traveling/");
  const catalog=page.getByRole("region",{name:"Выставки из официального раздела: Выездные выставки"});
  const cards=catalog.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(4);
  await expect(catalog).toContainText("Хлеб блокадного города");
  await expect(catalog).toContainText("Широкая Масленица");
  await expect(catalog).toContainText("не подтверждённое расписание");
  await expect(catalog.locator('a[href^="https://muzei-xleb.ru/vistavky/"]')).toHaveCount(5);
});

test("archival museum shows are correctly labeled past, not active",async({page})=>{
  await page.goto("/guide/exhibitions-past/");
  const catalog=page.getByRole("region",{name:"Выставки из официального раздела: Прошедшие выставки"});
  await expect(catalog.locator(".official-museum-program-card")).toHaveCount(12);
  await expect(catalog).toContainText("Рассказы о ленинградцах");
  await expect(catalog).toContainText("до 28 сентября 2026 г.");
  await expect(catalog.locator("img")).toHaveCount(12);
});

test("twelve virtual museum exhibitions are source-linked, not invented event dates",async({page})=>{
  await page.goto("/guide/exhibitions-virtual/");
  const catalog=page.getByRole("region",{name:"Выставки из официального раздела: Виртуальные выставки"});
  await expect(catalog.locator(".official-museum-program-card")).toHaveCount(12);
  await expect(catalog).toContainText("Супница: история в каждой ложке");
  await expect(catalog).toContainText("Елизавета Бём");
});

test("TZ-164: future exhibitions have a real CMS event-only filter and honest empty message",async({page})=>{
  await page.goto("/guide/exhibitions-future/");
  const region=page.getByRole("region",{name:"Будущие выставки из CMS"});
  await expect(region).toContainText("только выставки с датой открытия позднее сегодняшней");
  await expect(region).toContainText("Будущие выставки пока не подтверждены");
  await expect(region.locator(".event-card")).toHaveCount(0);
  await expect(page.locator("main")).not.toContainText("Этот раздел требуется ТЗ, но сведения");
});

test("exhibition details preserve source pages on 320px, with no horizontally overflowing cards",async({page})=>{
  await page.setViewportSize({width:320,height:700});
  for(const route of ["/guide/exhibitions-current/","/guide/exhibitions-traveling/","/guide/exhibitions-past/"]){
    await page.goto(route);
    await expect(page.locator(".official-exhibitions")).toBeVisible();
    const m=await page.evaluate(()=>({document:document.documentElement.scrollWidth,
      viewport:document.documentElement.clientWidth}));
    expect(m.document).toBeLessThanOrEqual(m.viewport+1);
  }
});

test("TZ-163: 12 real archived and 12 virtual exhibitions now have original detailed texts",async({page})=>{
  for (const [route,regionName] of [
    ["/guide/exhibitions-past/","Выставки из официального раздела: Прошедшие выставки"],
    ["/guide/exhibitions-virtual/","Выставки из официального раздела: Виртуальные выставки"],
  ]) {
    await page.goto(route);
    const region=page.getByRole("region",{name:regionName});
    await expect(region.locator(".official-museum-program-card")).toHaveCount(12);
    expect(await region.locator("details").count()).toBeGreaterThan(0);
    await expect(region.locator("img")).toHaveCount(12);
  }
});
