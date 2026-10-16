import { expect, test } from "@playwright/test";

test("главная и музейные разделы открываются", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Хлеб");
  await expect(page.getByText("Демонстрационный интерфейс")).toBeVisible();
  const museumMenu = page.locator(".main-nav .mega-group").first();
  await museumMenu.locator("summary").click();
  await museumMenu.getByRole("link", { name: "Все подразделы: Музей" }).click();
  await expect(page).toHaveURL(/\/guide\/museum\/$/);
  await expect(page.getByRole("heading", { name: "Музей", exact: true })).toBeVisible();
  await page.locator("main").getByRole("link", { name: /История музея/ }).click();
  await expect(page).toHaveURL(/\/guide\/museum-history\/$/);
  await expect(page.getByRole("heading", { name: "История музея", exact: true })).toBeVisible();
  // Existing CMS-snapshot routes still work independently of the new guide.
  await page.goto("/museum/museum-about/");
  await expect(page.getByRole("heading", { name: "История музея (тест)" })).toBeVisible();
});

test("TZ-154: прошедшие события доступны в архиве и по исходным URL", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-12-02T12:00:00Z"));
  await page.goto("/events/", { waitUntil: "networkidle" });
  const list = page.getByRole("region", { name: "Список мероприятий" });
  await expect(list).toHaveAttribute("data-ready", "true");
  await expect(list).toContainText("Предстоящих мероприятий пока нет");
  await expect(list.locator(".event-card")).toHaveCount(0);
  await list.getByRole("button", { name: /Архив/ }).press("Enter");
  await expect(list.getByRole("button", { name: /Архив/ })).toHaveAttribute("aria-pressed", "true");
  await expect(list.locator(".event-card")).toHaveCount(3);
  await expect(list.locator(".event-card").first()).toContainText("Выставка о хлебопечении");
  await list.getByRole("button", { name: /Все/ }).press("Enter");
  await expect(list.locator(".event-card")).toHaveCount(3);
  await page.goto("/events/bread-history/");
  await expect(page.getByRole("heading", { name: "История хлеба" })).toBeVisible();
  await page.goto("/");
  const home = page.getByRole("region", { name: "Ближайшие мероприятия" });
  await expect(home).toHaveAttribute("data-ready", "true");
  await expect(home.locator(".event-card")).toHaveCount(0);
});

test("TZ-154: мероприятие сегодняшнего дня ещё актуально, на следующий день архивируется", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-11-05T12:00:00Z"));
  await page.goto("/events/", { waitUntil: "networkidle" });
  const list = page.getByRole("region", { name: "Список мероприятий" });
  await expect(list).toHaveAttribute("data-ready", "true");
  await expect(list.locator(".event-card")).toHaveCount(3);
  await list.getByRole("button", { name: /Архив/ }).press("Enter");
  await expect(list.locator(".event-card")).toHaveCount(0);
  await page.clock.setFixedTime(new Date("2026-11-06T12:00:00Z"));
  await page.reload({ waitUntil: "networkidle" });
  await expect(list).toHaveAttribute("data-ready", "true");
  await expect(list.locator(".event-card")).toHaveCount(2);
  await list.getByRole("button", { name: /Архив/ }).press("Enter");
  await expect(list.locator(".event-card")).toHaveCount(1);
  await expect(list).toContainText("История хлеба");
});

test("поиск по афише работает с клавиатуры", async ({ page }) => {
  // Static export loads route chunks asynchronously. Wait for scripts before
  // asserting that client-side search handlers are attached.
  await page.goto("/events/", { waitUntil: "networkidle" });
  const search = page.getByRole("combobox", { name: "Поиск по событиям" });
  await expect(search).toHaveAttribute("data-ready", "true");
  await search.fill("экскурсия");
  const results = page.getByRole("listbox");
  await expect(results.getByRole("option")).toHaveCount(1);
  await expect(results).toContainText("История хлеба");
  await results.getByRole("option").first().click();
  await expect(page).toHaveURL(/\/events\/bread-history\/$/);
});

test("поиск: стрелки, Enter и Escape доступны без мыши", async ({ page }) => {
  // Static export loads route chunks asynchronously. Wait for scripts before
  // asserting that client-side search handlers are attached.
  await page.goto("/events/", { waitUntil: "networkidle" });
  const search = page.getByRole("combobox", { name: "Поиск по событиям" });
  await expect(search).toHaveAttribute("data-ready", "true");
  await search.fill("экскурсия");
  await search.press("ArrowDown");
  await expect(search).toHaveAttribute("aria-expanded", "true");
  expect(await search.getAttribute("aria-activedescendant")).toBeTruthy();
  await expect(page.locator('[role="option"][aria-selected="true"]')).toHaveCount(1);
  await search.press("Escape");
  await expect(search).toHaveAttribute("aria-expanded", "false");
  await expect(search).toBeFocused();
  await search.press("ArrowDown");
  await search.press("Enter");
  await expect(page).toHaveURL(/\/events\/bread-history\/$/);
});

test("поиск: отсутствие результатов сообщает статус, варианты скрыты", async ({ page }) => {
  // Static export loads route chunks asynchronously. Wait for scripts before
  // asserting that client-side search handlers are attached.
  await page.goto("/events/", { waitUntil: "networkidle" });
  const search = page.getByRole("combobox", { name: "Поиск по событиям" });
  await expect(search).toHaveAttribute("data-ready", "true");
  await search.fill("несуществующеесобытие");
  await expect(page.getByRole("status")).toContainText("не найдено");
  await expect(search).toHaveAttribute("aria-expanded", "false");
  await expect(page.getByRole("listbox")).toBeHidden();
});

test("Контакты из музея ведут на страницу с подтверждённым адресом", async ({ page }) => {
  await page.goto("/events/");
  const museumMenu = page.locator(".main-nav .mega-group").first();
  await museumMenu.locator("summary").click();
  await museumMenu.getByRole("link", { name: "Контакты" }).click();
  await expect(page).toHaveURL(/\/guide\/museum-contacts\/$/);
  await expect(page.getByRole("heading", { name: "Контакты" })).toBeVisible();
  await expect(page.locator("main")).toContainText("Михайлова");
  await expect(page.locator("main")).toContainText("294-50-82");
});

test("на мобильной ширине меню и ссылки доступны", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.locator(".mobile-nav > summary").click();
  const navigation = page.getByRole("navigation", { name: "Мобильное меню" });
  await expect(navigation).toBeVisible();
  await navigation.getByRole("link", { name: "Новости" }).click();
  await expect(page).toHaveURL(/\/news\/$/);
  await expect(page.getByText("Демонстрационная новость")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});

test("skip-link получает клавиатурный фокус", async ({ page, browserName }) => {
  await page.goto("/");
  // Safari/WebKit defaults to Option+Tab for focusing links unless
  // "Press Tab to highlight each item" is enabled in browser settings.
  await page.keyboard.press(browserName === "webkit" ? "Alt+Tab" : "Tab");
  await expect(page.getByRole("link", { name: "Перейти к содержимому" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});

test("снимки тестового интерфейса для протокола", async ({ page }, testInfo) => {
  await page.goto("/");
  await page.screenshot({ path: testInfo.outputPath("musbread-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await page.screenshot({ path: testInfo.outputPath("musbread-mobile.png"), fullPage: true });
});

test("адаптивность при масштабировании контента до 200%", async ({ page }) => {
  // At 200% browser zoom on a 1280px window, the effective CSS viewport is
  // 640px. Using 640 CSS pixels triggers the same responsive breakpoints.
  // This checks reflow, not OS/Safari's zoom UI or all WCAG criteria.
  await page.setViewportSize({ width: 640, height: 800 });
  for (const route of ["/", "/events/", "/museum/", "/news/demo-news/"]) {
    await page.goto(route);
    const heading = page.locator("main h1").first();
    await expect(heading).toBeVisible();
    const measures = await page.evaluate(() => ({
      content: document.documentElement.scrollWidth,
      viewport: window.innerWidth,
    }));
    expect(measures.content, `Horizontal overflow at ${route}`).toBeLessThanOrEqual(measures.viewport + 1);
  }
});
