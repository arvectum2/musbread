# CP-22 — передача исходников и результатов (только подготовка)

Комплект:
- DELIVERY_STRUCTURE.md — структура ZIP, будущий набор и порядок проверки;
- RIGHTS_MATRIX.md — собственные/сторонние права и риски TinyMCE GPL;
- ADMIN_GUIDE_TEMPLATE.md / EDITOR_GUIDE_TEMPLATE.md — инструкции;
- ACT_RIGHTS_DRAFT.md / DELIVERY_ACT_DRAFT.md / FINAL_REPORT_TEMPLATE.md — **не подписанные** проекты;
- HDD_YANDEX_CHECKLIST.md — физическая/облачная передача и SHA;
- scripts/handoff_bundle.py — ZIP по Git HEAD, MANIFEST, INVENTORY, STATUS, SHA256SUMS;
- tests/test_handoff_bundle.py — тесты защиты от повреждения/секретов и воспроизводимости.

Рабочее значение PRE-AWARD означает, что права не переданы, заказчик ничего не согласовал и исходные файлы по ТЗ ещё не изготовлены полностью. Не включать реальные персональные данные, пароли, API токены и закрытую переписку в публичные файлы.

Запуск из корня:

    python3 scripts/handoff_bundle.py build --output /tmp/musbread_preaward.zip
    python3 scripts/handoff_bundle.py verify /tmp/musbread_preaward.zip

Архивная копия создаётся из **зафиксированного Git HEAD**, не из uncommitted изменений. Перечень не изготовленных форматов в STATUS.json. Автоматическое обнаружение ключей не заменяет ручной DLP-аудит. Перед официальной передачей провести юридическую и содержательную проверку.
