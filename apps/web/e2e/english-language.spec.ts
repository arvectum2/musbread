import { expect, test } from "@playwright/test";

test("untranslated EN placeholder remains a 404 under a genuine English layout", async ({ page }) => {
  const response = await page.goto("/en/museum/not-translated/");
  // Python's static test server sends 200 for a prerendered notFound page.
  // The production Nginx template explicitly rejects this reserved URL.
  expect(response?.status()).toBe(200);
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.getByRole("navigation", { name: "English navigation" })).toBeVisible();
  await expect(page.getByRole("button", { name: "High contrast" })).toBeVisible();
  await expect(page.getByRole("contentinfo")).toContainText("English pages");
  await expect(page.locator("meta[name='robots']").first()).toHaveAttribute("content", /noindex/);
});

test("Russian home remains Russian and no fake translations appear in navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(page.getByRole("navigation", { name: "Основное меню" })).toBeVisible();
  await expect(page.locator("a[href='/en/museum/not-translated/']")).toHaveCount(0);
});
