# CODE-AUDIT-05 — безопасность CMS и зависимостей

**20.10.2026.** Mac mini / ArvectumSSD, локальная ветка MusBread. Живой сайт, DNS, ЕИС и исходные музейные документы не изменялись. Никаких новых вопросов заказчику и push.

## Выявлено и исправлено

**1. Лишние framework-маршруты к закрытым документам.** Диск local указывал на storage/app/private, но одновременно имел serve=true. Настоящий php artisan route:list вывел два подписанных Laravel GET/PUT-маршрута storage/{path}. Они требуют framework-подпись и сами по себе не доказывают анонимный обход, но создают ненужный обход привычной группы авторизации MoonShine при наличии подписанной ссылки.

Для приватного local установлено serve=false. Оба маршрута больше не регистрируются. GET и PUT по /storage/museum/media/private-original.webp возвращают 404; содержимое приватного файла не меняется. Контроллеры с разграничением прав на разделы остаются единственной точкой доступа. Добавлены два регрессионных теста MuseumPrivateStorageRoutesTest.php. Официальный статический сайт и отдельно проверенные публичные документы не затронуты.

**2. Подмена приватных WebP перед просмотром.** Ранее MuseumMediaController::preview проверял только наличие файла. Теперь проверяются symlink, ожидаемый размер, SHA-256 и формат WebP. Хешируется именно буфер, который будет возвращён посетителю CMS, чтобы не создавать отдельное окно между проверкой SHA и выдачей. Повреждение, замена содержимого при прежнем размере, отсутствие файла и symlink дают HTTP 404. Добавлен реальный HTTP feature-тест в MuseumMediaTest.php. Существующие ACL, Content-Type, nosniff и приватное кеширование сохранены.

## Lockfile dependency audit

- Composer на закреплённом composer.lock: 0 известных security advisory и 0 abandoned dependencies; Composer audit --locked --format=json, exit 0.
- npm --omit=dev на package-lock.json: 0 известных уязвимостей production dependencies; exit 0.
- npm с devDependencies: 5 записей High, одна транзитивная цепочка из @next/eslint-plugin-next, fast-glob, micromatch и braces; первичный GHSA-vfj7-8cjw-p6xm, DoS глубокой вложенностью масок. Установлен braces 3.0.3, npm registry предлагает 3.0.3 как последнюю версию ветки 3.x. Безопасного совместимого исправления не найдено. npm audit fix предлагает несовместимое по архитектуре понижение eslint-config-next до 14.2.35 при Next 16. Этого не делали, lock-файлы не меняли.
- В существующих GitHub Actions уже включён еженедельный read-only Composer/npm production audit. Dev advisory остаётся контролируемым открытым техническим риском, не заявленной дырой публичного сайта.

## Дополнительно рассмотрено

Проверены существующие реализация MoonShine Authenticate, MuseumSectionAccess, санитарная очистка HTML от script/javascript/event-handler, ограничения SVG/GIF и проверка загружаемых PDF/DOCX/XLSX, включая вредоносные вложения/макросы; cache-lock и rate limiting. Действующие защитные правила и тесты уже есть. Доказанного нового недостатка в этих участках в текущем проходе не выявлено.

Открытые вопросы не для музея, а для инженерной очереди: dev advisory в braces, полный внешний пентест/AV/CDR, боевые настройки HTTPS/proxy/headers и потенциальное файловое race-window при прямом BinaryFileResponse для приватных документов. Эти пункты не объявлены завершёнными.

## Локальные журналы

- .local_archive/security-composer-audit-20261020.json
- .local_archive/security-npm-prod-20261020.json
- .local_archive/security-npm-full-20261020.json
- .local_archive/security-private-storage-tests-20261020.log
- .local_archive/security-full-python-20261020.log
- .local_archive/security-static-release-20261020.log
- .local_archive/security-full-laravel-20261020.log

Фактический статус полного Laravel-прогона отражать только по его итоговому результату, не по количеству выведенных точек. Полный Python: 360 тестов PASS. Static verify: 945 HTML, 101 PDF/DOCX, 259 исходных фото URL, 0 новых неисправных ссылок. Статический музей не менялся.

**Матрица ТЗ: 🟢85 / 🟡118 / 🔴122 из 325, без изменения.**
