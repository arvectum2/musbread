import { expect, test } from "@playwright/test";

test("all 11 official museum rooms have their own readable descriptions", async ({ page }) => {
  await page.goto("/guide/museum-exposition/");
  const catalog = page.getByRole("region", { name: "Залы постоянной экспозиции" });
  await expect(catalog).toBeVisible();
  const cards = catalog.locator(".exposition-card");
  await expect(cards).toHaveCount(11);
  await expect(cards.first()).toContainText("Зал «Хлеб в мировой истории»");
  await expect(cards.nth(7)).toContainText("Зал «Хлеб в блокадном Ленинграде»");
  await cards.nth(7).locator("summary").click();
  await expect(cards.nth(7).locator(".exposition-card-body")).toBeVisible();
  await expect(cards.nth(7).locator(".exposition-card-body")).not.toBeEmpty();
  await expect(catalog.locator("img")).toHaveCount(0);
  await expect(catalog).toContainText("До подтверждения прав");
});

test("exposition descriptions fit a 320px phone", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 700 });
  await page.goto("/guide/museum-exposition/");
  const cards = page.locator(".exposition-card");
  await expect(cards).toHaveCount(11);
  await cards.last().locator("summary").click();
  await expect(cards.last().locator(".exposition-card-body")).toBeVisible();
  const dimensions = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    content: document.documentElement.scrollWidth,
  }));
  expect(dimensions.content).toBeLessThanOrEqual(dimensions.viewport + 1);
});

test("each source link points to a different official room; unpublished CMS drafts stay hidden", async ({ page }) => {
  await page.goto("/guide/museum-exposition/");
  const links = await page.locator(".exposition-card a[href^='https://muzei-xleb.ru/ekspozicii/']").evaluateAll(
    (anchors) => anchors.map((anchor) => (anchor as HTMLAnchorElement).href),
  );
  expect(links).toHaveLength(11);
  expect(new Set(links).size).toBe(11);
  await expect(page.locator(".exposition-card a[href^='/museum/']")).toHaveCount(0);
});
