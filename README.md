# MusBread — сайт и фирменный стиль Музея Хлеба

**Статус: предконтрактный прототип, не официальный сайт музея.**

Проект подготовки к возможному исполнению закупки № 0372200172326000015. Ветка `main` — основной код, GitHub — source of truth; GitVerse зеркалируется через GitHub Actions. Все текущие события и тексты **тестовые**, бренд и контент не согласованы с музеем.

## Окружение Mac mini

Нативно установлено через Homebrew: `php@8.4`. Composer хранится как проверенный PHAR в `~/.local/share/musbread/composer.phar` и запускается командой `~/.local/bin/musbread-composer`. Node.js/npm уже доступны на Mac mini.

```sh
cd /Volumes/ArvectumSSD/Arvectum/repos/musbread
python3 scripts/publish_snapshot.py --check
python3 -m unittest discover -s tests -v
cd apps/web
npm ci
npm run lint
npm run build
# Проверить локальную публикацию и развёртывание:
cd ../..
python3 scripts/release_site.py deploy
python3 scripts/release_site.py verify
# При необходимости: python3 scripts/release_site.py rollback
# Просмотр статических файлов: python3 -m http.server 8765 -d apps/web/out
```

Laravel:
```sh
cd /Volumes/ArvectumSSD/Arvectum/repos/musbread/apps/cms
export PATH="/opt/homebrew/opt/php@8.4/bin:$HOME/.local/bin:$PATH"
musbread-composer install
php artisan migrate
php artisan db:seed --class=DemoMuseumContentSeeder # только локально, не на проде
php artisan museum:export                   # выгрузка из CMS в Next.js
php artisan test
php artisan serve --host=127.0.0.1 --port=8766
```

## Архитектура
- `apps/cms`: Laravel 13 / MoonShine 4 / PHP 8.4+ (закрытый контур). MoonShine установлен на `/admin`, доступ требует входа; локальный пользователь создаётся отдельно без паролей в Git.
- `apps/web`: Next.js 16, статические страницы; читает только экспорт из CMS `src/data/published.json`, никакого HTTP-доступа к Laravel у публичных страниц нет.
- `fixtures/content.json`: исключительно тестовые материалы, не от имени музея.
- `scripts/publish_snapshot.py`: fixture-exporter с SHA256 manifest; Laravel-команда `museum:export` выпускает тот же формат. Для промышленной схемы ещё нужны согласованный канал, полная атомарность пакетов, реестр версий и rollback.

Мелкие подзадачи текущего спринта: [SPRINT-2026-10-15](docs/SPRINT-2026-10-15.md).

Подробнее: [ROADMAP](docs/ROADMAP.md), [REQUIREMENTS](docs/REQUIREMENTS.md), [ARCHITECTURE](docs/ARCHITECTURE.md), [SYNC](docs/SYNC.md).

**Не размещать в публичном репозитории** приватные документы заказчика, логины, личные данные, секреты и материалы интервью.

## Локальный релиз (до обследования музея)

Скрипт `scripts/release_site.py` сверяет SHA256 CMS-экспорта с манифестом, проверяет каждый статический файл, создаёт неизменяемую версию в `deploy/local/releases/` и атомарно переключает симлинк `current` с возможностью `rollback`. Это проверка схемы релизов на Mac mini, **а не** реализация закрытого сетевого канала музея. Каталог `deploy/local/` исключён из Git.

## Типизированные материалы музея

В MoonShine есть раздел «Материалы музея»: `page`, `news`, `excursion`, `exhibition`, `document`. С помощью `museum:export` только опубликованные и наступившие по времени записи попадают в `entries` статического JSON; Next.js создаёт информационные маршруты `/museum/`, `/news/`, `/excursions/`, `/exhibitions/`, `/documents/`. Все примеры — выдуманные демонстрационные данные.

## Полная демонстрационная публикация без Docker

`sh scripts/demo_publish.sh` последовательно выполняет экспорт Laravel, сборку Next.js, размещение версии и проверку контрольных сумм. Laravel Scheduler знает почасовое задание `museum:export`, но **сам Scheduler на Mac mini постоянно не запущен**: оно требует отдельного schedule runner и само по себе не передаёт файлы в сеть музея.

## Редактор rich text

Редактирование текстов в MoonShine выполняется на самохостинговом TinyMCE, ввод фильтруется HTMLPurifier, публичный рендер повторно очищает HTML с помощью `sanitize-html` (MIT). Реальные изображения, вложения и медиатека будут добавлены отдельно. TinyMCE распространяется по GPL-2.0-or-later, совместимость его включения в передаваемый заказчику комплект исходников следует согласовать до сдачи.

## Браузерные проверки

В `apps/web` установлен Playwright (Chromium) и команда `npm run test:e2e`. Сначала выполните `npm run build`. Тестовый веб-сервер запускается автоматически на 127.0.0.1:18765 (порт 8765 занят другим сервисом Mac mini), после теста выключается. Тесты охватывают навигацию, поиск афиши, мобильное меню, клавиатурный skip-link и axe-core. Технический протокол: docs/QA_PROTOCOL.md. Закрытый интерфейс MoonShine требует отдельной E2E-проверки.

## Журнал изменений

Редактирование событий и музейных материалов записывается в закрытую таблицу museum_audit_records (тип, ID объекта, действие, ID оператора и имена изменённых полей). Значения полей и тела текстов в журнал не дублируются. Раздел «Журнал изменений» в MoonShine доступен только администратору на чтение. В публичный JSON он не выгружается.

## Медиатека (закрытая CMS)

Из MoonShine доступна ссылка «Медиатека» → /admin/museum-media. Редактор прикрепляет изображение к существующему материалу и указывает обязательный alt-текст. Drag-and-drop поддерживается; обычный файловый выбор остаётся доступен с клавиатуры. Допустимы JPEG, PNG и WebP размером до 5 МБ и 4096 × 4096 пикселей. PHP GD перекодирует содержимое в WebP, удаляя EXIF и исходное имя; оригинал хранится только в закрытом хранилище CMS. Метаданные можно изменить или удалить.

Экспорт музейных материалов выпускает изображения **только опубликованных страниц** в public/media с уникальным путём по SHA-256 и проверяемым манифестом. При снятии публикации отсутствующие в новой выборке файлы очищаются из сгенерированной public/media. Исходные закрытые файлы не попадают в публичный Next.js напрямую и не коммитятся в Git. Сценарии и угрозы: docs/MEDIA.md.

## Отложенные публикации и очередь

В дополнение к прямому часовому экспорту готов механизм Laravel database queue и закрытый журнал попыток публикации. Чтобы не нарушить действующий локальный стенд, он по умолчанию выключен (MUSEUM_USE_PUBLISH_QUEUE=false): работающая схема прямого часового экспорта сохранена. Инструкция для дальнейшего подключения: docs/PUBLICATION_QUEUE.md. Постоянный worker и промышленный межконтурный канал ещё не развёрнуты.

## Полный браузерный E2E закрытой CMS

Запустить из корня: python3 scripts/qa_cms_browser.py. Создаётся временная SQLite в системном temp-каталоге и одноразовый тестовый администратор со случайным паролем только для этого запуска. PHP служит только на 127.0.0.1, затем завершается. Тест выполняет настоящий login → создание новости через TinyMCE и события, исключение черновика из публикации → загрузку тестовой картинки в приватную медиатеку → выгрузку CMS и проверку SHA-256. Исходная рабочая SQLite и постоянные пользователи Mac mini не затрагиваются.


Для дополнительной проверки Safari-подобного движка на Mac mini: cd apps/web && npx playwright install webkit && npm run test:webkit. Это тест WebKit Playwright, а не официальный сертификат Safari.

### CMS в WebKit

Для изолированной проверки закрытой CMS: MUSBREAD_E2E_BROWSER=webkit python3 scripts/qa_cms_browser.py. По умолчанию используется Chromium. Пароль и SQLite временные.

## Публикация и восстановление

Скрипт `python3 scripts/release_site.py verify` проверяет содержимое immutable release; `rollback` отказывает при несовпадении хешей. Операции защищены файловой блокировкой.

Laravel с опциональной очередью (`MUSEUM_USE_PUBLISH_QUEUE=true`) сериализует запросы, хранит журнал и периодически восстанавливает неактуальные queued/running состояния командой `php artisan museum:recover-stale-publications`. Постоянно запущенный worker *не включён*: он требуется только на согласованной инфраструктуре заказчика. Перед включением соблюдать рабочий timeout <=600 секунд и DB_QUEUE_RETRY_AFTER >=900 секунд.

## Сквозной browser-to-static E2E

Запуск: python3 scripts/qa_cms_browser.py. Создаётся временная MoonShine CMS, браузер отправляет новость, событие и черновик, затем из экспорта в отдельной временной копии Next.js строится реальный HTML и WebP. Проверяется отсутствие закрытых записей. Основной frontend не затрагивается; webpack нужен для временной директории с симлинком node_modules.

## CSP и rate-limit

Строгая для inline-JavaScript CSP автоматически вычисляется командой:
    python3 scripts/build_csp.py apps/web/out --output /tmp/musbread-csp.conf

Скрипт sh scripts/demo_publish.sh помещает build-specific CSP в deploy/local/csp.generated.conf (не публичный каталог). В реальном контуре конфигурацию Nginx необходимо установить вместе с релизом и перезагрузить Nginx, включая rollback. Порядок и ограничения: docs/SECURITY.md и infra/README.md.

Laravel ограничивает POST входа MoonShine и загрузки файлов; Nginx содержит дополнительный шаблон ограничения. Пентест и реальные доступы музея не выполнялись.


## Предконтрактный браузерный аудит

После сборки Next.js в apps/web выполнить npm run test:e2e (Chromium),
npm run test:webkit (WebKit) либо npm run test:chrome (установленный Google Chrome).
Все три команды пересоздают CSP из текущей сборки; Chrome идёт последовательно.
На Mac mini команда sh scripts/qa_native_safari.sh открывает и закрывает собственное окно
настоящего Safari для проверки трёх публичных страниц. В Linux CI она не запускается.
Проверка ссылок: python3 scripts/audit_static_navigation.py apps/web/out.
Актуальный QA отчёт: docs/QA_PREAWARD_REPORT.md.

## Интеграции до победы

Семь типов интеграций из ТЗ описаны в docs/INTEGRATIONS.md. PHP hub и adapters находятся в apps/cms/app/Integrations; по умолчанию всё выключено. Публичный Next.js имеет только безопасные типизированные HTTPS-ссылки, тестируемые через npm run test:integrations. Реальные билеты и персональные заявки не подключены.

## Интервью, исследование UX и шаблоны концепций

Рабочий бриф в docs/research/INTERVIEW_BRIEF.md, UX методика и согласия в docs/research, пустой CSV для реальных анонимных попыток. Подсчёт после исследования: python3 scripts/score_ux.py <private_results.csv> (два раунда, минимум 5 участников каждый, порог 85%). Три пятистраничных PDF-каркаса и HTML-источники — docs/design/templates. Пересборка на Mac: cd apps/web && node scripts/build_concept_templates.mjs. Эти PDF пока не являются финальными концепциями.
