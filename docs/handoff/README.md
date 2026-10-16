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

## CP-28D — руководство посетителю и проверка комплекта

VISITOR_GUIDE_DRAFT.md — самостоятельный черновик пользовательской инструкции для текущей демонстрации, а не утверждённый музейный документ. scripts/audit_delivery_readiness.py проверяет наличие 17 заготовок и перечисляет 16 внешних условий для реальной сдачи. Они не превращаются в выполненные при успешных тестах.

## CP-29D — полная детализация дизайна и носителей

DESIGN_DELIVERABLES.csv и DESIGN_DELIVERABLES.md — 113 атомарных целей по ТЗ. DESIGN_EVIDENCE.csv (пока без строк) привязывает будущие реальные исходники к целям. CUSTOMER_INPUTS_AFTER_INTERVIEW.md — машинная матрица вопросов, CUSTOMER_INTERVIEW_DESIGN_CHECKLIST.md — русский бриф для первого интервью. Проверка scripts/audit_design_delivery.py выявляет потерянные целевые элементы и неподходящие файлы, но принципиально не выдаёт согласованную оригинальную графику за готовую по одной подписи. Полная методология docs/CP29_DESIGN_HANDOFF_SPEC.md.

## CP-30D neutral technical templates

docs/design/technical-drafts contains 13 editable SVG, 13 PDF previews and two real editable PPTX sample decks. They are explicitly TECHNICAL_DRAFT_ONLY; proposed 3mm bleed and 10mm safe guides require confirmation. The delivery evidence checker rejects these drafts as final art. All 113 actual customer design positions remain unapproved.
