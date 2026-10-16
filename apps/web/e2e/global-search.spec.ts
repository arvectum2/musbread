import { expect, test } from "@playwright/test";

test("полнотекстовый офлайн-поиск находит опубликованное тело новости и не обращается к CMS", async ({ page }) => {
  const privateRequests: string[] = [];
  page.on("request", (request) => {
    if (/\/admin\/|\/api\/|18082|\.php(?:\?|$)/.test(request.url())) privateRequests.push(request.url());
  });
  await page.goto("/search/");
  const search = page.getByRole("combobox", { name: "Поиск по сайту" });
  await search.fill("конвейера"); // only in the demo-news body, not its title/excerpt
  const suggestion = page.getByRole("listbox", { name: "Результаты поиска по сайту" });
  await expect(suggestion.getByRole("option", { name: /Демонстрационная новость/ })).toBeVisible();
  await page.getByRole("button", { name: /Показать все результаты/ }).click();
  const full = page.getByRole("region", { name: "Все результаты поиска" });
  await expect(full.getByRole("link", { name: "Демонстрационная новость" })).toHaveAttribute("href", "/news/demo-news/");
  await expect(full).toContainText("Найдено: 1");
  await expect(suggestion).toBeHidden();
  expect(privateRequests).toEqual([]);
});

test("несколько слов из заголовка и текста, смена запроса и клавиатура", async ({ page }) => {
  await page.goto("/search/");
  const search = page.getByRole("combobox", { name: "Поиск по сайту" });
  await search.fill("новость конвейера");
  await expect(page.getByRole("listbox").getByRole("option", { name: /Демонстрационная новость/ })).toHaveCount(1);
  await search.press("ArrowDown");
  await search.press("Enter");
  await expect(page).toHaveURL(/\/news\/demo-news\/$/);
  await page.goto("/search/");
  await search.fill("фраза которой нет в публичных материалах");
  await expect(page.getByRole("status")).toHaveText("Материалы не найдены.");
});
