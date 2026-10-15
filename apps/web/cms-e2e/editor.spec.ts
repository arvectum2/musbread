import { test, expect } from "@playwright/test";

test("реальный вход и редактор материалов в MoonShine", async ({ page }) => {
  await page.goto("/admin/login");
  const login = page.locator('input[name="username"]');
  await expect(login).toBeVisible({ timeout: 12_000 });
  await login.fill(process.env.MUSBREAD_E2E_USERNAME!);
  await page.locator('input[type="password"]').fill(process.env.MUSBREAD_E2E_PASSWORD!);
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL(/\/admin/);

  await page.goto("/admin/resource/museum-entry-resource/museum-entry-form-page");
  await expect(page.getByText("Основной текст")).toBeVisible();
  await expect(page.locator("iframe.tox-edit-area__iframe")).toBeVisible();
  await page.locator('select[name="type"]').selectOption('news');
  await page.locator('input[name="title"]').fill('QA: публикация из настоящего браузера');
  await page.locator('input[name="slug"]').fill('qa-browser-news');
  await page.locator('textarea[name="excerpt"]').fill('Тестовый анонс');
  await page.frameLocator('iframe.tox-edit-area__iframe').locator('body')
    .fill('Демонстрационная публикация из браузерного теста');
  await page.locator('select[name="status"]').selectOption('published');
  await page.locator('button[type="submit"]').filter({ hasText: 'Save' }).click();
  await expect(page).toHaveURL(/museum-entry-form-page\/\d+/, { timeout: 10_000 });

  // CP-12 acceptance: create an actual event through the MoonShine browser UI.
  await page.goto("/admin/resource/museum-event-resource/museum-event-form-page");
  await expect(page.locator('input[name="title"]')).toBeVisible();
  await page.locator('input[name="title"]').fill('QA: музейное событие из браузера');
  await page.locator('input[name="slug"]').fill('qa-browser-event');
  await page.locator('input[name="category"]').fill('Тестовая экскурсия');
  await page.locator('input[name="starts_at"]').fill('2026-11-20');
  await page.locator('textarea[name="excerpt"]').fill('Тестовый анонс события');
  await page.locator('textarea[name="body"]').fill('Описание тестового события');
  await page.locator('select[name="status"]').selectOption('published');
  await page.locator('button[type="submit"]').filter({ hasText: 'Save' }).click();
  await expect(page).toHaveURL(/museum-event-form-page\/\d+/, { timeout: 10_000 });

  // A draft must not appear in public content.
  await page.goto("/admin/resource/museum-event-resource/museum-event-form-page");
  await page.locator('input[name="title"]').fill('QA: закрытый черновик');
  await page.locator('input[name="slug"]').fill('qa-private-draft');
  await page.locator('input[name="category"]').fill('Тест');
  await page.locator('input[name="starts_at"]').fill('2026-11-21');
  await page.locator('textarea[name="excerpt"]').fill('Тестовый черновик');
  await page.locator('textarea[name="body"]').fill('Не публиковать');
  await page.locator('select[name="status"]').selectOption('draft');
  await page.locator('button[type="submit"]').filter({ hasText: 'Save' }).click();
  await expect(page).toHaveURL(/museum-event-form-page\/\d+/, { timeout: 10_000 });
});

test("закрытая медиатека поддерживает загрузку и alt-текст", async ({ page }) => {
  await page.goto("/admin/login");
  await expect(page.locator('input[name="username"]')).toBeVisible({ timeout: 12_000 });
  await page.locator('input[name="username"]').fill(process.env.MUSBREAD_E2E_USERNAME!);
  await page.locator('input[type="password"]').fill(process.env.MUSBREAD_E2E_PASSWORD!);
  await page.locator('button[type="submit"]').click();

  await page.goto("/admin/museum-media");
  await expect(page.getByRole("heading", { name: "Изображения материалов" })).toBeVisible();
  await expect(page.getByLabel("Описание изображения (alt) *")).toBeVisible();
  await expect(page.locator('input[type="file"]')).toHaveAttribute("accept", /image\/png/);
  await expect(page.getByRole("link", { name: /Вернуться в MoonShine/ })).toBeVisible();
  const option = page.locator('select[name="museum_entry_id"] option')
    .filter({ hasText: "QA: публикация из настоящего браузера" });
  const entryId = await option.first().getAttribute("value");
  expect(entryId).not.toBeNull();
  await page.locator('select[name="museum_entry_id"]').first().selectOption(entryId!);
  await page.locator('input[name="alt"]').first().fill('QA: экспонат на тестовом изображении');
  await page.locator('input[name="caption"]').first().fill('Изолированный E2E');
  await page.locator('input[type="file"]').setInputFiles(process.env.MUSBREAD_E2E_IMAGE_PATH!);
  await page.getByRole("button", { name: "Загрузить изображение" }).click();
  await expect(page.getByText("Изображение добавлено.")).toBeVisible();
  await expect(page.getByRole("img", { name: "QA: экспонат на тестовом изображении" })).toBeVisible();

});
