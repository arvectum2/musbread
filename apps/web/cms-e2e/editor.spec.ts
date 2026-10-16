import { test, expect } from "@playwright/test";

test("реальный вход и редактор материалов в MoonShine", async ({ page }) => {
  await page.goto("/admin/login");
  const login = page.locator('input[name="username"]');
  await expect(login).toBeVisible({ timeout: 12_000 });
  await login.fill(process.env.MUSBREAD_E2E_USERNAME!);
  await page.locator('input[type="password"]').fill(process.env.MUSBREAD_E2E_PASSWORD!);
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL(/\/admin/);

  // A real HTTP request made with the authenticated session but without
  // Laravel's CSRF token must be rejected before touching protected media.
  const csrfDenied = await page.request.post("/admin/museum-media", {
    data: { alt: "No CSRF token", museum_entry_id: "1" },
  });
  expect(csrfDenied.status(), "Private media POST requires a CSRF token").toBe(419);

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

  // Editor updates alt/caption without exposing a direct public file URL.
  const initialCard = page.locator("article.item").filter({
    has: page.getByRole("img", { name: "QA: экспонат на тестовом изображении" }),
  });
  await initialCard.locator('input[name="caption"]').fill("Проверенная подпись");
  await initialCard.getByRole("button", { name: "Сохранить" }).click();
  await expect(page.getByText("Подпись и привязка обновлены.")).toBeVisible();
  await expect(page.getByText("Проверенная подпись")).toBeVisible();

  // A separate disposable image exercises deletion; keep the approved QA
  // image available for the subsequent export/integrity verification.
  await page.locator('select[name="museum_entry_id"]').first().selectOption(entryId!);
  await page.locator('input[name="alt"]').first().fill("QA: временное изображение для удаления");
  await page.locator('input[type="file"]').setInputFiles(process.env.MUSBREAD_E2E_IMAGE_PATH!);
  await page.getByRole("button", { name: "Загрузить изображение" }).click();
  await expect(page.getByText("Изображение добавлено.")).toBeVisible();
  const disposable = page.locator("article.item").filter({
    has: page.getByRole("img", { name: "QA: временное изображение для удаления" }),
  });
  page.once("dialog", dialog => dialog.accept());
  await disposable.getByRole("button", { name: "Удалить" }).click();
  await expect(page.getByText("Изображение удалено.")).toBeVisible();
  await expect(page.getByRole("img", { name: "QA: временное изображение для удаления" })).toHaveCount(0);
  await expect(page.getByRole("img", { name: "QA: экспонат на тестовом изображении" })).toBeVisible();


});

test("CP-39D: редактор связывает опубликованную новость с экскурсией и событием через закрытую CMS", async ({ page }) => {
  await page.goto("/admin/login");
  await page.locator('input[name="username"]').fill(process.env.MUSBREAD_E2E_USERNAME!);
  await page.locator('input[type="password"]').fill(process.env.MUSBREAD_E2E_PASSWORD!);
  await page.locator('button[type="submit"]').click();
  await page.goto("/admin/museum-media");
  const newsOption = page.locator('select[name="museum_entry_id"] option')
    .filter({ hasText: "QA: публикация из настоящего браузера" });
  const newsId = await newsOption.first().getAttribute("value");
  expect(newsId).not.toBeNull();

  await page.goto(`/admin/museum-entries/${newsId}/relations`);
  await expect(page.getByRole("heading", { name: "Связанные материалы" })).toBeVisible();
  const excursion = page.locator('select#related-entries option').filter({ hasText: "Демонстрационная экскурсия" });
  const event = page.locator('select#related-events option').filter({ hasText: "QA: музейное событие из браузера" });
  const draft = page.locator('select#related-events option').filter({ hasText: "QA: закрытый черновик" });
  const excursionId = await excursion.getAttribute("value");
  const eventId = await event.getAttribute("value");
  const draftId = await draft.getAttribute("value");
  expect(excursionId).not.toBeNull();
  expect(eventId).not.toBeNull();
  expect(draftId).not.toBeNull();

  await page.locator('select#related-entries').selectOption([excursionId!]);
  await page.locator('select#related-events').selectOption([eventId!, draftId!]);
  await page.getByRole("button", { name: "Сохранить связи" }).click();
  await expect(page.getByRole("status")).toContainText("Связи сохранены");
  await expect(page.locator('select#related-entries')).toHaveValues([excursionId!]);
  const selectedEvents = await page.locator('select#related-events').evaluate((element) =>
    Array.from((element as HTMLSelectElement).selectedOptions).map((option) => option.value).sort());
  expect(selectedEvents).toEqual([eventId!, draftId!].sort());
});

test("CP-40D: администратор создаёт дерево и меняет порядок соседей через интерфейс", async ({ page }) => {
  await page.goto("/admin/login");
  await page.locator('input[name="username"]').fill(process.env.MUSBREAD_E2E_USERNAME!);
  await page.locator('input[type="password"]').fill(process.env.MUSBREAD_E2E_PASSWORD!);
  await page.locator('button[type="submit"]').click();
  await expect(page).toHaveURL(/\/admin/);

  const create = async (slug: string, parentId?: string) => {
    await page.goto("/admin/resource/museum-section-resource/museum-section-form-page");
    await page.locator('input[name="title"]').fill("QA: " + slug);
    await page.locator('input[name="slug"]').fill(slug);
    if (parentId) await page.locator('select[name="parent_id"]').selectOption(parentId);
    await page.locator('select[name="status"]').selectOption("published");
    await page.locator('button[type="submit"]').filter({ hasText: "Save" }).click();
    await expect(page).toHaveURL(/museum-section-form-page\/\d+/, { timeout: 10_000 });
    return page.url().split("/").at(-1)!;
  };

  const root = await create("qa-tree-root");
  await create("qa-tree-child-a", root);
  await create("qa-tree-child-b", root);
  await page.goto("/admin/museum-sections/tree");
  await expect(page.getByRole("heading", { name: "Карта структуры сайта" })).toBeVisible();
  await expect(page.locator('.tree>li[data-section="qa-tree-root"]')).toHaveAttribute("data-depth", "0");
  await expect(page.locator('.tree>li[data-section="qa-tree-child-a"]')).toHaveAttribute("data-depth", "1");
  await expect(page.locator('.tree>li[data-section="qa-tree-child-b"]')).toHaveAttribute("data-depth", "1");
  const initial = await page.locator(".tree>li").evaluateAll((items) => items.map((item) => item.getAttribute("data-section")));
  expect(initial.indexOf("qa-tree-child-a")).toBeLessThan(initial.indexOf("qa-tree-child-b"));
  await page.getByRole("button", { name: "Опустить раздел QA: qa-tree-child-a среди соседних" }).click();
  await expect(page.getByRole("status")).toContainText("Порядок соседних разделов обновлён");
  const after = await page.locator(".tree>li").evaluateAll((items) => items.map((item) => item.getAttribute("data-section")));
  expect(after.indexOf("qa-tree-child-b")).toBeLessThan(after.indexOf("qa-tree-child-a"));

  await page.goto(`/admin/resource/museum-section-resource/museum-section-form-page/${root}`);
  const possibleParentIds = await page.locator('select[name="parent_id"] option').evaluateAll(
    (options) => options.map((option) => (option as HTMLOptionElement).value));
  expect(possibleParentIds).not.toContain(root);
  await expect(page.locator('select[name="parent_id"]')).not.toContainText("qa-tree-child-a");
  await expect(page.locator('select[name="parent_id"]')).not.toContainText("qa-tree-child-b");
});

test("CP-41D: штатные фильтры MoonShine, поиск и количество связанных объектов", async ({ page }) => {
  await page.goto("/admin/login");
  await page.locator('input[name="username"]').fill(process.env.MUSBREAD_E2E_USERNAME!);
  await page.locator('input[type="password"]').fill(process.env.MUSBREAD_E2E_PASSWORD!);
  await page.locator('button[type="submit"]').click();
  const index = "/admin/resource/museum-entry-resource/museum-entry-index-page";
  await page.goto(index);
  await expect(page.locator("body")).toContainText("Готовность к экспорту");
  await expect(page.locator("body")).toContainText("Связанных материалов");
  await expect(page.locator("body")).toContainText("Раздел сайта");
  const newsRow = page.locator("tbody tr").filter({ hasText: "QA: публикация из настоящего браузера" });
  await expect(newsRow).toBeVisible();
  await expect(newsRow).toContainText("Настроить");
  await expect(newsRow).toContainText("Открыть");
  await expect(newsRow).toContainText("1"); // one related excursion, two linked events
  await expect(newsRow).toContainText("2");
  await page.goto(index + "?" + new URLSearchParams({ "filter[publication_state]": "ready" }));
  await expect(page.locator("tbody tr").filter({ hasText: "QA: публикация из настоящего браузера" })).toBeVisible();
  await page.goto(index + "?" + new URLSearchParams({ "filter[publication_state]": "draft" }));
  await expect(page.locator("tbody tr").filter({ hasText: "QA: публикация из настоящего браузера" })).toHaveCount(0);
  await page.goto(index + "?" + new URLSearchParams({ "filter[link_state]": "linked" }));
  await expect(page.locator("tbody tr").filter({ hasText: "QA: публикация из настоящего браузера" })).toBeVisible();
  await page.goto(index + "?" + new URLSearchParams({ "filter[link_state]": "unlinked" }));
  await expect(page.locator("tbody tr").filter({ hasText: "QA: публикация из настоящего браузера" })).toHaveCount(0);
  await page.goto(index + "?" + new URLSearchParams({ "filter[museum_section_id]": "unassigned" }));
  await expect(page.locator("tbody tr").filter({ hasText: "QA: публикация из настоящего браузера" })).toBeVisible();
  await page.goto(index + "?" + new URLSearchParams({ search: "qa-browser-news" }));
  await expect(page.locator("tbody tr").filter({ hasText: "QA: публикация из настоящего браузера" })).toBeVisible();
  await expect(page.locator("tbody tr").filter({ hasText: "Демонстрационная экскурсия" })).toHaveCount(0);
});

test("CP-42D: закрытый предпубликационный отчёт и ссылки на исправление в MoonShine", async ({ page }) => {
  await page.goto("/admin/login");
  await page.locator('input[name="username"]').fill(process.env.MUSBREAD_E2E_USERNAME!);
  await page.locator('input[type="password"]').fill(process.env.MUSBREAD_E2E_PASSWORD!);
  await page.locator('button[type="submit"]').click();

  const index = "/admin/resource/museum-entry-resource/museum-entry-index-page";
  await page.goto(index);
  const newsRow = page.locator("tbody tr").filter({ hasText: "QA: публикация из настоящего браузера" });
  await expect(newsRow.getByRole("link", { name: "Открыть отчёт" })).toBeVisible();
  await newsRow.getByRole("link", { name: "Открыть отчёт" }).click();
  await expect(page).toHaveURL(/\/admin\/museum-content\/preflight#entry-\d+$/);
  await expect(page.getByRole("heading", { name: "Проверка перед публикацией" })).toBeVisible();
  await expect(page.getByText("Критических ошибок готовых записей:")).toBeVisible();

  const news = page.locator("article.record").filter({ hasText: "QA: публикация из настоящего браузера" });
  await expect(news).toBeVisible();
  await expect(news).toContainText("Готово к следующей выгрузке");
  await expect(news).toContainText("Часть связанных материалов или событий не попадёт");
  await expect(news.getByRole("link", { name: "Исправить в CMS" })).toBeVisible();
  await expect(news.getByRole("link", { name: "Предпросмотр" })).toBeVisible();
  await expect(news.getByRole("link", { name: "Связи" })).toBeVisible();
  await news.getByRole("link", { name: "Предпросмотр" }).click();
  await expect(page.getByText("Демонстрационная публикация из браузерного теста")).toBeVisible();
});


test("CP-43D: отчёт проверяет события афиши и открывает редактор события", async ({ page }) => {
  await page.goto("/admin/login");
  await page.locator('input[name="username"]').fill(process.env.MUSBREAD_E2E_USERNAME!);
  await page.locator('input[type="password"]').fill(process.env.MUSBREAD_E2E_PASSWORD!);
  await page.locator('button[type="submit"]').click();

  await page.goto("/admin/resource/museum-event-resource/museum-event-index-page");
  const row = page.locator("tbody tr").filter({ hasText: "QA: музейное событие из браузера" });
  await expect(row.getByRole("link", { name: "Открыть отчёт" })).toBeVisible();
  await row.getByRole("link", { name: "Открыть отчёт" }).click();
  await expect(page).toHaveURL(/\/admin\/museum-content\/preflight#event-\d+$/);
  await expect(page.getByRole("heading", { name: "События афиши" })).toBeVisible();
  await expect(page.getByText("Критических ошибок готовых событий:")).toBeVisible();
  const item = page.locator("article.record").filter({ hasText: "QA: музейное событие из браузера" });
  await expect(item).toContainText("Готово к следующей выгрузке");
  await expect(item).toContainText("SEO-заголовка события");
  await item.getByRole("link", { name: "Исправить событие" }).click();
  await expect(page.locator('input[name="title"]')).toHaveValue('QA: музейное событие из браузера');
});


test("CP-44D: реальная CMS сравнивает новые материалы с архивом локального снимка", async ({ page }) => {
  await page.goto("/admin/login");
  await page.locator('input[name="username"]').fill(process.env.MUSBREAD_E2E_USERNAME!);
  await page.locator('input[type="password"]').fill(process.env.MUSBREAD_E2E_PASSWORD!);
  await page.locator('button[type="submit"]').click();
  await page.goto("/admin/resource/museum-entry-resource/museum-entry-index-page");
  await expect(page.getByRole("link", { name: "Сравнить" }).first()).toBeVisible();
  await page.getByRole("link", { name: "Сравнить" }).first().click();
  await expect(page).toHaveURL(/\/admin\/museum-content\/compare$/);
  await expect(page.getByRole("heading", { name: "Сравнение подготовленной и предыдущей версий" })).toBeVisible();
  await expect(page.getByText("Подтверждённый локальный базовый снимок недоступен")).toHaveCount(0);
  await expect(page.getByText("SHA-256 исходного снимка")).toBeVisible();
  const news = page.locator("article[data-action='added']").filter({ hasText: "news:qa-browser-news" });
  await expect(news).toBeVisible();
  await expect(news).toContainText("Добавится");
  const event = page.locator("article[data-action='added']").filter({ hasText: "qa-browser-event" });
  await expect(event).toBeVisible();
  await page.getByRole("link", { name: "Открыть подробный отчёт" }).click();
  await expect(page).toHaveURL(/\/admin\/museum-content\/preflight$/);
});
