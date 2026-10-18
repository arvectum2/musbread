import {expect,test} from "@playwright/test";

test("TZ-135: news list has ten official current museum posts with original link and date",async({page})=>{
  await page.goto("/news/");
  const feed=page.getByRole("region",{name:"Последние новости действующего сайта музея"});
  const cards=feed.locator(".official-museum-program-card");
  await expect(cards).toHaveCount(10);
  await expect(cards.first()).toContainText("Ночь искусств");
  await expect(cards.first()).toContainText("16.10.2026");
  await expect(feed).toContainText("События в музее с 12 по 19 октября");
  await expect(cards.first().locator('a[href="https://muzei-xleb.ru/novosty/2026-10-16/noch-iskusstv-v-muzee-hleba"]')).toHaveCount(1);
  await cards.first().locator("summary").click();
  await expect(cards.first()).toContainText("Петербург гостеприимный");
  await expect(cards.first()).toContainText("3 ноября 2026 г.");
  await expect(feed.locator("img")).toHaveCount(0);
});

test("TZ-147: real museum night of arts appears separately from three demo CMS events",async({page})=>{
  await page.goto("/events/");
  const area=page.getByRole("region",{name:"Официальный анонс Ночи искусств"});
  await expect(area).toContainText("Ночь искусств в Музее Хлеба");
  await expect(area).toContainText("3 ноября 2026 г., 18:00–20:00");
  await expect(area).toContainText("16.10.2026");
  await expect(area).toContainText("Эта карточка не осуществляет продажи билетов");
  await expect(area.locator('a[href^="https://muzei-xleb.ru/novosty/"]')).toHaveCount(1);
  await expect(area.locator("img")).toHaveCount(0);
});

test("TZ-147: real night event is visible in source afisha category without pretending CMS approval",async({page})=>{
  await page.goto("/guide/agenda-events/");
  await expect(page.getByRole("region",{name:"Официальный анонс Ночи искусств"}))
    .toContainText("3 ноября 2026 г., 18:00–20:00");
  await expect(page.getByRole("link",{name:"Открыть афишу и архив мероприятий →"}))
    .toHaveAttribute("href","/events/");
});

test("original news and source-based Night Arts event work on 320px",async({page})=>{
  await page.setViewportSize({width:320,height:700});
  for(const route of ["/news/","/events/","/guide/agenda-events/"]){
    await page.goto(route);
    const x=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
    expect(x).toBeLessThanOrEqual(1);
  }
});
