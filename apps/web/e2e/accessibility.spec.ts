import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

const urls = ["/", "/events/", "/museum/", "/news/demo-news/"];

for (const url of urls) {
  test("автоматический a11y аудит " + url, async ({ page }) => {
    await page.goto(url);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"])
      .analyze();
    const serious = results.violations.filter((violation) =>
      violation.impact === "critical" || violation.impact === "serious"
    );
    expect(serious, JSON.stringify(serious, null, 2)).toEqual([]);
  });
}
