import { test, expect } from "@playwright/test";

test("TZ-075/078: «Все события» открывает существующий каталог, а не вторую пустую страницу", async ({page}) => {
  await page.goto("/");
  const top = page.getByRole("navigation", {name:"Основное меню"});
  const agenda = top.locator(".mega-group").filter({has:page.locator("summary", {hasText:"Афиша"})});
  await agenda.locator("summary").click();
  await expect(agenda.getByRole("link", {name:"Все события"})).toHaveAttribute("href", "/events/");
  await agenda.getByRole("link", {name:"Все события"}).click();
  await expect(page).toHaveURL(/\/events\/$/);
  await expect(page.getByRole("heading", {name:"Афиша", exact:true})).toBeVisible();
  const official = page.locator("main").getByRole("link", {name:/действующем сайте Музея хлеба/});
  await expect(official).toHaveAttribute("href", "https://muzei-xleb.ru/novosty");
  await expect(page.locator("main")).toContainText("Это не официальное расписание музея");
});

test("TZ-074/078: новости и контакты доступны из главного меню и имеют официальные источники", async ({page}) => {
  await page.goto("/");
  const navigation = page.getByRole("navigation", {name:"Основное меню"});
  await navigation.getByRole("link", {name:"Контакты", exact:true}).click();
  await expect(page).toHaveURL(/\/guide\/museum-contacts\/$/);
  await expect(page.locator("main")).toContainText("Михайлова");
  await expect(page.locator("main").getByRole("link", {name:/Открыть исходную страницу/}))
    .toHaveAttribute("href", "https://muzei-xleb.ru/kontakty");
  await navigation.getByRole("link", {name:"Новости", exact:true}).click();
  await expect(page).toHaveURL(/\/news\/$/);
  await expect(page.locator("main").getByRole("link", {name:/Читать новости музея/}))
    .toHaveAttribute("href", "https://muzei-xleb.ru/novosty");
  await expect(page.locator("main")).toContainText("Тестовые материалы");
});

test("TZ-073: существующие разделы и новые страницы по ТЗ не обозначаются одинаково", async ({page}) => {
  await page.goto("/guide/museum-history/");
  await expect(page.locator("main .eyebrow")).toContainText("РАЗДЕЛ НА ДЕЙСТВУЮЩЕМ САЙТЕ");
  await expect(page.locator("main").getByRole("link", {name:/Открыть исходную страницу/}))
    .toHaveAttribute("href", "https://muzei-xleb.ru/o-muzee");
  await page.goto("/guide/friends/");
  await expect(page.locator("main .eyebrow")).toContainText("НОВЫЙ РАЗДЕЛ ПО ТЗ");
  await expect(page.locator("main")).toContainText("не предоставил утверждённые сведения");
  await expect(page.locator("main").getByRole("link", {name:/Открыть исходную страницу/})).toHaveCount(0);
});

test("TZ-075/078: мобильное меню и подвал содержат работающие пути, без второго экземпляра политики", async ({page}) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto("/");
  await page.locator(".mobile-nav > summary").click();
  const menu = page.getByRole("navigation", {name:"Мобильное меню"});
  await expect(menu.getByRole("link", {name:"Контакты", exact:true})).toHaveAttribute("href","/guide/museum-contacts/");
  const agenda = menu.locator(".mobile-subnav").filter({has:page.locator("summary",{hasText:"Афиша"})});
  await agenda.locator("summary").click();
  await expect(agenda.getByRole("link", {name:"Все события"})).toHaveAttribute("href","/events/");
  await agenda.getByRole("link", {name:"Все события"}).click();
  await expect(page).toHaveURL(/\/events\/$/);
  const footer = page.locator(".site-footer");
  await expect(footer.getByRole("link", {name:"Контакты",exact:true})).toHaveAttribute("href","/guide/museum-contacts/");
  await expect(footer.getByRole("link", {name:"Спланировать визит",exact:true})).toHaveAttribute("href","/guide/plan-visit/");
  await expect(footer.locator('a[href*="politika-konfidencialnosti"]')).toHaveCount(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBeTruthy();
});
