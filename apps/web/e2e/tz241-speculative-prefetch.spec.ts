import { expect, test } from "@playwright/test";

/** TZ-241: conserve bandwidth on the mobile museum site.
 * Manual clicks must still navigate despite no speculative Next.js fetch.
 * Not a production speed SLA.
 */
test.describe("TZ-241: no speculative historic-page prefetch", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  for (const route of ["/news/", "/guide/museum/", "/search/"]) {
    test(route + " stays idle without background RSC prefetch", async ({ page }) => {
      const resourceFetches: string[] = [];
      page.on("request", (request) => {
        if (request.resourceType() === "fetch" && new URL(request.url()).hostname === "127.0.0.1") {
          resourceFetches.push(new URL(request.url()).pathname);
        }
      });
      const response = await page.goto(route, { waitUntil: "load" });
      expect(response?.status()).toBe(200);
      await page.waitForTimeout(600);
      expect(resourceFetches, "Unexpected speculative fetches from " + route).toEqual([]);
      await expect(page.locator("h1")).toBeVisible();
    });
  }

  test("user click opens full preserved news", async ({ page }) => {
    await page.goto("/news/");
    const first = page.locator(".museum-news-source h3 a").first();
    await expect(first).toContainText("Ночь искусств");
    await first.click();
    await expect(page).toHaveURL(/\/news\/museum-news-2026-10-16-noch-iskusstv/);
    await expect(page.locator("h1")).toContainText("Ночь искусств");
  });

  test("search remains interactive", async ({ page }) => {
    await page.goto("/search/");
    const field = page.getByRole("combobox", { name: "Поиск по сайту" });
    await field.fill("хлеб");
    await expect(field).toHaveValue("хлеб");
    await expect(page.getByRole("button", { name: "Показать результаты поиска" })).toBeVisible();
  });
});
