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


test("TZ-120: поиск в шапке сохраняет запрос и показывает все результаты на отдельной странице", async ({ page }) => {
  const privateRequests: string[] = [];
  page.on("request", (request) => {
    if (/\/admin\/|\/api\/|18082|\.php(?:\?|$)/.test(request.url())) privateRequests.push(request.url());
  });
  await page.goto("/", { waitUntil: "networkidle" });
  const header = page.locator(".site-header");
  const search = header.getByRole("combobox", { name: "Поиск", exact: true });
  await expect(search).toHaveAttribute("data-ready", "true");
  await search.fill("конвейера");
  await header.getByRole("button", { name: "Искать по всему сайту" }).click();
  await expect(page).toHaveURL(/\/search\/\?q=/);
  expect(new URL(page.url()).searchParams.get("q")).toBe("конвейера");
  const fullSearch = page.getByRole("combobox", { name: "Поиск по сайту" });
  await expect(fullSearch).toHaveValue("конвейера");
  const full = page.getByRole("region", { name: "Все результаты поиска" });
  await expect(full.getByRole("link", { name: "Демонстрационная новость" }))
    .toHaveAttribute("href", "/news/demo-news/");
  expect(privateRequests).toEqual([]);
});

test("TZ-177: автодополнение в шапке, немедленный Enter и отсутствие результата", async ({ page }) => {
  await page.goto("/", { waitUntil: "networkidle" });
  const search = page.locator(".site-header").getByRole("combobox", { name: "Поиск", exact: true });
  await expect(search).toHaveAttribute("data-ready", "true");
  await search.fill("история хлеба");
  await search.press("ArrowDown");
  await search.press("Enter");
  await expect(page).toHaveURL(/\/events\/bread-history\/$/);
  await page.goto("/", { waitUntil: "networkidle" });
  await search.fill("никаких таких документов не существует");
  await expect(page.getByRole("status")).toHaveText("Материалы не найдены.");
  await expect(search).toHaveAttribute("aria-expanded", "false");
});


test("TZ-120: справочные сведения и типовые публичные разделы доступны в поиске", async ({ page }) => {
  await page.goto("/search/", { waitUntil: "networkidle" });
  const search = page.getByRole("combobox", { name: "Поиск по сайту" });
  await search.fill("михайлова");
  const suggestions = page.getByRole("listbox", { name: "Результаты поиска по сайту" });
  await expect(suggestions.getByRole("option", { name: /Контакты/ })).toBeVisible();
  await search.fill("документы");
  await page.getByRole("button", { name: "Показать результаты поиска" }).click();
  const results = page.getByRole("region", { name: "Все результаты поиска" });
  await expect(results.getByRole("link", { name: "Документы", exact: true })).toBeVisible();
  await search.fill("ничего_подобного_не_найдётся");
  await expect(page.getByRole("status")).toHaveText("Материалы не найдены.");
});
