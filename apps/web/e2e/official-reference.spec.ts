import { expect, test } from "@playwright/test";

test("семь разделов нового ТЗ объединены с действующим меню музея", async ({ page }) => {
  await page.goto("/");
  const menu = page.getByRole("navigation", { name: "Основное меню" });
  await expect(menu.locator(".mega-group")).toHaveCount(7);
  for (const name of ["Музей", "Посетителям", "Афиша", "Экскурсии", "Детям", "Выставки", "Наука"]) {
    await expect(menu.locator("summary").filter({ hasText: name })).toHaveCount(1);
  }
  const science = menu.locator(".mega-group").last();
  await science.locator("summary").click();
  await science.getByRole("link", { name: "Коллекция" }).click();
  await expect(page).toHaveURL(/\/guide\/science-collection\/$/);
  await expect(page.getByRole("link", { name: /Госкаталоге/ })).toHaveAttribute("href", /goskatalog.ru/);
});

test("адрес, график, почта и билетный оператор взяты с действующего сайта", async ({ page }) => {
  await page.goto("/guide/plan-visit/");
  await expect(page.locator("main")).toContainText("195009");
  await expect(page.locator("main")).toContainText("Михайлова");
  await expect(page.locator("main")).toContainText("10:00–18:00");
  await expect(page.locator("main")).toContainText("Вторник");
  await expect(page.locator("main a[href^='mailto:']")).toHaveAttribute("href", "mailto:musbread@cult.gugov.spb.ru");
  const ticket = page.locator(".header-action");
  await expect(ticket).toHaveAttribute("href", "https://vmuzey.com/museum/sankt-peterburgskiy-muzey-hleba");
  await expect(ticket).toHaveAttribute("rel", /noopener/);
});

test("глобальный поиск содержит и старые, и новые разделы", async ({ page }) => {
  await page.goto("/search/");
  const search = page.getByRole("combobox", { name: "Поиск по сайту" });
  await search.fill("дарителей");
  const option = page.getByRole("listbox", { name: "Результаты поиска по сайту" }).getByRole("option");
  await expect(option.filter({ hasText: "Информация для дарителей" })).toHaveCount(1);
  await option.filter({ hasText: "Информация для дарителей" }).click();
  await expect(page).toHaveURL(/\/guide\/museum-donors\/$/);
  await expect(page.locator("main")).toContainText("действующем сайте");
});

test("режим для слабовидящих переключает контраст и сохраняет настройку", async ({ page }) => {
  await page.goto("/");
  const toggle = page.getByRole("button", { name: "Для слабовидящих" });
  await toggle.click();
  await expect(page.locator("html")).toHaveAttribute("data-vision-mode", "on");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-vision-mode", "on");
  await page.getByRole("button", { name: "Обычная версия" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-vision-mode", "off");
});

test("доступ к поиску с мобильного и перенос без горизонтального скролла", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.locator(".mobile-nav > summary").click();
  const nav = page.getByRole("navigation", { name: "Мобильное меню" });
  await nav.getByRole("link", { name: "Поиск по сайту" }).click();
  await expect(page).toHaveURL(/\/search\/$/);
  await expect(page.getByRole("combobox", { name: "Поиск по сайту" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
});

test("ширина основного контента на десктопе не менее 80%", async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto("/");
  const ratio = await page.locator(".hero").evaluate((element) =>
    element.getBoundingClientRect().width / window.innerWidth);
  expect(ratio).toBeGreaterThanOrEqual(0.8);
});

test("поиск с клавиатуры: стрелка вниз и Enter", async ({ page }) => {
  await page.goto("/search/");
  const search = page.getByRole("combobox", { name: "Поиск по сайту" });
  await search.fill("дарителей");
  await search.press("ArrowDown");
  await expect(search).toHaveAttribute("aria-expanded", "true");
  await search.press("Enter");
  await expect(page).toHaveURL(/\/guide\/museum-donors\/$/);
});
