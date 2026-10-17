import { expect, test } from "@playwright/test";

test("TZ-114/TZ-123: header and footer share verified museum name, not invented logo", async ({page}) => {
  await page.goto("/", { waitUntil: "networkidle" });
  const head = page.locator(".site-header");
  const foot = page.locator(".site-footer");
  await expect(head.locator(".museum-identity-name")).toHaveText("Санкт-Петербургский музей Хлеба");
  await expect(foot.locator(".museum-identity-name")).toHaveText("Санкт-Петербургский музей Хлеба");
  await expect(head.locator("img.museum-identity-logo")).toHaveCount(0);
  await expect(foot.locator("img.museum-identity-logo")).toHaveCount(0);
  await expect(head.locator(".brand-mark")).toHaveCount(0);
  await expect(foot.locator(".brand-mark")).toHaveCount(0);
  await expect(foot).toContainText("СПб ГБУК");
  await head.getByRole("link", {name:/Санкт-Петербургский музей Хлеба — главная/}).click();
  await expect(page).toHaveURL(/\/$/);

  await page.goto("/en/museum/not-translated/", { waitUntil: "networkidle" });
  await expect(page.locator(".site-header .museum-identity-name")).toHaveText("Museum of Bread");
  await expect(page.locator(".site-footer .museum-identity-name")).toHaveText("Museum of Bread");
});

test("TZ-122: homepage upcoming demo agenda has source notice; archive is not shown as current", async ({page}) => {
  await page.clock.setFixedTime(new Date("2026-11-06T12:00:00Z"));
  await page.goto("/", { waitUntil: "networkidle" });
  const section = page.locator(".events-section");
  await expect(section.getByRole("heading", {name:"Афиша музея"})).toBeVisible();
  await expect(section).toContainText("демонстрационные события");
  await expect(section.getByRole("link",{name:/новостях действующего сайта/}))
    .toHaveAttribute("href", "https://muzei-xleb.ru/novosty");
  const upcoming = section.getByRole("region", {name:"Ближайшие мероприятия"});
  await expect(upcoming).toHaveAttribute("data-ready","true");
  await expect(upcoming.locator(".event-card")).toHaveCount(2);
  await expect(upcoming).not.toContainText("История хлеба");
  await section.getByRole("link",{name:/Вся афиша/}).click();
  await expect(page).toHaveURL(/\/events\/$/);
  const list=page.getByRole("region", {name:"Список мероприятий"});
  await list.getByRole("button",{name:/Архив/}).click();
  await expect(list).toContainText("История хлеба");
});

test("TZ-114/TZ-123: longer factual wordmark fits narrow mobile without overflow", async ({page}) => {
  await page.setViewportSize({width:320,height:700});
  await page.goto("/", {waitUntil:"networkidle"});
  const head=page.locator(".site-header");
  await expect(head.locator(".museum-identity-name")).toBeVisible();
  await expect(page.locator(".site-footer .museum-identity-name")).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(dimensions.scroll).toBeLessThanOrEqual(dimensions.viewport+2);
});
