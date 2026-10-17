import { devices, expect, test } from "@playwright/test";

// Chromium touch emulation with Pixel viewport; NOT Android hardware certification.
test.use({ ...devices["Pixel 7"] });

test("TZ-113: Android/Chromium — visitor paths fit viewport and navigate by touch", async ({page}) => {
  for (const path of ["/", "/news/", "/events/", "/guide/plan-visit/", "/guide/museum-contacts/"]) {
    await page.goto(path,{waitUntil:"networkidle"});
    await expect(page.locator("main h1").first()).toBeVisible();
    const width = await page.evaluate(() => ({
      scroll: document.documentElement.scrollWidth,
      viewport: document.documentElement.clientWidth,
    }));
    expect(width.scroll,"Pixel overflow at " + path).toBeLessThanOrEqual(width.viewport+2);
  }
  await page.goto("/");
  await page.locator(".mobile-nav > summary").tap();
  const menu=page.getByRole("navigation",{name:"Мобильное меню"});
  await expect(menu).toBeVisible();
  await menu.getByRole("link",{name:"Новости", exact:true}).tap();
  await expect(page).toHaveURL(/\/news\/$/);
  await expect(page.locator("main").getByRole("link",{name:/Читать новости музея/}))
    .toHaveAttribute("href","https://muzei-xleb.ru/novosty");
});

test("TZ-113: Android/Chromium — existing live agenda link is accessible on touch", async ({page}) => {
  await page.goto("/");
  await page.locator(".mobile-nav > summary").tap();
  const menu=page.getByRole("navigation",{name:"Мобильное меню"});
  const agenda=menu.locator(".mobile-subnav").filter({has:page.locator("summary",{hasText:"Афиша"})});
  await agenda.locator("summary").tap();
  await agenda.getByRole("link",{name:"Все события"}).tap();
  await expect(page).toHaveURL(/\/events\/$/);
  await expect(page.locator("main")).toContainText("Это не официальное расписание");
});
