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

Подробнее: [ROADMAP](docs/ROADMAP.md), [REQUIREMENTS](docs/REQUIREMENTS.md), [ARCHITECTURE](docs/ARCHITECTURE.md), [SYNC](docs/SYNC.md).

**Не размещать в публичном репозитории** приватные документы заказчика, логины, личные данные, секреты и материалы интервью.

## Локальный релиз (до обследования музея)

Скрипт `scripts/release_site.py` сверяет SHA256 CMS-экспорта с манифестом, проверяет каждый статический файл, создаёт неизменяемую версию в `deploy/local/releases/` и атомарно переключает симлинк `current` с возможностью `rollback`. Это проверка схемы релизов на Mac mini, **а не** реализация закрытого сетевого канала музея. Каталог `deploy/local/` исключён из Git.

## Типизированные материалы музея

В MoonShine есть раздел «Материалы музея»: `page`, `news`, `excursion`, `exhibition`, `document`. С помощью `museum:export` только опубликованные и наступившие по времени записи попадают в `entries` статического JSON; Next.js создаёт информационные маршруты `/museum/`, `/news/`, `/excursions/`, `/exhibitions/`, `/documents/`. Все примеры — выдуманные демонстрационные данные.
