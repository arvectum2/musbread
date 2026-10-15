import { expect, test } from "@playwright/test";

test("главная и музейные разделы открываются", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("h1")).toContainText("Хлеб");
  await expect(page.getByText("Демонстрационный интерфейс")).toBeVisible();
  await page.getByRole("navigation", { name: "Основное меню" })
    .getByRole("link", { name: "Музей" }).click();
  await expect(page).toHaveURL(/\/museum\/$/);
  await expect(page.getByRole("heading", { name: "Музей", exact: true })).toBeVisible();
  await page.getByRole("link", { name: /Музей и его история/ }).click();
  await expect(page).toHaveURL(/\/museum\/museum-about\/$/);
  await expect(page.getByRole("heading", { name: "История музея (тест)" })).toBeVisible();
});

test("поиск по афише работает с клавиатуры", async ({ page }) => {
  await page.goto("/events/");
  const search = page.getByRole("combobox", { name: "Поиск по событиям" });
  await search.fill("экскурсия");
  const results = page.getByRole("listbox");
  await expect(results.getByRole("option")).toHaveCount(1);
  await expect(results).toContainText("История хлеба");
  await results.getByRole("option").first().click();
  await expect(page).toHaveURL(/\/events\/bread-history\/$/);
});

test("на мобильной ширине меню и ссылки доступны", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.locator(".mobile-nav summary").click();
  const navigation = page.getByRole("navigation", { name: "Мобильное меню" });
  await expect(navigation).toBeVisible();
  await navigation.getByRole("link", { name: "Новости" }).click();
  await expect(page).toHaveURL(/\/news\/$/);
  await expect(page.getByText("Демонстрационная новость")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});

test("skip-link получает клавиатурный фокус", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Перейти к содержимому" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});
