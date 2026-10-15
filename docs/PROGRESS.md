# MusBread — checkpoints

Актуальная рабочая нарезка по подзадачам: **[SPRINT-2026-10-15.md](SPRINT-2026-10-15.md)**.

Актуальная детализированная дорожная карта, включая расходы: **[CHECKPOINTS.md](CHECKPOINTS.md)**.

Дата: 15 октября 2026. Исходный статус закупки: заявка 39 000 ₽, результаты ожидаются 20 октября. Все материалы сайта и мероприятия сейчас демонстрационные.

| ID | Статус | Подтверждение |
|---|---|---|
| MB-001 Требования | DONE (база) | docs/REQUIREMENTS.md; предстоит расширить матрицу по каждому носителю |
| MB-002 Архитектура | DONE (проект) | docs/ARCHITECTURE.md, deployment в музей — после согласования |
| MB-003 Laravel | DONE | PHP 8.4.26 native, Laravel 13.36.0, php artisan test |
| MB-004 MoonShine | PARTIAL | MoonShine 4.19.5, CRUD событий и материалов, логин и роли проверены HTTP-тестами; реальный Playwright E2E CMS/login/editor/media готов; ручной Safari аудит ещё не закрыт |
| MB-005 Next.js | DONE (прототип) | 16.4.1 static export, страницы главная/афиша/событие |
| MB-006 CI | DONE (проверка) | GitHub Actions web-ci.yml: PHP, Python, Next.js |
| MB-007 Модели контента | PARTIAL | MuseumEvent + MuseumEntry (страницы/новости/экскурсии/выставки/документы), SEO, CRUD и статический экспорт работают; медиатека/сотрудники и сложная иерархия ещё в очереди |
| MB-008 Роли | DONE (v1) | Системный Admin/Editor, запрет доступа редактора к пользователям/ролям на уровне серверных ресурсов, HTTP тесты |
| MB-009 Экспорт | DONE (v1) | museum:export и Python fixture parity: SHA256 manifest |
| MB-010 Publisher | DONE (pre-award); #9 production blocked | SHA-256, версионирование, rollback, часовой schedule и demo_publish.sh готовы. Очередь и журнал готовы в коде; добавлены защита одновременного enqueue, проверяемое восстановление зависших публикаций и отказ от повреждённого rollback. Worker и переход на queue выключены до конфигурации. Межконтурный канал и промышленный запуск остаются после согласования |
| MB-011 Статический сайт | DONE (v1) | Next.js строит HTML без API к CMS |
| MB-012 Сквозной тест | DONE (pre-award) | DONE (pre-award): настоящий браузерный CRUD MoonShine → JSON/медиа/SHA256 → изолированный Next.js static build из браузерных материалов; CI дополнительно проверяет локальный publisher и rollback. Физический канал музея ещё не готов. |
| MB-013 Навигация | PARTIAL | главная, афиша, хлебные крошки, поиск событий, мобильное меню; полная структура ТЗ впереди |
| MB-014 UX/UI | PARTIAL | нейтральный адаптивный дизайн без согласованной айдентики |
| MB-015 Доступность | PARTIAL | skip link, focus-visible, мобильное меню, русскоязычная разметка; полный аудит/scale 200% и тесты — впереди |
| MB-016 CMS-редактор | DONE (pre-award); GPL check remains | формы событий и SEO-поля, WYSIWYG + двойная HTML-очистка реализованы, журнал аудита только для Admin; отдельная закрытая медиатека с upload/WebP/alt/caption/drag-and-drop и SHA-256 экспортом, браузерная ручная проверка ещё впереди |
| MB-017 Demo/UAT | PARTIAL | CI green, автоматические Chromium Playwright + axe-core a11y проверки публичного UI; закрытый MoonShine CMS Playwright E2E через временный стенд; Playwright WebKit на Mac mini 9/9, ручной Safari/Chromium-GOST и официальный UAT ещё впереди; ручная проверка CMS, Safari и протокол ещё впереди |

## Локальное окружение

- Homebrew `php@8.4` установлен нативно, PHP-FPM не запускаем постоянно.
- Composer PHAR находится в `~/.local/share/musbread/composer.phar` и запускается `~/.local/bin/musbread-composer`.
- Node.js/npm нативно. Laravel SQLite dev, без постоянно запущенного контейнера Docker.
- Локальные значения секретов, базы и .env не коммитить. MoonShine /admin требует вход; существование формы входа не означает созданную учётную запись.

## Не запускать до согласования

Реальные билетные/платёжные сервисы, клиентские сети, обработку ПДн, финальную айдентику. Официальную публикацию на musbread.ru только после подписания контракта и согласования музеем.

## CP-18 (предконтрактные шаблоны, issue #10)

Подготовлены публичный и закрытый Nginx, systemd worker/timer, правило отсутствия прямого backend в публичной выдаче и инструкция восстановления. Это **не** настроенные серверы заказчика и не выполненное резервирование реальной БД. Проверка в CI добавлена отдельно.

## CP-19 — security baseline (issue #11)

Добавлен scripts/audit_public_artifacts.py. Composer audit и production npm audit включены в CI. CSP из SHA-256 inline-JS и HTTP rate-limit POST (8/мин login, 30/мин upload) проверены; Playwright Chromium/WebKit, CSRF, SQLi-like slug и HTML sanitization. Продакшен TLS/firewall/IP и независимый pentest ещё не проведены.
