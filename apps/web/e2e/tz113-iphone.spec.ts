import { devices, expect, test } from "@playwright/test";

// Realistic WebKit viewport/touch emulation; NOT a physical iOS-device test.
test.use({ ...devices["iPhone 13"] });

test("TZ-113: iPhone/WebKit — visitor paths and no horizontal overflow", async ({page}) => {
  for (const path of ["/", "/news/", "/events/", "/guide/museum-contacts/", "/guide/accessible-museum/"]) {
    await page.goto(path, {waitUntil:"networkidle"});
    await expect(page.locator("main h1").first()).toBeVisible();
    const width = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
    }));
    expect(width.scroll, "iPhone overflow at " + path).toBeLessThanOrEqual(width.viewport + 2);
  }
  await page.goto("/");
  await page.locator(".mobile-nav > summary").tap();
  const menu = page.getByRole("navigation", {name:"Мобильное меню"});
  await expect(menu).toBeVisible();
  await menu.getByRole("link", {name:"Контакты",exact:true}).tap();
  await expect(page).toHaveURL(/\/guide\/museum-contacts\/$/);
  await expect(page.locator("main")).toContainText("Михайлова");
});

test("TZ-113: iPhone/WebKit — official museum source and touch-accessible news", async ({page}) => {
  await page.goto("/");
  await page.locator(".mobile-nav > summary").tap();
  await page.getByRole("navigation",{name:"Мобильное меню"}).getByRole("link",{name:"Новости",exact:true}).tap();
  await expect(page).toHaveURL(/\/news\/$/);
  await expect(page.locator("main").getByRole("link",{name:/Читать новости музея/}))
    .toHaveAttribute("href","https://muzei-xleb.ru/novosty");
  await expect(page.locator("main")).toContainText("НОВОСТИ ИЗ ОФИЦИАЛЬНОГО МУЗЕЙНОГО ИСТОЧНИКА");
  await expect(page.getByRole("region",{name:"Последние новости действующего сайта музея"})
    .locator(".official-museum-program-card")).toHaveCount(10);
});
