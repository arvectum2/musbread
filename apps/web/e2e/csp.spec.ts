import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

// Generated after each static build; never reuse this for a different release.
const nginxSnippet = readFileSync(resolve(process.cwd(), ".csp-header.txt"), "utf8");
const match = nginxSnippet.match(/add_header Content-Security-Policy "([^"]+)" always;/);
if (!match) throw new Error("Build-specific CSP must be generated before browser tests");
const policy = match[1];

test("Next.js hydration, navigation and search work under strict script-hash CSP", async ({ page }) => {
  const violations: string[] = [];
  page.on("console", msg => {
    if (/content security policy|content-security-policy|refused to execute|refused to load/i.test(msg.text())) {
      violations.push(msg.text());
    }
  });
  await page.route("**/*", async route => {
    if (route.request().resourceType() !== "document") {
      await route.continue();
      return;
    }
    const response = await route.fetch();
    const headers = { ...response.headers(), "content-security-policy": policy };
    await route.fulfill({ response, headers });
  });
  await page.goto("/events/");
  await expect(page.getByRole("heading", { name: "Афиша" })).toBeVisible();
  const search = page.getByRole("combobox", { name: "Поиск по событиям" });
  await search.fill("экскурсия");
  await expect(page.getByRole("listbox").getByRole("option")).toHaveCount(1);
  await page.getByRole("listbox").getByRole("option").click();
  await expect(page).toHaveURL(/\/events\/bread-history\/$/);
  expect(violations, "CSP violations in static Next.js").toEqual([]);
});

test("unknown inline JavaScript is actively blocked by the generated CSP", async ({ page }) => {
  await page.route("**/*", async route => {
    if (route.request().resourceType() !== "document") {
      await route.continue();
      return;
    }
    const response = await route.fetch();
    const original = await response.text();
    const altered = original.replace(
      "</head>",
      "<script>window.__MUSBREAD_INJECTED = true;</script></head>",
    );
    await route.fulfill({
      response,
      body: altered,
      headers: { ...response.headers(), "content-security-policy": policy },
    });
  });
  await page.goto("/");
  await expect(page.locator("main h1").first()).toBeVisible();
  const injected = await page.evaluate(() =>
    (window as Window & { __MUSBREAD_INJECTED?: boolean }).__MUSBREAD_INJECTED
  );
  expect(injected, "Unhashed script must never execute").toBeUndefined();
});
