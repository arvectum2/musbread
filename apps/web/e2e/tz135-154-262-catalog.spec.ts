import {test, expect} from "@playwright/test";

test("TZ-148/150: agenda categories are taken from published CMS data and combine with archive",async ({page})=>{
  await page.clock.setFixedTime(new Date("2026-11-06T12:00:00Z"));
  await page.goto("/events/",{waitUntil:"networkidle"});
  const list=page.getByRole("region",{name:"Список мероприятий"});
  const category=list.getByRole("combobox",{name:"Категория мероприятий"});
  await expect(category).toBeVisible();
  await expect(category.locator("option")).toHaveCount(4);
  await category.selectOption("Экскурсия");
  await expect(list.locator(".event-card")).toHaveCount(0);
  await list.getByRole("button",{name:/Архив/}).click();
  await expect(list.locator(".event-card")).toHaveCount(1);
  await expect(list).toContainText("История хлеба");
  await category.selectOption("Выставка");
  await expect(list.locator(".event-card")).toHaveCount(0);
  await list.getByRole("button",{name:/Предстоящие/}).click();
  await expect(list.locator(".event-card")).toHaveCount(1);
  await expect(list).toContainText("Выставка о хлебопечении");
  await category.selectOption("");
  await expect(list.locator(".event-card")).toHaveCount(2);
  await expect(page.getByRole("link",{name:/действующем сайте Музея хлеба/}))
    .toHaveAttribute("href","https://muzei-xleb.ru/novosty");
});

test("TZ-136: public media route never publishes private assets without approved content",async ({page})=>{
  await page.goto("/guide/museum-media/",{waitUntil:"networkidle"});
  await expect(page.getByRole("heading",{name:"Опубликованные фотоматериалы"})).toBeVisible();
  await expect(page.locator(".museum-media-hub")).toContainText("Утверждённые фотоматериалы пока не опубликованы");
  await expect(page.locator(".museum-gallery-preview")).toHaveCount(0);
  await expect(page.locator(".museum-media-hub .reference-source")).toContainText("видеохостингу");
});

test("TZ-175/252/262: representative pages preserve semantic layout, crumbs and footer",async ({page})=>{
  const paths=["/events/","/events/bread-history/","/news/","/guide/museum-media/","/guide/museum-contacts/","/search/","/404/"];
  for(const path of paths){
    await page.goto(path,{waitUntil:"domcontentloaded"});
    await expect(page.locator("header.site-header")).toHaveCount(1);
    await expect(page.locator("main")).toHaveCount(1);
    await expect(page.locator("footer.site-footer")).toHaveCount(1);
    const crumbs=page.getByRole("navigation",{name:"Хлебные крошки"});
    await expect(crumbs).toHaveCount(1);
    await expect(crumbs.locator('[aria-current="page"]')).toHaveCount(1);
    await expect(crumbs.getByRole("link",{name:"Главная"})).toHaveAttribute("href","/");
    const footer=page.locator("footer.site-footer");
    await expect(footer.locator('a[href^="tel:"]')).toHaveCount(1);
    await expect(footer.locator('a[href^="mailto:"]')).toHaveCount(1);
    await expect(footer.getByRole("link",{name:/ВКонтакте/})).toHaveAttribute("href","https://vk.com/club37126776");
    await expect(footer.getByRole("link",{name:/MAX/})).toHaveAttribute("href","https://max.ru/id7808018523_gos");
  }
});
