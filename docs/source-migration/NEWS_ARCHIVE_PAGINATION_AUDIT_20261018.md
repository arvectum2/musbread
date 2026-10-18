# Архив новостей: следующая очередь источников — 18.10.2026

Прямые HTTP GET с Mac mini по `/novosty?page=1` и `?page=2`. Это **поимённая сверка и завершённый перенос полных HTML-текстов 20 публикаций** с проверкой SHA-256 и оригинальных ссылок. Последние 10 новостей первой страницы остались отдельной новостной лентой. Ещё 20 архивных новостей добавлены в приватные редакторские черновики и отдельную архивную секцию `/news/`; все фотографии отложены до согласования прав. Перенос этих двадцати **не** доказывает полноту исторического архива.

| Страница архива | Новостей в листинге | Уже известных из актуальной десятки |
|---|---:|---:|
| `?page=1` | 10 | 0 |
| `?page=2` | 10 | 0 |

## Перенесённые подлинные архивные материалы

| Исходная дата | Название | Оригинальный URL |
|---|---|---|
| 2026-08-31 | События в музее с 31 августа по 7 сентября | https://muzei-xleb.ru/novosty/2026-08-31/sobytiya-v-muzee-s-31-avgusta-po-7-sentyabrya |
| 2026-08-24 | События в музее с 24 по 31 августа | https://muzei-xleb.ru/novosty/2026-08-24/sobytiya-v-muzee-s-24-po-31-avgusta |
| 2026-08-17 | События в музее с 17 по 24 августа | https://muzei-xleb.ru/novosty/2026-08-17/sobytiya-v-muzee-s-17-po-24-avgusta |
| 2026-08-10 | События в музее с 10 по 17 августа | https://muzei-xleb.ru/novosty/2026-08-10/sobytiya-v-muzee-s-10-po-17-avgusta |
| 2026-08-03 | События в музее с 3 по 10 августа | https://muzei-xleb.ru/novosty/2026-08-03/sobytiya-v-muzee-s-3-po-10-avgusta |
| 2026-07-27 | События в музее с 27 июля по 3 августа | https://muzei-xleb.ru/novosty/2026-07-27/sobytiya-v-muzee-s-27-iyulya-po-3-avgusta |
| 2026-07-17 | События в музее с 20 июля по 26 июля | https://muzei-xleb.ru/novosty/2026-07-17/sobytiya-v-muzee-s-20-iyulya-po-26-iyulya |
| 2026-07-13 | События в музее с 13 июля по 20 июля | https://muzei-xleb.ru/novosty/2026-07-13/sobytiya-v-muzee-s-13-iyulya-po-20-iyulya |
| 2026-07-07 | События в музее с 06 июля по 12 июля | https://muzei-xleb.ru/novosty/2026-07-07/sobytiya-v-muzee-s-06-iyulya-po-12-iyulya |
| 2026-06-28 | События в музее с 29 июня по 05 июля | https://muzei-xleb.ru/novosty/2026-06-28/sobytiya-v-muzee-s-29-iyunya-po-05-iyulya |
| 2026-06-22 | События в музее с 22 по 28 июня | https://muzei-xleb.ru/novosty/2026-06-22/sobytiya-v-muzee-s-22-po-28-iyunya |
| 2026-06-16 | События в музее с 15 по 21 июня | https://muzei-xleb.ru/novosty/2026-06-16/sobytiya-v-muzee-s-15-po-21-iyunya |
| 2026-06-08 | События в музее с 10 по 15 июня | https://muzei-xleb.ru/novosty/2026-06-08/sobytiya-v-muzee-s-10-po-15-iyunya |
| 2026-06-02 | События в музее с 03 по 08 июня | https://muzei-xleb.ru/novosty/2026-06-02/sobytiya-v-muzee-s-03-po-08-iyunya |
| 2026-05-26 | События в музее с 27 мая по 01 июня | https://muzei-xleb.ru/novosty/2026-05-26/sobytiya-v-muzee-s-27-maya-po-01-iyunya |
| 2026-05-18 | События на неделе с 20 по 24 мая | https://muzei-xleb.ru/novosty/2026-05-18/sobytiya-na-nedele-s-20-po-24-maya |
| 2026-05-15 | ДОРОГИЕ ДРУЗЬЯ! | https://muzei-xleb.ru/novosty/2026-05-15/dorogie-druzya |
| 2026-05-14 | Выставка «Я без пропитания оставаться не могу...» | https://muzei-xleb.ru/novosty/2026-05-14/vystavka-ya-bez-propitaniya-ostavatsya-ne-mogu |
| 2026-05-13 | Совсем скоро "Ночь музеев"! | https://muzei-xleb.ru/novosty/2026-05-13/sovsem-skoro-noch-muzeev |
| 2026-05-13 | Фестиваль «Петербург. Пространство Булгакова» | https://muzei-xleb.ru/novosty/2026-05-13/festival-peterburg-prostranstvo-bulgakova |

**Выполнено:** HTML каждой из 20 перечисленных публикаций извлечён по указанному исходному URL, SHA-256 сохранён в `apps/web/src/data/official-museum-news-archive.json`, приватные черновики добавлены командой `php artisan museum:import-official-archive-news --apply`, редакторские правки и публичные права сохранены. `/news/` показывает отдельный архивный каталог без вымышленных анонсов, изображений или продаж билетов. Проверено 3 PHP, 2 Python, 5 браузерных E2E, Next.js production build.

**Дальнейшая очередь:** у действующего музея пагинатор ведёт на `?page=27` (28 страниц вместе с первой). Мы перенесли только страницы с индексами 0, 1, 2 — оставшиеся 25 страниц `?page=3`–`?page=27` требуют дальнейшей поэтапной сверки источников, количество самих публикаций пока не подтверждено.
