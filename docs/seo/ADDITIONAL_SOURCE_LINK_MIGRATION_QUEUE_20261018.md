# Очередь дополнительного переноса из найденных внутренних ссылок музея · 18.10.2026

**Источник:** буквальные ссылки из исходного HTML старого сайта, проверенного по SHA-256 и сохранённого на Mac mini SSD. [Полная CSV-матрица исходных ссылок и страниц-источников](ORIGINAL_MUSEUM_CROSSLINK_GAPS_20261018.csv). Это **82 недообследованных URL, а не 82 обнаруженные 404**. Нельзя закрывать SEO-гейт только по первым 518 адресам.

| Вид исходной ссылки | Ещё не покрытых уникальных URL | Следующее действие |
|---|---:|---|
| Публичные страницы/узлы Drupal | 21 | Скачать конечные адреса через Mac mini, сохранить настоящий H1/текст/URL, проверить статус и canonical. 301 — только для настоящего исходного редиректа. |
| PDF/DOCX | 24 | Скачать исходные байты, проверить magic, SHA-256 и разложить по первоначальным URL в полной локальной сборке. |
| JPEG/PNG | 37 | Скачать оригиналы без OCR, показать как собственные WebP и сопоставить старые file URL для Nginx. |

## Принцип обработки

1. Приоритизировать реально существующие страницы, правовые/финансовые PDF и фото, на которые ссылаются публичные материалы. Не генерировать недоступные оригиналы и не считать ссылки на действующий музей конечным решением после DNS.
2. Каждую ссылку проверять прямым HTTP через Mac mini с crawl-delay=10 с. Для текущих 403/404 сохранять точный исходный код/URL и решение заказчика; не делать фиктивный `200`.
3. После каждой партии — заново прогонять `scripts/audit_museum_original_crosslinks.py`, сборку `npm run build:museum-deploy` и `scripts/audit_museum_seo_migration_cutover.py`. Новые оригиналы могут содержать новые вложенные ссылки; это рекурсивная, но конечная по проверяемому корпусу проверка.
4. Боевая индексация, sitemap, robots, `301/308`, Yandex Webmaster / GSC / Метрика и DNS остаются **NO-GO** без утверждения музея и реальной площадки.

## Адреса, уже недоступные у самого первоисточника

- `/node/462` → музейная афиша мая 2026, старый музей возвращает HTTP 403.
- `/obratnaya-svyaz` → исходный HTTP 403.
- `/sites/default/files/page/202110271242-prikaz_no94.pdf` → исходный HTTP 404; исторический приказ нельзя подменять.

## Ближайший проверяемый пакет: документы

| Исходный путь документа | Число ссылок в подтверждённых музейных статьях |
|---|---:|
| `/sites/default/files/page/201215131505_0001.pdf` | 1 |
| `/sites/default/files/page/201215160030_0001.pdf` | 1 |
| `/sites/default/files/page/202110271242-prikaz_no94.pdf` | 1 |
| `/sites/default/files/page/20231102115627-pismo_monitoring_2023.docx` | 1 |
| `/sites/default/files/page/20231102115627-prikaz_monitoring_2023.pdf` | 1 |
| `/sites/default/files/page/20240826123542-1.pdf` | 1 |
| `/sites/default/files/page/20240910101626-polozhenie_o_muzee_istorii_hlebopecheniya.pdf` | 1 |
| `/sites/default/files/page/20240910101626-prikaz_o_muzee_hleba.pdf` | 1 |
| `/sites/default/files/page/20241114141130-1.pdf` | 1 |
| `/sites/default/files/page/20250418101708-1._pfhd_na_01.01.2025_f.56.pdf` | 1 |
| `/sites/default/files/page/20250620100612-protokoly_pervoe_polugodie_2025.pdf` | 1 |
| `/sites/default/files/page/20250620100746-monitoring_pervoe_polugodie_2025.pdf` | 1 |
| `/sites/default/files/page/20251224111452-monitoring_za_2025_g.pdf` | 1 |
| `/sites/default/files/page/20251224212255-protokol_3_za_2025_g.pdf` | 1 |
| `/sites/default/files/page/20260119162140-1.pdf` | 1 |
| `/sites/default/files/page/221216115845_0001.pdf` | 1 |
| `/sites/default/files/page/plan_finansovo-hozyaystvennoy_deyatelnosti_muzeya_11.12.2018.pdf` | 1 |
| `/sites/default/files/page/plan_na_2022.pdf` | 1 |
| `/sites/default/files/page/prikaz_monitoring_21.pdf` | 1 |
| `/sites/default/files/page/prikaz_pismo_monitoring.pdf` | 1 |
| `/sites/default/files/page/prikaz_plan_22.pdf` | 1 |
| `/sites/default/files/page/svodnaya_vedomost_sout_1.pdf` | 1 |
| `/sites/default/files/page/svodnaya_vedomost_sout_2.pdf` | 1 |
| `/sites/default/files/page/svodnaya_vedomost_sout_3.pdf` | 1 |

## Ближайший проверяемый пакет: дополнительные страницы

| Исходный путь | Количество подтверждённых источников |
|---|---:|
| `/node/462` | 9 |
| `/node/100` | 1 |
| `/node/189` | 1 |
| `/node/191` | 1 |
| `/node/198` | 1 |
| `/node/199` | 1 |
| `/node/207` | 1 |
| `/node/269` | 1 |
| `/node/270` | 1 |
| `/node/271` | 1 |
| `/node/283` | 1 |
| `/node/291` | 1 |
| `/node/361` | 1 |
| `/node/425` | 1 |
| `/node/454` | 1 |
| `/node/455` | 1 |
| `/node/495` | 1 |
| `/node/536` | 1 |
| `/node/633` | 1 |
| `/obratnaya-svyaz` | 1 |
| `/vistavky/2019-06-21/peterburgskoe-chaepitie-20-iyunya-31-avgusta-2019-g` | 1 |

**Актуальный технический SEO-срез:** [518 старых путей](URL_MIGRATION_MATRIX_20261018.csv), из них 448 собственных HTML и 70 source-verified Drupal node-переходов, для которых подготовлен, но пока не активирован HTTP 301. Полный набор документов — 59, изображений — 269 исходных URL / 264 уникальных WebP. Продакшн **NO-GO**.
