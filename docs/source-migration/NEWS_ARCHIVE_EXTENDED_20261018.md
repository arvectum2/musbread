# Полный перенос опубликованного музеем новостного архива · 18.10.2026

**Источники: `https://muzei-xleb.ru/novosty` и 27 реально существующих страниц `/novosty?page=1`–`?page=27`, загруженные напрямую на Mac mini через ArvectumSSD.** Проверено 28 индексов (0–27), 280 **уникальных** URL публикаций. На самой старой странице зафиксирована новость 01.09.2019, на последнем индексе нет перехода к ещё более ранней странице.

**Подлинное содержимое перенесено:** 10 последних + **270 архивных** новостей (2019–2026), оригинальные даты/заголовки/HTML, источник каждой новости и SHA-256; [перечень 27 исходных HTML-индексов и SHA-256](ALL_MUSEUM_NEWS_INDEX_PAGINATION_VERIFIED_20261018.md), [CSV всех URL](ALL_HISTORICAL_MUSEUM_NEWS_URLS_20261018.csv). Корпус архивных статей хранится в `apps/web/src/data/official-museum-news-archive.json` и неизменённых приватных оригинальных записях `.local_archive/news-archive-verified-articles`.

**Из них 56 настоящих музейных объявлений не имеют отдельного текста**, содержат только исходный плакат; их изображения без OCR/заменителей входят в [локальную фотобиблиотеку](MUSEUM_PHOTO_DOMAIN_CUTOVER_20261018.md). Нельзя представлять старые объявления 2019–2026 годов как будущие события, новые правила посещения или действующие предложения.

Каждая новость существует как самостоятельная страница `/news/museum-news-…/`. Старые адреса `/novosty/YYYY-MM-DD/slug` присутствуют в [статическом реестре ссылок](LEGACY_MUSEUM_PAGE_CUTOVER_20261018.md); **это пока браузерные переходники, не SEO-равноценная замена старым каноническим URL**. Стоп-гейт [CP-SEO-01](../SEO_MIGRATION_NO_REGRESSION_20261018.md) проверяется после закрытия пробелов переноса; DNS не менялся.

В источниках найден **один исторический PDF**, приказ №94 от 27.10.2021 по старым правилам посещения. Истинный URL `http://muzei-xleb.ru/sites/default/files/page/202110271242-prikaz_no94.pdf` перенаправляет на HTTPS, но файл **уже возвращает HTTP 404 на действующем музее**. Не выдумывать замену; фиксировать как дефект исходного сайта и вопрос заказчику, не выдавать за доступный документ. Действующие 57 проверенных PDF/DOCX уже сохранены побайтово и встроены в локальную статическую сборку.

## Реальные годы архивных публикаций

| Год | Подлинных архивных новостей |
|---|---:|
| 2026 | 51 |
| 2025 | 28 |
| 2024 | 32 |
| 2023 | 34 |
| 2022 | 44 |
| 2021 | 42 |
| 2020 | 29 |
| 2019 | 10 |

## Исходные архивные индексы

| URL | Новостей |
|---|---:|
| [https://muzei-xleb.ru/novosty?page=1](https://muzei-xleb.ru/novosty?page=1) | 10 |
| [https://muzei-xleb.ru/novosty?page=2](https://muzei-xleb.ru/novosty?page=2) | 10 |
| [https://muzei-xleb.ru/novosty?page=3](https://muzei-xleb.ru/novosty?page=3) | 10 |
| [https://muzei-xleb.ru/novosty?page=4](https://muzei-xleb.ru/novosty?page=4) | 10 |
| [https://muzei-xleb.ru/novosty?page=5](https://muzei-xleb.ru/novosty?page=5) | 10 |
| [https://muzei-xleb.ru/novosty?page=6](https://muzei-xleb.ru/novosty?page=6) | 10 |
| [https://muzei-xleb.ru/novosty?page=7](https://muzei-xleb.ru/novosty?page=7) | 10 |
| [https://muzei-xleb.ru/novosty?page=8](https://muzei-xleb.ru/novosty?page=8) | 10 |
| [https://muzei-xleb.ru/novosty?page=9](https://muzei-xleb.ru/novosty?page=9) | 10 |
| [https://muzei-xleb.ru/novosty?page=10](https://muzei-xleb.ru/novosty?page=10) | 10 |
| [https://muzei-xleb.ru/novosty?page=11](https://muzei-xleb.ru/novosty?page=11) | 10 |
| [https://muzei-xleb.ru/novosty?page=12](https://muzei-xleb.ru/novosty?page=12) | 10 |
| [https://muzei-xleb.ru/novosty?page=13](https://muzei-xleb.ru/novosty?page=13) | 10 |
| [https://muzei-xleb.ru/novosty?page=14](https://muzei-xleb.ru/novosty?page=14) | 10 |
| [https://muzei-xleb.ru/novosty?page=15](https://muzei-xleb.ru/novosty?page=15) | 10 |
| [https://muzei-xleb.ru/novosty?page=16](https://muzei-xleb.ru/novosty?page=16) | 10 |
| [https://muzei-xleb.ru/novosty?page=17](https://muzei-xleb.ru/novosty?page=17) | 10 |
| [https://muzei-xleb.ru/novosty?page=18](https://muzei-xleb.ru/novosty?page=18) | 10 |
| [https://muzei-xleb.ru/novosty?page=19](https://muzei-xleb.ru/novosty?page=19) | 10 |
| [https://muzei-xleb.ru/novosty?page=20](https://muzei-xleb.ru/novosty?page=20) | 10 |
| [https://muzei-xleb.ru/novosty?page=21](https://muzei-xleb.ru/novosty?page=21) | 10 |
| [https://muzei-xleb.ru/novosty?page=22](https://muzei-xleb.ru/novosty?page=22) | 10 |
| [https://muzei-xleb.ru/novosty?page=23](https://muzei-xleb.ru/novosty?page=23) | 10 |
| [https://muzei-xleb.ru/novosty?page=24](https://muzei-xleb.ru/novosty?page=24) | 10 |
| [https://muzei-xleb.ru/novosty?page=25](https://muzei-xleb.ru/novosty?page=25) | 10 |
| [https://muzei-xleb.ru/novosty?page=26](https://muzei-xleb.ru/novosty?page=26) | 10 |
| [https://muzei-xleb.ru/novosty?page=27](https://muzei-xleb.ru/novosty?page=27) | 10 |

## Оригинальные даты и заголовки

| Опубликовано | Подлинный заголовок | Содержимое | URL музея |
|---|---|---|---|
| 2026-08-31 | События в музее с 31 августа по 7 сентября | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-08-31/sobytiya-v-muzee-s-31-avgusta-po-7-sentyabrya) |
| 2026-08-24 | События в музее с 24 по 31 августа | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-08-24/sobytiya-v-muzee-s-24-po-31-avgusta) |
| 2026-08-17 | События в музее с 17 по 24 августа | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-08-17/sobytiya-v-muzee-s-17-po-24-avgusta) |
| 2026-08-10 | События в музее с 10 по 17 августа | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-08-10/sobytiya-v-muzee-s-10-po-17-avgusta) |
| 2026-08-03 | События в музее с 3 по 10 августа | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-08-03/sobytiya-v-muzee-s-3-po-10-avgusta) |
| 2026-07-27 | События в музее с 27 июля по 3 августа | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-07-27/sobytiya-v-muzee-s-27-iyulya-po-3-avgusta) |
| 2026-07-17 | События в музее с 20 июля по 26 июля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-07-17/sobytiya-v-muzee-s-20-iyulya-po-26-iyulya) |
| 2026-07-13 | События в музее с 13 июля по 20 июля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-07-13/sobytiya-v-muzee-s-13-iyulya-po-20-iyulya) |
| 2026-07-07 | События в музее с 06 июля по 12 июля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-07-07/sobytiya-v-muzee-s-06-iyulya-po-12-iyulya) |
| 2026-06-28 | События в музее с 29 июня по 05 июля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-06-28/sobytiya-v-muzee-s-29-iyunya-po-05-iyulya) |
| 2026-06-22 | События в музее с 22 по 28 июня | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-06-22/sobytiya-v-muzee-s-22-po-28-iyunya) |
| 2026-06-16 | События в музее с 15 по 21 июня | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-06-16/sobytiya-v-muzee-s-15-po-21-iyunya) |
| 2026-06-08 | События в музее с 10 по 15 июня | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-06-08/sobytiya-v-muzee-s-10-po-15-iyunya) |
| 2026-06-02 | События в музее с 03 по 08 июня | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-06-02/sobytiya-v-muzee-s-03-po-08-iyunya) |
| 2026-05-26 | События в музее с 27 мая по 01 июня | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-05-26/sobytiya-v-muzee-s-27-maya-po-01-iyunya) |
| 2026-05-18 | События на неделе с 20 по 24 мая | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-05-18/sobytiya-na-nedele-s-20-po-24-maya) |
| 2026-05-15 | ДОРОГИЕ ДРУЗЬЯ! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-05-15/dorogie-druzya) |
| 2026-05-14 | Выставка «Я без пропитания оставаться не могу...» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-05-14/vystavka-ya-bez-propitaniya-ostavatsya-ne-mogu) |
| 2026-05-13 | Совсем скоро "Ночь музеев"! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-05-13/sovsem-skoro-noch-muzeev) |
| 2026-05-13 | Фестиваль «Петербург. Пространство Булгакова» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-05-13/festival-peterburg-prostranstvo-bulgakova) |
| 2026-05-12 | События на неделе с 13 по 17 мая | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-05-12/sobytiya-na-nedele-s-13-po-17-maya) |
| 2026-05-08 | РЕЖИМ РАБОТЫ МУЗЕЯ В ПРАЗДНИКИ! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2026-05-08/rezhim-raboty-muzeya-v-prazdniki) |
| 2026-05-06 | В Музее Хлеба открылась выставка «Мимолетности. Зима и снова лето» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-05-06/v-muzee-hleba-otkrylas-vystavka-mimoletnosti-zima-i-snova-leto) |
| 2026-05-05 | События на неделе с 6 по 10 мая | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-05-05/sobytiya-na-nedele-s-6-po-10-maya) |
| 2026-04-29 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2026-04-29/rezhim-raboty-muzeya) |
| 2026-04-27 | События на неделе с 29 апреля по 3 мая | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-04-27/sobytiya-na-nedele-s-29-aprelya-po-3-maya) |
| 2026-04-20 | События на неделе с 22 по 26 апреля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-04-20/sobytiya-na-nedele-s-22-po-26-aprelya) |
| 2026-04-13 | События на неделе с 15 по 19 апреля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-04-13/sobytiya-na-nedele-s-15-po-19-aprelya) |
| 2026-04-08 | Выставка «Дом на трёх улицах» в Центральном государственном архиве | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-04-08/vystavka-dom-na-tryoh-ulicah-v-centralnom-gosudarstvennom-arhive) |
| 2026-04-07 | События на неделе с 08 по 12 апреля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-04-07/sobytiya-na-nedele-s-08-po-12-aprelya) |
| 2026-03-31 | События на неделе с 01 по 05 апреля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-31/sobytiya-na-nedele-s-01-po-05-aprelya) |
| 2026-03-27 | Мастер-класс студии «Лоскутные забавы» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-27/master-klass-studii-loskutnye-zabavy) |
| 2026-03-26 | Фестиваль «Детские дни» в нашем музее: весенние каникулы с пользой и радостью! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-26/festival-detskie-dni-v-nashem-muzee-vesennie-kanikuly-s-polzoy-i-radostyu) |
| 2026-03-20 | С 21 марта по 5 апреля 2026 года в России проходит всероссийская акция «Приведи родителей в музей» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-20/s-21-marta-po-5-aprelya-2026-goda-v-rossii-prohodit-vserossiyskaya-akciya-privedi) |
| 2026-03-18 | Выставка «Жили-были...» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-18/vystavka-zhili-byli) |
| 2026-03-17 | События на неделе с 18 по 22 марта | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-17/sobytiya-na-nedele-s-18-po-22-marta) |
| 2026-03-16 | Выставка «Жили-были...» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-16/vystavka-zhili-byli) |
| 2026-03-10 | События на неделе с 11 по 15 марта | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-10/sobytiya-na-nedele-s-11-po-15-marta) |
| 2026-03-06 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2026-03-06/rezhim-raboty-muzeya) |
| 2026-03-05 | В Музее Хлеба открылась выставка «Искусство шить красиво» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-05/v-muzee-hleba-otkrylas-vystavka-iskusstvo-shit-krasivo) |
| 2026-03-02 | События на неделе с 4 по 7 марта | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-03-02/sobytiya-na-nedele-s-4-po-7-marta) |
| 2026-02-24 | События на неделе с 25 февраля по 1 марта | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-02-24/sobytiya-na-nedele-s-25-fevralya-po-1-marta) |
| 2026-02-19 | Режим работы музея | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-02-19/rezhim-raboty-muzeya) |
| 2026-02-17 | В Музее истории Обуховского завода открылась выставка «Широкая масленица» с участием Музея Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-02-17/v-muzee-istorii-obuhovskogo-zavoda-otkrylas-vystavka-shirokaya-maslenica-s) |
| 2026-02-16 | События на неделе с 18 по 22 февраля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-02-16/sobytiya-na-nedele-s-18-po-22-fevralya) |
| 2026-02-11 | События на неделе с 11 по 15 февраля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-02-11/sobytiya-na-nedele-s-11-po-15-fevralya) |
| 2026-02-11 | Китайский Новый год в Музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-02-11/kitayskiy-novyy-god-v-muzee-hleba) |
| 2026-01-30 | Цифровая память: комментарий Музея Хлеба для издания «Коммерсантъ» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-01-30/cifrovaya-pamyat-kommentariy-muzeya-hleba-dlya-izdaniya-kommersant) |
| 2026-01-29 | Музей Хлеба в репортаже Первого канала в честь Дня освобождения Ленинграда от фашистской блокады | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-01-29/muzey-hleba-v-reportazhe-pervogo-kanala-v-chest-dnya-osvobozhdeniya-leningrada-ot) |
| 2026-01-23 | 28 января (в среду) санитарный день в музее отменяется | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-01-23/28-yanvarya-v-sredu-sanitarnyy-den-v-muzee-otmenyaetsya) |
| 2026-01-21 | В Музее хлеба открывается выставка «Растревоженная память» ко Дню Ленинградской Победы | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2026-01-21/v-muzee-hleba-otkryvaetsya-vystavka-rastrevozhennaya-pamyat-ko-dnyu-leningradskoy) |
| 2025-12-30 | График работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2025-12-30/grafik-raboty-muzeya) |
| 2025-12-26 | Музей в радиоэфире | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-12-26/muzey-v-radioefire) |
| 2025-12-23 | События на неделе с 24 по 28 декабря | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-12-23/sobytiya-na-nedele-s-24-po-28-dekabrya) |
| 2025-12-18 | Выставка «Солнце на сковородке» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-12-18/vystavka-solnce-na-skovorodke) |
| 2025-12-16 | Открытие выставки | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-12-16/otkrytie-vystavki) |
| 2025-12-15 | Дорогие друзья! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-12-15/dorogie-druzya) |
| 2025-12-15 | Друзья! В нашем музее полным ходом идёт монтаж выставки "Солнце на сковородке" | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-12-15/druzya-v-nashem-muzee-polnym-hodom-idyot-montazh-vystavki-solnce-na-skovorodke) |
| 2025-12-12 | В Санкт-Петербургском музее Хлеба с 10 декабря 2025 г. открыта выставка «С НОВЫМ ГОДОМ!» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-12-12/v-sankt-peterburgskom-muzee-hleba-s-10-dekabrya-2025-g-otkryta-vystavka-s-novym) |
| 2025-12-10 | Режим работы музея в праздничные дни | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2025-12-10/rezhim-raboty-muzeya-v-prazdnichnye-dni) |
| 2025-12-09 | «WWW.КУЛЬТУРА.РФ – твой гид по культуре | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-12-09/wwwkulturarf-tvoy-gid-po-kulture) |
| 2025-12-04 | Режим работы | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2025-12-04/rezhim-raboty) |
| 2025-12-04 | Коллекция музейных предметов | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-12-04/kollekciya-muzeynyh-predmetov) |
| 2025-11-27 | Друзья! Наш музей теперь в МАХ! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-11-27/druzya-nash-muzey-teper-v-mah) |
| 2025-11-25 | Виртуальная выставка «Супница: история в каждой ложке» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-11-25/virtualnaya-vystavka-supnica-istoriya-v-kazhdoy-lozhke) |
| 2025-11-14 | Выставка «Бастион культуры» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-11-14/vystavka-bastion-kultury) |
| 2025-10-31 | Выставка «Выставка о выставке» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-10-31/vystavka-vystavka-o-vystavke) |
| 2025-10-31 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2025-10-31/rezhim-raboty-muzeya) |
| 2025-10-27 | «Детские Дни» в музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-10-27/detskie-dni-v-muzee-hleba) |
| 2025-10-24 | Выставка «Слава хлебу на столе!» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-10-24/vystavka-slava-hlebu-na-stole) |
| 2025-09-22 | Выставка «В сердце Азии» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-09-22/vystavka-v-serdce-azii) |
| 2025-09-22 | «Форум малых музеев» в музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-09-22/forum-malyh-muzeev-v-muzee-hleba) |
| 2025-09-22 | Выставка «Дом на трёх улицах» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-09-22/vystavka-dom-na-tryoh-ulicah) |
| 2025-06-16 | Вы ставка «Птичий базар» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-06-16/vy-stavka-ptichiy-bazar) |
| 2025-06-05 | Выставка «Мы в этом городе живём» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-06-05/vystavka-my-v-etom-gorode-zhivyom) |
| 2025-05-16 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2025-05-16/rezhim-raboty-muzeya) |
| 2025-05-05 | Выставка «О, спорт, ты — мир!» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-05-05/vystavka-o-sport-ty-mir) |
| 2025-04-29 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2025-04-29/rezhim-raboty-muzeya) |
| 2025-01-30 | Выставка «Ваше здоровье!» (Тема алкоголя в коллекции Санкт-Петербургского музея Хлеба) | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2025-01-30/vystavka-vashe-zdorove-tema-alkogolya-v-kollekcii-sankt-peterburgskogo-muzeya) |
| 2024-12-27 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2024-12-27/rezhim-raboty-muzeya) |
| 2024-12-26 | Оцените нашу организацию | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2024-12-26/ocenite-nashu-organizaciyu) |
| 2024-12-24 | Перенос санитарного дня в декабре | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-12-24/perenos-sanitarnogo-dnya-v-dekabre) |
| 2024-12-23 | Выставка «Где спрятался подарок?» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-12-23/vystavka-gde-spryatalsya-podarok) |
| 2024-12-11 | Выставка «Съ Рождествомъ!» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-12-11/vystavka-s-rozhdestvom) |
| 2024-11-22 | Выставка «А завтра был мир» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-11-22/vystavka-zavtra-byl-mir) |
| 2024-10-31 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2024-10-31/rezhim-raboty-muzeya) |
| 2024-10-25 | Санкт-Петербургский музей Хлеба приглашает в музей на экскурсионную программу в рамках фестиваля «Детские дни в Петербурге» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-10-25/sankt-peterburgskiy-muzey-hleba-priglashaet-v-muzey-na-ekskursionnuyu-programmu-v) |
| 2024-10-23 | Виртуальная выставка «Одёжка для конфеты» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-10-23/virtualnaya-vystavka-odyozhka-dlya-konfety) |
| 2024-10-02 | Приглашаем на Форум малых музеев! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-10-02/priglashaem-na-forum-malyh-muzeev) |
| 2024-10-02 | Выставка "Короли кондитерского дела. «Товарищество А.И.Абрикосова Сыновей» (к 200-летию А.И.Абрикосова)" | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-10-02/vystavka-koroli-konditerskogo-dela-tovarishchestvo-aiabrikosova-synovey-k-200) |
| 2024-10-02 | Виртуальная выставка «Подношение гостям» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-10-02/virtualnaya-vystavka-podnoshenie-gostyam) |
| 2024-09-24 | 28 сентября 2024 года Санкт-Петербургский музей Хлеба приглашает на праздник закрытия выставки «Марийские традиции» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-09-24/28-sentyabrya-2024-goda-sankt-peterburgskiy-muzey-hleba-priglashaet-na-prazdnik) |
| 2024-08-30 | Выставка «Марийские традиции» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-08-30/vystavka-mariyskie-tradicii) |
| 2024-07-23 | Виртуальная выставка «Хранительница тайн» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-07-23/virtualnaya-vystavka-hranitelnica-tayn) |
| 2024-07-02 | Выставка «целый мир в маленькой чашке» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-07-02/vystavka-celyy-mir-v-malenkoy-chashke) |
| 2024-06-13 | Выставка временно закрыта | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-06-13/vystavka-vremenno-zakryta) |
| 2024-06-10 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2024-06-10/rezhim-raboty-muzeya) |
| 2024-05-27 | Выставка «Город над вольной Невой...» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-05-27/vystavka-gorod-nad-volnoy-nevoy) |
| 2024-05-16 | Внимание! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-05-16/vnimanie) |
| 2024-05-15 | Режим работы в «Ночь музеев» | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2024-05-15/rezhim-raboty-v-noch-muzeev) |
| 2024-05-06 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2024-05-06/rezhim-raboty-muzeya) |
| 2024-04-25 | Внимание! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-04-25/vnimanie) |
| 2024-04-25 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2024-04-25/rezhim-raboty-muzeya) |
| 2024-04-19 | Выставка «История хлебопекарной промышленности Санкт-Петербурга» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-04-19/vystavka-istoriya-hlebopekarnoy-promyshlennosti-sankt-peterburga) |
| 2024-03-06 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2024-03-06/rezhim-raboty-muzeya) |
| 2024-03-01 | Выставка «Из чего только сделаны барышни...» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-03-01/vystavka-iz-chego-tolko-sdelany-baryshni) |
| 2024-02-19 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2024-02-19/rezhim-raboty-muzeya) |
| 2024-02-07 | Выставка недоступна для осмотра | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-02-07/vystavka-nedostupna-dlya-osmotra) |
| 2024-02-07 | Приглашаем на трансляцию семинара | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-02-07/priglashaem-na-translyaciyu-seminara) |
| 2024-01-26 | Выставка «Начало Дороги Жизни — восточный берег Ладоги» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-01-26/vystavka-nachalo-dorogi-zhizni-vostochnyy-bereg-ladogi) |
| 2024-01-11 | Музейный форум «Дневные звёзды» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2024-01-11/muzeynyy-forum-dnevnye-zvyozdy) |
| 2023-12-27 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2023-12-27/rezhim-raboty-muzeya) |
| 2023-12-25 | Выставка «Жизнь, деленная на граммы» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-12-25/vystavka-zhizn-delennaya-na-grammy) |
| 2023-12-21 | Приглашаем в музей! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-12-21/priglashaem-v-muzey) |
| 2023-12-21 | Выставка «И я там был...» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-12-21/vystavka-i-ya-tam-byl) |
| 2023-11-21 | Выставки временно недоступны | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-11-21/vystavki-vremenno-nedostupny) |
| 2023-11-10 | Приглашаем в музей! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-11-10/priglashaem-v-muzey) |
| 2023-11-08 | Культурный форум в музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-11-08/kulturnyy-forum-v-muzee-hleba) |
| 2023-11-01 | Режим работы музея | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-11-01/rezhim-raboty-muzeya) |
| 2023-10-27 | Выставка «Меры и размеры» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-10-27/vystavka-mery-i-razmery) |
| 2023-10-26 | Приглашаем в музей! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-10-26/priglashaem-v-muzey) |
| 2023-10-26 | Фестиваль «Детские Дни» в музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-10-26/festival-detskie-dni-v-muzee-hleba) |
| 2023-10-26 | Выставка «Он был большой лакомка» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-10-26/vystavka-byl-bolshoy-lakomka) |
| 2023-10-13 | Приглашаем на экскурсию! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-10-13/priglashaem-na-ekskursiyu) |
| 2023-10-11 | Выставка «Хлеб многонационального Петербурга» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-10-11/vystavka-hleb-mnogonacionalnogo-peterburga) |
| 2023-09-22 | Выставка «Баттл: рожь vs пшеница» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-09-22/vystavka-battl-rozh-vs-pshenica) |
| 2023-08-29 | Выставка «О хлебе и цветах» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-08-29/vystavka-o-hlebe-i-cvetah) |
| 2023-08-11 | Выставка «В банке, в вазочке, в розетке...» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-08-11/vystavka-v-banke-v-vazochke-v-rozetke) |
| 2023-07-10 | Виртуальная выставка «Пища богов» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-07-10/virtualnaya-vystavka-pishcha-bogov) |
| 2023-07-07 | Выставка «От чак-чака до эчпочмака» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-07-07/vystavka-ot-chak-chaka-do-echpochmaka) |
| 2023-06-19 | Внимание! Мошенники! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-06-19/vnimanie-moshenniki) |
| 2023-05-25 | Виртуальная выставка «Город, знакомый до слёз» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-05-25/virtualnaya-vystavka-gorod-znakomyy-do-slyoz) |
| 2023-05-23 | В музее с 24 мая 2023 года по 02 июля 2023 года работает выставка «Шерстяной Петербург» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-05-23/v-muzee-s-24-maya-2023-goda-po-02-iyulya-2023-goda-rabotaet-vystavka-sherstyanoy) |
| 2023-05-18 | Режим работы музея 20 и 21 мая | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2023-05-18/rezhim-raboty-muzeya-20-i-21-maya) |
| 2023-05-12 | Выставка «В краю драников» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-05-12/vystavka-v-krayu-dranikov) |
| 2023-05-04 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2023-05-04/rezhim-raboty-muzeya) |
| 2023-04-27 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2023-04-27/rezhim-raboty-muzeya) |
| 2023-04-17 | Выставка «Хлеб в русских традициях» в Пикалево | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-04-17/vystavka-hleb-v-russkih-tradiciyah-v-pikalevo) |
| 2023-04-14 | Выставка «Пасха в Петербурге: поздравления и подарки» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-04-14/vystavka-pasha-v-peterburge-pozdravleniya-i-podarki) |
| 2023-03-24 | «Детские Дни» в музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-03-24/detskie-dni-v-muzee-hleba) |
| 2023-03-02 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2023-03-02/rezhim-raboty-muzeya) |
| 2023-03-02 | Выставка ко Дню кошек | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-03-02/vystavka-ko-dnyu-koshek) |
| 2023-02-20 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2023-02-20/rezhim-raboty-muzeya) |
| 2023-01-19 | Выставка «Искра жизни» в музее Горэлектротранспорта | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-01-19/vystavka-iskra-zhizni-v-muzee-gorelektrotransporta) |
| 2023-01-13 | Выставка «В великой битве прорвана блокада» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2023-01-13/vystavka-v-velikoy-bitve-prorvana-blokada) |
| 2022-12-29 | Музей приглашает в январе | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-12-29/muzey-priglashaet-v-yanvare) |
| 2022-12-26 | Новый номер телефона | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-12-26/novyy-nomer-telefona) |
| 2022-12-26 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-12-26/rezhim-raboty-muzeya) |
| 2022-12-23 | Временно не работает телефон! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-12-23/vremenno-ne-rabotaet-telefon) |
| 2022-12-21 | Приглашаем на концерт | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-12-21/priglashaem-na-koncert) |
| 2022-11-28 | Трансляция экскурсии | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-11-28/translyaciya-ekskursii) |
| 2022-11-08 | Экскурсии «Имя вещи» на выставке «Честная реклама» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-11-08/ekskursii-imya-veshchi-na-vystavke-chestnaya-reklama) |
| 2022-11-03 | Временное закрытие выставки | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-11-03/vremennoe-zakrytie-vystavki) |
| 2022-11-01 | Режим работы музея в праздничные дни | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-11-01/rezhim-raboty-muzeya-v-prazdnichnye-dni) |
| 2022-10-28 | Выставка «К истории хлебопечения в Петербурге — Петрограде — Ленинграде» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-10-28/vystavka-k-istorii-hlebopecheniya-v-peterburge-petrograde-leningrade) |
| 2022-10-25 | Фестиваль «Детские дни» в музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-10-25/festival-detskie-dni-v-muzee-hleba) |
| 2022-10-21 | Выставка «Честная реклама» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-10-21/vystavka-chestnaya-reklama) |
| 2022-10-18 | Изменения в графике работы музея | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-10-18/izmeneniya-v-grafike-raboty-muzeya) |
| 2022-10-13 | Трансляция экскурсии 13 октября | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-10-13/translyaciya-ekskursii-13-oktyabrya) |
| 2022-10-12 | Выставка «У нас на Севере» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-10-12/vystavka-u-nas-na-severe) |
| 2022-10-04 | Лекция «О Кавказе со вкусом» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-10-04/lekciya-o-kavkaze-so-vkusom) |
| 2022-09-15 | Выставка «Журнал Печорина. Кавказ» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-09-15/vystavka-zhurnal-pechorina-kavkaz) |
| 2022-09-15 | Выставка «Пища наша» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-09-15/vystavka-pishcha-nasha) |
| 2022-09-02 | 4 сентября закрыты два зала экспозиции | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-09-02/4-sentyabrya-zakryty-dva-zala-ekspozicii) |
| 2022-08-12 | Выставка продолжает работу | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-08-12/vystavka-prodolzhaet-rabotu) |
| 2022-08-10 | Уважаемые посетители! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-08-10/uvazhaemye-posetiteli) |
| 2022-07-07 | Выставка «Наедине с Петром» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-07-07/vystavka-naedine-s-petrom) |
| 2022-07-04 | Выставка «Азиатские мотивы» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-07-04/vystavka-aziatskie-motivy) |
| 2022-07-01 | Уважаемые посетители! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-07-01/uvazhaemye-posetiteli) |
| 2022-06-08 | 12 июня музей закрыт! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-06-08/12-iyunya-muzey-zakryt) |
| 2022-05-27 | Выставка «На троне вечный был работник...» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-05-27/vystavka-na-trone-vechnyy-byl-rabotnik) |
| 2022-05-26 | Выставка «Координаты чудес. Миры Игоря и Анны Игнатьевых» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-05-26/vystavka-koordinaty-chudes-miry-igorya-i-anny-ignatevyh) |
| 2022-05-17 | Режим работы в «Ночь музеев» | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-05-17/rezhim-raboty-v-noch-muzeev) |
| 2022-05-04 | Режим работы музея в праздничные дни мая | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-05-04/rezhim-raboty-muzeya-v-prazdnichnye-dni-maya) |
| 2022-04-26 | ГИС ЖКХ | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-04-26/gis-zhkh) |
| 2022-04-18 | Выставка «Пасхальные традиции» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-04-18/vystavka-pashalnye-tradicii) |
| 2022-04-08 | Изменение режима работы музея | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-04-08/izmenenie-rezhima-raboty-muzeya) |
| 2022-04-05 | 12 апреля музей закрыт | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-04-05/12-aprelya-muzey-zakryt) |
| 2022-04-04 | Семинар «Научное наследие историка хлебопечения С.В. Коновцева» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-04-04/seminar-nauchnoe-nasledie-istorika-hlebopecheniya-sv-konovceva) |
| 2022-03-25 | Отмена санитарного дня | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-03-25/otmena-sanitarnogo-dnya) |
| 2022-03-22 | Фестиваль «Детские дни в Петербурге» | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-03-22/festival-detskie-dni-v-peterburge) |
| 2022-03-16 | Телеграм-канал нашего музея | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-03-16/telegram-kanal-nashego-muzeya) |
| 2022-03-04 | 8 марта музей закрыт! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-03-04/8-marta-muzey-zakryt) |
| 2022-03-03 | Отмена QR-кодов! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-03-03/otmena-qr-kodov) |
| 2022-02-25 | Выставка «Лоскутная полифония» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-02-25/vystavka-loskutnaya-polifoniya) |
| 2022-02-18 | 23 февраля музей закрыт! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-02-18/23-fevralya-muzey-zakryt) |
| 2022-02-01 | Изменение режима работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2022-02-01/izmenenie-rezhima-raboty-muzeya) |
| 2022-01-26 | Запрет на посещение музея | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-01-26/zapret-na-poseshchenie-muzeya) |
| 2022-01-11 | Продление работы выставки | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2022-01-11/prodlenie-raboty-vystavki) |
| 2021-12-28 | Режим работы музея в январе 2022 г. | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2021-12-28/rezhim-raboty-muzeya-v-yanvare-2022-g) |
| 2021-12-16 | Проект «Мост в будущее: креативные практики сохранения и развития живого наследия» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-12-16/proekt-most-v-budushchee-kreativnye-praktiki-sohraneniya-i-razvitiya-zhivogo) |
| 2021-12-10 | Режим работы музея в декабре 2021 года | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2021-12-10/rezhim-raboty-muzeya-v-dekabre-2021-goda) |
| 2021-11-30 | Выставка «В ожидании чуда» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-11-30/vystavka-v-ozhidanii-chuda) |
| 2021-11-27 | Выставка «Хроники голодных лет» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-11-27/vystavka-hroniki-golodnyh-let) |
| 2021-11-10 | Выставка «Хлеб в мировой истории» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-11-10/vystavka-hleb-v-mirovoy-istorii) |
| 2021-10-27 | Изменение правил посещения музея | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-10-27/izmenenie-pravil-poseshcheniya-muzeya) |
| 2021-10-22 | «Детские дни» в музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-10-22/detskie-dni-v-muzee-hleba) |
| 2021-09-30 | Выставка «Блокада Ленинграда. 80 лет» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-09-30/vystavka-blokada-leningrada-80-let) |
| 2021-09-03 | Экскурсия ко Дню начала Блокады | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-09-03/ekskursiya-ko-dnyu-nachala-blokady) |
| 2021-09-02 | Продолжается регистрация команд на участие в 14-м сезоне Большой Регаты! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-09-02/prodolzhaetsya-registraciya-komand-na-uchastie-v-14-m-sezone-bolshoy-regaty) |
| 2021-08-26 | День Знаний в музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-08-26/den-znaniy-v-muzee-hleba) |
| 2021-08-25 | «Музеи — детям» в Летнем саду | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-08-25/muzei-detyam-v-letnem-sadu) |
| 2021-08-24 | Новый сезон «Большой Регаты» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-08-24/novyy-sezon-bolshoy-regaty) |
| 2021-08-13 | Большая Музейная Прогулка | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-08-13/bolshaya-muzeynaya-progulka) |
| 2021-08-11 | Выставка «Щедрый Август. Три Спаса» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-08-11/vystavka-shchedryy-avgust-tri-spasa) |
| 2021-08-02 | Выставка из серии «Короткой строкой» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-08-02/vystavka-iz-serii-korotkoy-strokoy) |
| 2021-07-02 | Аудиогид на izi.TRAVEL | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-07-02/audiogid-na-izitravel) |
| 2021-06-28 | День Достоевского в музее Хлеба | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-06-28/den-dostoevskogo-v-muzee-hleba) |
| 2021-06-08 | 12 июня музей закрыт! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2021-06-08/12-iyunya-muzey-zakryt) |
| 2021-06-07 | Приглашаем на семинар! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-06-07/priglashaem-na-seminar) |
| 2021-05-28 | Выставка продолжает свою работу | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-05-28/vystavka-prodolzhaet-svoyu-rabotu) |
| 2021-05-27 | Приглашаем на пешеходную экскурсию! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-05-27/priglashaem-na-peshehodnuyu-ekskursiyu) |
| 2021-05-04 | В музее открылась мини-выставка, посвященная Дню напитков! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-05-04/v-muzee-otkrylas-mini-vystavka-posvyashchennaya-dnyu-napitkov) |
| 2021-04-30 | Майские праздники в музее Хлеба! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-04-30/mayskie-prazdniki-v-muzee-hleba) |
| 2021-04-28 | Режим работы музея | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2021-04-28/rezhim-raboty-muzeya) |
| 2021-04-21 | Выставка ко Дню пряника | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-04-21/vystavka-ko-dnyu-pryanika) |
| 2021-04-20 | Выставка «Пасхальные традиции Петербурга» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-04-20/vystavka-pashalnye-tradicii-peterburga) |
| 2021-04-15 | Приглашаем на экскурсии! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-04-15/priglashaem-na-ekskursii) |
| 2021-04-13 | Выставка «В гостях у сказки» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-04-13/vystavka-v-gostyah-u-skazki) |
| 2021-04-09 | Выставка ко Дню космонавтики | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-04-09/vystavka-ko-dnyu-kosmonavtiki) |
| 2021-04-09 | Экскурсии в музее! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-04-09/ekskursii-v-muzee) |
| 2021-04-01 | Сохранёние уникального облика Петербурга в руках жителей города | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-04-01/sohranyonie-unikalnogo-oblika-peterburga-v-rukah-zhiteley-goroda) |
| 2021-03-19 | Весенние каникулы в музее | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-03-19/vesennie-kanikuly-v-muzee) |
| 2021-03-01 | Масленица в музее! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-03-01/maslenica-v-muzee) |
| 2021-02-20 | 23 февраля музей открыт! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2021-02-20/23-fevralya-muzey-otkryt) |
| 2021-02-19 | Билеты в музей онлайн | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-02-19/bilety-v-muzey-onlayn) |
| 2021-02-15 | Билеты за баллы! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-02-15/bilety-za-bally) |
| 2021-02-03 | Экскурсии в музее | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-02-03/ekskursii-v-muzee) |
| 2021-01-29 | Музей приглашает | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-01-29/muzey-priglashaet) |
| 2021-01-26 | Музей Хлеба приглашает на экскурсии! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-01-26/muzey-hleba-priglashaet-na-ekskursii) |
| 2021-01-15 | Выставка «Рождество в Петербурге. Метаморфозы праздника» будет открыта до 13 февраля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2021-01-15/vystavka-rozhdestvo-v-peterburge-metamorfozy-prazdnika-budet-otkryta-do-13) |
| 2020-12-24 | Внимание! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2020-12-24/vnimanie) |
| 2020-12-22 | Музей Хлеба приглашает | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-12-22/muzey-hleba-priglashaet) |
| 2020-12-17 | Транспортный бот в Telegram | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2020-12-17/transportnyy-bot-v-telegram) |
| 2020-12-14 | Выставка " Рождество в Петербурге. Метаморфозы праздника" | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-12-14/vystavka-rozhdestvo-v-peterburge-metamorfozy-prazdnika) |
| 2020-12-03 | Внимание! Уважаемые посетители! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-12-03/vnimanie-uvazhaemye-posetiteli) |
| 2020-11-30 | «Эстафета доброты» 2020 | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-11-30/estafeta-dobroty-2020) |
| 2020-10-29 | 4 ноября музей закрыт | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2020-10-29/4-noyabrya-muzey-zakryt) |
| 2020-10-24 | 27 октября музей открыт! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2020-10-24/27-oktyabrya-muzey-otkryt) |
| 2020-10-23 | На каникулах - в музей! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-10-23/na-kanikulah-v-muzey) |
| 2020-10-21 | «Колобок» 7 ноября в 15.00 | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-10-21/kolobok-7-noyabrya-v-1500) |
| 2020-09-29 | «КОЛОБОК» 3 октября | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-09-29/kolobok-3-oktyabrya) |
| 2020-09-24 | Форум малых музеев | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-09-24/forum-malyh-muzeev) |
| 2020-09-23 | Экскурсии в музее | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2020-09-23/ekskursii-v-muzee) |
| 2020-09-22 | Приглашаем на семинар! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-09-22/priglashaem-na-seminar) |
| 2020-09-17 | Санкт-Петербургский музей Хлеба приглашает на экскурсию "Хлеб в Петербурге" | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2020-09-17/sankt-peterburgskiy-muzey-hleba-priglashaet-na-ekskursiyu-hleb-v-peterburge) |
| 2020-09-11 | Началась регистрация команд для участия в новом сезоне "Большой Регаты"! Присоединяйтесь! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-09-11/nachalas-registraciya-komand-dlya-uchastiya-v-novom-sezone-bolshoy-regaty) |
| 2020-08-31 | Дорогие друзья! с 1 сентября музей Хлеба работает в обычном режиме! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-08-31/dorogie-druzya-s-1-sentyabrya-muzey-hleba-rabotaet-v-obychnom-rezhime) |
| 2020-07-20 | Музей Хлеба приглашает на экскурсии! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2020-07-20/muzey-hleba-priglashaet-na-ekskursii) |
| 2020-07-07 | Дорогие друзья! 7 июля музей Хлеба снова открывает свои двери для посетителей! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-07-07/dorogie-druzya-7-iyulya-muzey-hleba-snova-otkryvaet-svoi-dveri-dlya-posetiteley) |
| 2020-06-03 | Уверенная навигация в культурном пространстве — на портале «Культура Петербурга» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-06-03/uverennaya-navigaciya-v-kulturnom-prostranstve-na-portale-kultura-peterburga) |
| 2020-03-27 | Музей не работает с 28 марта по 30 апреля | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-03-27/muzey-ne-rabotaet-s-28-marta-po-30-aprelya) |
| 2020-03-23 | Новая рубрика в социальных сетях музея | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-03-23/novaya-rubrika-v-socialnyh-setyah-muzeya) |
| 2020-03-19 | Музей приостанавливает прием посетителей с 19 марта | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2020-03-19/muzey-priostanavlivaet-priem-posetiteley-s-19-marta) |
| 2020-03-18 | Уважаемые друзья! | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-03-18/uvazhaemye-druzya) |
| 2020-03-06 | Режим работы музея 7, 8 , 9 марта | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2020-03-06/rezhim-raboty-muzeya-7-8-9-marta) |
| 2020-02-21 | Экскурсия «Цена Хлеба» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-02-21/ekskursiya-cena-hleba) |
| 2020-02-04 | Экскурсия в фонд открытого хранения | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-02-04/ekskursiya-v-fond-otkrytogo-hraneniya) |
| 2020-01-22 | Экскурсии ко Дню полного освобождения Ленинграда от фашистской блокады | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-01-22/ekskursii-ko-dnyu-polnogo-osvobozhdeniya-leningrada-ot-fashistskoy-blokady) |
| 2020-01-14 | Маршрут фестиваля «Детские Дни в Петербурге» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2020-01-14/marshrut-festivalya-detskie-dni-v-peterburge) |
| 2019-12-27 | Музей Хлеба приглашает! | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2019-12-27/muzey-hleba-priglashaet) |
| 2019-12-16 | Режим работы музея в праздничные дни | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2019-12-16/rezhim-raboty-muzeya-v-prazdnichnye-dni) |
| 2019-12-06 | Семинар в музее | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2019-12-06/seminar-v-muzee) |
| 2019-11-20 | «Эстафета доброты» | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2019-11-20/estafeta-dobroty) |
| 2019-11-14 | Общероссийская акция «Сообщи, где торгуют смертью» | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2019-11-14/obshcherossiyskaya-akciya-soobshchi-gde-torguyut-smertyu) |
| 2019-10-24 | Во время фестиваля "Детские Дни в Петербурге" музей Хлеба будет работать по воскресеньям | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2019-10-24/vo-vremya-festivalya-detskie-dni-v-peterburge-muzey-hleba-budet-rabotat-po) |
| 2019-10-14 | 22 октября - санитарный день в музее | Плакат без текста | [Музей](https://muzei-xleb.ru/novosty/2019-10-14/22-oktyabrya-sanitarnyy-den-v-muzee) |
| 2019-10-10 | «Колобок» 19 октября | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2019-10-10/kolobok-19-oktyabrya) |
| 2019-09-10 | Мастер-класс "Зерновушка" 21 сентября | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2019-09-10/master-klass-zernovushka-21-sentyabrya) |
| 2019-09-01 | "Колобок" 7 сентября в 11.00 | Исходный HTML | [Музей](https://muzei-xleb.ru/novosty/2019-09-01/kolobok-7-sentyabrya-v-1100) |

**Открытые ссылочные пробелы исторического контента:** в самих новостях встречаются старые Drupal-адреса `/node/N` и две дополнительные ссылки на подробности выставок. Их нужно сверять отдельно по исходной странице перед признанием миграции всей архитектуры сайта завершённой. [Контроль исходных ссылок](NEWS_ARCHIVE_NESTED_ORIGINAL_LINKS_20261018.csv).
