# CP-RELEASE-HARDEN-20261021 — три инженерных улучшения MusBread

**21.10.2026.** Локальный репозиторий на ArvectumSSD/Mac mini. Без смены DNS, публикации на сервере музея, рассылок, изменения основного контента и Git push. Настоящий производственный запуск остаётся **NO-GO** до контракта, доступов, согласованного дизайна и проверки музеем.

## 1. Жёсткая граница времени публикации

- `PublishMuseumSnapshot` имеет per-job `timeout=540s` и `failOnTimeout=true`, то есть Laravel worker прекращает **очередное** исполнение до окончания `museum:publication-export` cache lock (`840s`). Конфигурация `retry_after >=900s`; восстановление упавшего worker допустимо только **после** истечения lock TTL. Три срока проверяет pre-start `museum:cache-check --require-queue-worker`. `RecoverStalePublications` использует единую константу TTL.
- Шаблон единственного Linux systemd worker согласован с `--timeout=540` и `TimeoutStopSec=600`. Retry при сработавшем hard timeout не должен стартовать одновременно с долгим заданием. Отдельные ручные PHP вызовы вне штатного queue worker этими ограничениями **не защищены**. Поведение при SIGKILL или реальном отключении питания, автоматический restart на музейной машине — отдельная приёмка.
- Протестированы инварианты, очередность, stale recover и взаимная эксклюзивность кеша. Не использовать PHP `queue:work --timeout=0` либо вызов `handle()` как метод production-публикации.

## 2. npm-dev advisory: изоляция и контроль до upstream fix

- Выполнен текущий `npm audit`: **production: 0 уязвимостей**, **dev: 5 High** — все одна цепочка `eslint-config-next 16.4.1 → @next/eslint-plugin-next → fast-glob → micromatch → braces 3.0.3`, исходное advisory `GHSA-vfj7-8cjw-p6xm` (рекурсивный DoS). На 21 октября npm возвращает `braces@3.0.3` как последнюю версию, поэтому безопасного upstream исправления **нет**. Предлагаемое `npm audit fix --force` понижает `eslint-config-next` до несовместимого 14.x; **не применять**.
- Добавлен строгий read-only `scripts/audit_npm_release_security.py`: полноценный `npm audit --omit=dev` должен быть **0**; из полного аудита разрешена **только эта ровно одна известная цепочка**. Новое advisory, другая версия графа либо переход любой уязвимой зависимости в production дают FAIL. После выхода исправления скрипт допускает 0 dev advisory автоматически. Закреплён в еженедельном GitHub Actions dependency-review.
- Исключение — **принятый, а не устранённый** dev-риск. В production устанавливать только production npm зависимости; ESLint и произвольные glob patterns из недоверенных внешних источников на production-машине не запускать. Трекать upstream обновления отдельно.

## 3. Автоматический preflight / gate

```bash
cd /Volumes/ArvectumSSD/arvectum/repos/musbread
.venv/bin/python scripts/preflight_museum_release.py
# или: cd apps/web && npm run preflight:museum
```

По умолчанию офлайн: проверка исходного сборщика (945 HTML, реальные внутренние ссылки, 101 PDF/DOCX по SHA-256, 255 фото), запрет индексации staging, пустой staging sitemap, защитный шаблон Nginx и **реальная изолированная репетиция двух версий сайта с откатом** через production-кандидат `release_site.py`. Репетиция пишет **только** во временный каталог `.local_archive` на ArvectumSSD и удаляет его. Никаких рабочих release pointers или серверов не переключает.

После выделения серверов и явного согласования боевого домена, **не до переключения**:

```bash
.venv/bin/python scripts/preflight_museum_release.py \
    --release-root /srv/musbread/public \
    --live-url https://muzei-xleb.ru
```

Это **только чтение**: проверяет существующие SHA текущего и предыдущего immutable releases, наличие работоспособной rollback-target, TLS не ниже 1.2 и hostname verification, HTTPS 200 главной, security headers CSP/HSTS/nosniff, отсутствие `noindex`, открытые robots и непустой sitemap с нужным доменом, пример старых URL→301→правильная локальная цель по source-verified Nginx redirect map. Полный ручной пострелизный обход, TLS/frontend config на двух хостах, доступность из РФ, настоящие редакционные SLA, UAT, пентест, работоспособность билетов и PDF не доказываются одним preflight. Любая ошибка выдаёт FAIL, не меняя настройки сервера.

**Важно:** предконтрактный `apps/web/out` намеренно `Disallow: /` и имеет пустой sitemap; проверка живого сайта правильно даёт FAIL до согласованной замены SEO-настроек при cutover. Нельзя называть выпуск готовым к индексации без отдельного SEO-плана и утверждённого домена `www`/non-www.

## Итог фактических проверок (21 октября 2026)

| Проверка | Фактический результат |
|---|---|
| Laravel Feature и полный набор | **413/413 PASS, 4201 assertions**, в том числе тесты новой очереди |
| Python unittest полный набор | **374/374 PASS** (повторный запуск после исправления ожиданий и регенерации матрицы) |
| ESLint / `npm run lint` | **PASS** |
| npm strict dev-chain gate | **PASS**; production 0, dev 5 High, все известные и не исправленные upstream |
| `npm run preflight:museum` | **PASS**: 945 HTML, 148357 локальных ссылок и ресурсов, 101 исходный документ, 259 музейных фото URL, 255 сохранённых оригинальных файлов; откат PASS |
| `git diff --check` | **PASS**, матрица перегенерирована и детерминированность подтверждена полным Python-набором |

Локальные журналы: `.local_archive/final-php-suite.log`, `.local_archive/harden-python-final-attempt.log`, `.local_archive/final-web-lint.log`, `.local_archive/final-web-preflight.log`, `.local_archive/final-npm-audit.log`. Все эти журналы приватные и не включены в поставку.

## Критерии завершения

- PHP lint, адресные Laravel feature, полный Laravel и Python, тесты новых защитных ворот, `npm lint`, npm audit + локальный preflight должны пройти. Повторять после изменения кода.
- Технические тесты и self-contained preflight не увеличивают светофор ТЗ автоматически: **325 пунктов = 85 зелёных / 118 частичных / 122 красных** до подтверждения реальных внешних условий.
