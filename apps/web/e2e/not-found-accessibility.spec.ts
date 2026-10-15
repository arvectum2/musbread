import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("custom 404 is navigable, noindex and structured for keyboard users", async ({ page }) => {
  await page.goto("/404/");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(page).toHaveTitle(/Страница не найдена/);
  await expect(page.getByRole("main")).toHaveCount(1);
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Страница не найдена");
  await expect(page.locator('meta[name="robots"]').first()).toHaveAttribute("content", /noindex/);
  const result = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
  expect(result.violations.filter((x) => x.impact === "serious" || x.impact === "critical")).toEqual([]);
});
