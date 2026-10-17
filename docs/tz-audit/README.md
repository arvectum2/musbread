# Аудит первичного ТЗ MusBread

Исходный документ — «Описание объекта закупки», приложение 3 к извещению №0372200172326000015. Анализ по оригиналу tz.docx и локальному tz.txt на Mac mini, 485 физических строк; сравнение DOCX/TXT токенов подтвердило полноту текстовой выгрузки.

- [TZ_FULL_MATRIX.md](TZ_FULL_MATRIX.md): 325 отдельных проверяемых обязательств с пунктом первоисточника, исходными строками, колонками **Учли? / Готово?**, текущими свидетельствами, недостающими действиями, потребностями музея и приоритетами.
- [TZ_FULL_MATRIX.csv](TZ_FULL_MATRIX.csv): та же таблица для фильтрации/Excel (UTF-8 BOM).
- [requirements.psv](requirements.psv): редактируемый канонический реестр строк без автоматически вычисленных данных.
- [TZ_RECOVERY_CHECKPOINTS.md](TZ_RECOVERY_CHECKPOINTS.md): девять крупных чекпоинтов, ссылки на GitHub Issues и план приоритетов.

Обновление реестра: изменить requirements.psv и запустить из корня python3 scripts/render_tz_audit.py, затем python3 -m unittest tests/test_tz_audit.py -v. Исходные файлы заказчика и секреты не включены в публичный репозиторий. Результат аудита — внутренняя карта обязательств, не подписанный акт приёмки и не юридическое заключение.

## Сквозной аудит первоначального ТЗ и проекта контракта, 17.10.2026

- [Общий построчный протокол и 25 важнейших вопросов](TZ_CONTRACT_ROADMAP_DEEP_AUDIT.md).
- [284 открытых TZ с отметкой учёта, недостающими действиями, вопросом заказчику](OPEN_CUSTOMER_QUESTIONS.md) / [CSV](OPEN_CUSTOMER_QUESTIONS.csv).
- [125 договорных блоков с физическими строками и вопросами](CONTRACT_CLAUSE_MAP.md) / [CSV](CONTRACT_CLAUSE_MAP.csv).
- [25 рисков/разночтений проекта контракта](CONTRACT_DISCREPANCIES_AND_RISKS.csv).

Оригиналы хранятся только в /Volumes/ArvectumSSD/Arvectum/data/tenders/eis/0372200172326000015, не в Git. Их повторные извлечения из Word побайтово совпадают с tz.txt (485 строк) и contract.txt (837 строк); основные приложения ТЗ совпали по 317 содержательным строкам. Закрытые физические построчные регистры только в .local_archive/primary-source-audit. Повторить: python3 scripts/build_customer_questions_audit.py, python3 scripts/audit_primary_contract.py --source-dir /Volumes/ArvectumSSD/Arvectum/data/tenders/eis/0372200172326000015, python3 scripts/render_primary_audit_summary.py. Статус договора: проект, не подписан.
