# ADR: приём обращений на двух виртуальных машинах

Дата: 29.10.2026. Статус: **код и шаблоны подготовлены; на серверах музея НЕ активировано**. Это решение заменяет трёхсерверную схему приёма из ADR_20261029_PUBLIC_INTERACTIONS_WITH_STATIC_EXPORT.md.

## Распределение функций

**ВМ №2 (публичная):** Nginx раздаёт статический Next.js export; на ней **нет** PHP, Node runtime, CMS, базы, ключей и очереди. В рамках предусмотренной ТЗ функции **Nginx как reverse proxy** (п. 2.2.3.7.1), после подтверждения соответствия конкретной схемы на стадии архитектуры и приёмки Nginx выполняет точечное проксирование **HTTPS POST /v1/requests** через mTLS на приватный адрес ВМ №1. Все остальные пути и методы остаются статическими или получают отказ. Доступ к CMS/БД с публичной ВМ запрещён.

**ВМ №1 (закрытая):** Laravel/MoonShine/БД/Next.js build остаются закрытыми. Отдельный PHP-FPM instance под выделенным Unix-пользователем musbread-ingress принимает POST в 9443 через Nginx (private NIC + firewall allowlist ВМ №2 + обязательный mTLS). Он имеет только **публичный ключ** sodium и SQLite с шифрованными сообщениями вне webroot; PHP-FPM с PrivateNetwork=true, AF_UNIX, ProtectSystem=strict и отказом в доступе к файлам CMS и Unix-сокетам СУБД. Laravel каждые 60 секунд забирает сообщения с **127.0.0.1:8443** по mTLS и Bearer-токену, расшифровывает внутри закрытой зоны, сохраняет и ACK после commit. На listener 9443 нет /internal/pull или /internal/ack. Клиент получает 202 только после записи в очередь; это не подтверждение брони.

Браузер → musbread.ru/v1/requests → VM2 Nginx exact-route mTLS → VM1 isolated PHP-FPM encrypted SQLite → VM1 Laravel loopback mTLS pull → private MoonShine Inbox.

## Критичная граница договора

**В оригинале ТЗ обратное проксирование прямо названо среди функций Nginx (п. 2.2.3.7.1, строка 264).** Ограничение п. 2.2.3.4 (строки 149–158) относится к размещению содержимого публичного сервера, read-only, изоляции CMS/БД и приватной передаче. Поэтому проксирование единственного POST **может соответствовать ТЗ**, если оно исключительно пересылает данные, не сохраняет их на публичной ВМ и не предоставляет доступ к CMS/БД. Это НЕ запрос на исключение из ТЗ. Вместе с тем п. 2.2.3.1 (строка 136) требует, чтобы все операции обработки и управления выполнялись из защищённого бэкенда, а п. 2.2.3.4 (строка 151) ограничивает доступ сотрудников к CMS доверенными IP. Следовательно, реальное соответствие зависит от проверенного разделения служебного канала приёма и доступа к админпанели, а также согласованного процесса обработки обращений редактором. **Без подтверждения этой границы в рамках предусмотренных ТЗ стадий и без испытаний считать соответствие доказанным нельзя.**

Режим остаётся выключен до согласования технической схемы/регламента ПДн и целевого UAT. Если фактическое сетевое разграничение не позволяет выполнить требования, нужно пересмотреть приём данных без ослабления CMS/firewall, сохранив две ВМ. Mailto — лишь временная функциональность, **не полноценное закрытие обязательных форм**.

## Конфигурационные артефакты

- infra/nginx/two-vm-public-requests.http.conf — rate limit на исходные IP, внутри http{} публичной ВМ.
- infra/nginx/two-vm-public-requests.location.conf — **только** в HTTPS server{} musbread.ru на публичной ВМ после разрешения музея.
- infra/nginx/two-vm-private-ingress.conf — private 9443 (только ВМ2/mTLS), loopback 8443 (только Laravel/mTLS).
- infra/php-fpm/two-vm-request-ingress-*.conf и infra/systemd/musbread-request-ingress-fpm.service — отдельный изолированный PHP-FPM на ВМ1, не в CMS pool. При установке master-конфиг разместить как /etc/musbread/ingress-php-fpm.conf, pool как /etc/musbread/two-vm-request-ingress-pool.conf; PHP-FPM должен работать только после проверки версии PHP, прав каталогов и сокета.
- services/request-ingress/public/index.php — sealed-box + durable SQLite; MUSEUM_TRUSTED_PROXY=1 требует FastCGI-параметр MUSEUM_CLIENT_IP, HTTP-заголовки не доверяются.
- apps/cms/app/Console/Commands/PullMuseumInboundRequests.php — import-once с ACK после DB commit; apps/web/src/components/MuseumVisitorInquiryForm.tsx — disabled до UAT.

**Старый infra/nginx/request-ingress.conf для третьего хоста применять к двум ВМ нельзя.** IP 10.20.30.10 (ВМ1), 10.20.30.20 (ВМ2), TLS-пути и имена сертификатов — исключительно примеры. Установку возможного PHP2Shell-уязвимого PHP запретить существующим check_php_runtime.py.

## Эксплуатация после согласования

На отдельном FPM ВМ1: MUSEUM_INGRESS_DB=/var/lib/musbread-requests/queue.sqlite, MUSEUM_TRUSTED_PROXY=1, MUSEUM_INGRESS_PUBLIC_KEY, MUSEUM_RATE_SECRET, MUSEUM_INTERNAL_TOKEN, MUSEUM_ALLOWED_ORIGIN=https://musbread.ru, MUSEUM_CONSENT_VERSION. Unix-каталог 0700, SQLite 0600; для сокета отдельная группа musbread-ingress-socket; создать группу, включить в неё системного пользователя Nginx (обычно www-data), перезапустить Nginx после изменения групп. Не включать обработчик в группу www-data: она может давать доступ к файлам CMS; env-файл/закрытые ключи не передавать в Git. На Laravel: MUSEUM_REQUEST_IMPORT_ENABLED=true только после UAT, URL https://ingress-internal.example.invalid:8443 с локальным 127.0.0.1 resolution, проверка SAN/CA, собственный mTLS клиентский сертификат и sodium **закрытый** ключ. На Next.js: NEXT_PUBLIC_MUSEUM_REQUESTS_ENDPOINT=https://musbread.ru/v1/requests, enabled=1 только после UAT; CSP connect-src self.

Физическая сеть: внешние подключения только к публичной 80/443; VM2→VM1 **только 9443** (плюс независимый отдельно согласованный канал доставки релизов); запрещены VM2→CMS, DB, 8443, SSH. 8443 только localhost на VM1. Nginx VM2 перезаписывает X-Museum-Client-IP значением remote_addr, Nginx VM1 передаёт его PHP только через FastCGI; PHP без проверенного IP отказывает, чтобы все посетители не попадали под лимит одного прокси IP. Cookies/Authorization в proxy не пересылаются. Логи POST отключены.

Синтаксическая проверка шаблонов (без реальных секретов/сети): bash scripts/test_two_vm_nginx_syntax.sh и bash scripts/test_two_vm_php_fpm_syntax.sh. Это не запуск приёмщика на серверах музея.

## Приёмка — НЕ проведена на площадке заказчика

- Подтвердить при согласовании стадии техническую схему Nginx reverse proxy и недоступность CMS с публичной ВМ; утвердить операторов/ПДн, поля, срок хранения, порядок удаления, backup и права доступа.
- Проверить конфиги Nginx, firewall, mTLS (invalid/expired client cert/CA/SAN), отрицательный доступ к CMS/SQL/8443/SSH с VM2 и извне.
- Синтетические 202/422/409/413/429/503, честное сообщение об ошибке, независимые IP, потеря ACK, повторный import, отсутствие открытого текста в очереди.
- Проверить backup/restore SQLite **через SQLite API** вместе с DB и ключами закрытой зоны, retention/удаление, наблюдаемость без ПДн, аварийное выключение и rollback на mailto.
- UAT сотрудников, тесты доступности, письменное согласование; лишь после — включать режим и менять статусы ТЗ.

Светофор 85/118/122 не повышен. Production NO-GO.

**Проверка записи ПДн:** на публичном Nginx для POST заданы `client_max_body_size 8k`, `client_body_buffer_size 16k`, `proxy_request_buffering off`, `proxy_buffering off` и `access_log off`. Поэтому тело небольшого запроса не должно попадать в клиентские временные файлы Nginx; отдельно проверить реальную конфигурацию, логи и сбойный путь при тестах на Linux. Любое попадание ПДн на диск ВМ2 — стоп-гейт.
