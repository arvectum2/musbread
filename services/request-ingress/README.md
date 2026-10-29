# MusBread · приём обращений (техническая реализация)

Статус 29.10.2026: **код готов для изолированного тестирования, в промышленной инфраструктуре не включён**. Не меняет договорную модель: Nginx публичного сайта отдаёт только статические файлы Next.js. Обработчик `services/request-ingress/public/index.php` размещается **на отдельном изолированном DMZ-хосте**, а Laravel импортирует заявки *исходящим* mTLS-соединением по закрытой сети. Этот хост, канал и режим их сопровождения требуют согласования Заказчика.

## Схема

1. Браузер сайта делает HTTPS POST `/v1/requests` на отдельный адрес обработчика. Без HTTP API в Next.js. Включается **только** явным build-time флагом; иначе остаются действующие `mailto:`-формы.
2. Минимальный PHP 8.4+ со встроенными `sodium`, `pdo_sqlite`, `mbstring` валидирует поля, origin, версию согласия; 5 попыток на IP в минуту, honeypot, 8 КиБ максимум, 5000 ожидающих обращений. Входящие не пишутся в логи.
3. `sodium_crypto_box_seal` шифрует JSON на **публичный ключ** закрытого контура до записи. SQLite с WAL, `synchronous=FULL`, каталог 0700, БД 0600. На DMZ нет приватного ключа. Ответ 202 — **только после commit**, не обещание экскурсии.
4. Laravel-команда `museum:pull-requests` каждые 60 секунд (только после разрешения) делает GET `/internal/pull` через mTLS на приватном интерфейсе, расшифровывает, повторно валидирует и сохраняет в `museum_inbound_requests` с Laravel APP_KEY encryption. После commit отправляет ack; дубли по external_id не размножаются, ошибка/обрыв сохраняет данные в очереди до повторного poll.
5. Read-only раздел MoonShine «Обращения посетителей» виден **только суперпользователю**; в перечне нет имён/e-mail/текстов, детали отображаются только в авторизованном закрытом интерфейсе. Отдельный демо-журнал `MuseumRequest` не менялся.

## Блокировка включения по умолчанию

Никаких сертификатов, секретов, полученных от клиента персональных данных, DNS, боевых серверов или платных услуг **этот коммит не создаёт**. Перед включением: утверждение полей/согласия и версии политики, адресатов/регламента рассмотрения, сроков хранения/удаления, изолированной инфраструктуры, частной сети, mTLS/CA и ограничения брандмауэра; перенос клиентского и серверного кодов на санкционированные хосты; UAT и резервное копирование зашифрованных очередей.

## Настройка отдельного DMZ-сервера (пример)

Создать каталог базы **вне webroot**, права 0700, владелец PHP-FPM, отдельный пул:
`/var/lib/musbread-requests/queue.sqlite`. Копировать PHP-код в `/srv/musbread/request-ingress/public/index.php`.
Nginx: `infra/nginx/request-ingress.conf` (нужно заменить EXAMPLE hostname, **10.20.30.10**, сертификаты, путь сокета, DNS и сегмент). Внешний 443 предоставляет **только POST/OPTIONS и /health**; внутренний 8443 доступен лишь со стороны CMS по частной сети, требует клиентский сертификат. В PHP-FPM pool явно передать эти переменные как `env[NAME]=...` или через защищённый конфиг, поскольку `clear_env=yes` по умолчанию; хранить секреты вне корня веб-сервера.

```text
MUSEUM_INGRESS_DB=/var/lib/musbread-requests/queue.sqlite
MUSEUM_INGRESS_PUBLIC_KEY=<base64-32-byte-box-public-key>
MUSEUM_RATE_SECRET=<long-random-secret>
MUSEUM_INTERNAL_TOKEN=<long-random-secret-32+-chars>
MUSEUM_ALLOWED_ORIGIN=https://musbread.ru
MUSEUM_CONSENT_VERSION=<museum-approved-version>
```

Создать пару ключей через PHP sodium на доверенной **закрытой** машине, сохранить секретный ключ только на ней:
```sh
php -r '$p=sodium_crypto_box_keypair(); echo "PUBLIC=".base64_encode(sodium_crypto_box_publickey($p)).PHP_EOL; echo "SECRET=".base64_encode(sodium_crypto_box_secretkey($p)).PHP_EOL;'
```
Не выводить и не сохранять настоящий секретный ключ в Git, CI или общих логах; перенести через защищённый канал в закрытый секрет-хранилище. Для production обмен по внутреннему HTTPS нужен реальный клиентский TLS-сертификат от доверенного CA, отдельный от ключа sodium.

## Закрытый Laravel

Миграция `2026_10_29_210000_create_museum_inbound_requests.php` **только на согласованной базе**. Настройки `config/museum_requests.php`:

```text
MUSEUM_REQUEST_IMPORT_ENABLED=false       # true только после проверок
MUSEUM_REQUEST_INGRESS_PRIVATE_URL=https://requests-internal.example.invalid:8443
MUSEUM_REQUEST_INGRESS_TOKEN=<тот же внутренний секрет>
MUSEUM_REQUEST_SEAL_SECRET_KEY=<base64-box-secret-key>
MUSEUM_REQUEST_TLS_CLIENT_CERT=/secure/path/client.crt
MUSEUM_REQUEST_TLS_CLIENT_KEY=/secure/path/client.key
MUSEUM_REQUEST_TLS_CA=/secure/path/private-ca.crt
MUSEUM_REQUEST_CONSENT_VERSION=<museum-approved-version>
```

Запуск команды вручную: `php artisan museum:pull-requests`, при `MUSEUM_REQUEST_IMPORT_ENABLED=true` регистрируется ежеминутно в уже существующем Laravel Scheduler; нужен реально работающий `schedule:run` на закрытом сервере. Без флага команда **отказывает**. Вынести в мониторинг ошибки импорта, длину очереди и oldest age, но не данные заявителей.

## Статический Next.js

```text
NEXT_PUBLIC_MUSEUM_REQUESTS_ENABLED=0
NEXT_PUBLIC_MUSEUM_REQUESTS_ENDPOINT=https://requests.example.invalid/v1/requests
NEXT_PUBLIC_MUSEUM_REQUESTS_CONSENT_VERSION=<museum-approved-version>
```

Включать значение `1` **только после завершения серверной и правовой приёмки** и пересобирать Next.js. Эти переменные публичны в JS, в них не должно быть секретов. Для отключения выполнить повторную сборку с флагом `0`, в случае инцидента дополнительно блокировать POST на DMZ; статический fallback остаётся.

### CSP для статического сайта

При включении приёмщика выполнить генерацию CSP **с тем же официально одобренным origin**, что и в NEXT_PUBLIC_MUSEUM_REQUESTS_ENDPOINT. Иначе политики безопасности правильно заблокируют POST.

```sh
MUSEUM_REQUESTS_CSP_ORIGIN=https://requests.musbread.ru python3 scripts/build_csp.py apps/web/out --output apps/web/.csp-header.txt
```

Адрес requests.musbread.ru в примере условный (подлежит выделению/согласованию); этот параметр устанавливается только после согласования реального адреса музеем и должен присутствовать в воспроизводимом процессе сборки/публикации. При выключении шлюза origin нужно удалить; стандартный CSP разрешает connect-src только self.

## Устойчивость и ограничения

- Идемпотентность PHP `client_id` сохраняет один receipt в течение 7 суток (включая после ack); повтор при тайм-ауте не создаёт новый документ. Клиент отправляет криптографически случайный `client_id` и переиспользует его до изменения полей.
- `/internal/ack` может удалить только подтверждённый ID, но worker отправляет ack **после** commit. Без связи запрос остаётся в зашифрованной очереди; если CMS база потеряна, нужен её backup. SQLite backups делать штатным `.backup` / SQLite API, а не неатомарным копированием активного WAL.
- Поле `email` требуется для ответа. Никаких заявленных «броней» и передачи билетов/платежей.
- Сквозные TLS/изоляция 2 хостов, работа разрешённых доменов и юридическая модель обращения **не проверены**, потому что нет инфраструктуры музея.
- Нет управления согласованным сроком хранения/удаления: включать серверные формы до закрепления такого регламента нельзя; закрытая БД пока хранит записи до согласованной процедуры удаления. Не засчитывать соответствующие пункты ТЗ как выполненные только по локальным тестам.

## Тестирование на Mac mini (только синтетика)

```sh
python3 services/request-ingress/tests/test_ingress.py
(cd apps/cms && php artisan test --filter=MuseumInboundImportTest)
(cd apps/web && npx eslint src/components/MuseumVisitorInquiryForm.tsx && npx tsc --noEmit)
```

Тесты используют одноразовые временные ключи, фиктивные адреса и временную SQLite; не создают реальных заявок. Для полной приёмки после инфраструктуры нужны: mTLS refusal / invalid CA / network deny to CMS, TLS 1.2+, миграции боевой СУБД, перезапуск под нагрузкой, резервная копия/восстановление, журнал без ПДн, consent/a11y, физический фаервол и UAT.
