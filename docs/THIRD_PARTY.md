# MusBread — внешние лицензии и зависимости

Проект публичен. При заключении контракта нужно согласовать с юристом заказчика разграничение исключительных прав на собственные результаты разработки и прав по лицензиям сторонних библиотек.

| Компонент | Использование | Лицензия / вопрос |
|---|---|---|
| Laravel | backend | MIT |
| MoonShine | CMS | MIT |
| Next.js | frontend | MIT |
| sanitize-html | фильтрация HTML в статическом рендере | MIT |
| HTMLPurifier | очистка HTML при сохранении | LGPL-2.1-or-later |
| TinyMCE (в поставке moonshine/tinymce) | WYSIWYG в CMS, без Tiny Cloud API | **GPL-2.0-or-later**; при передаче кода необходимо соблюдать условия GPL. Проверить совместимость с передачей исключительных прав и при необходимости заменить редактор до сдачи. |

Платные API или SaaS-подписки не подключены. Встроенные JS/CSS редактора размещаются локально в CMS. **Нельзя передавать заказчику исключительные права на исходный код сторонних открытых библиотек**.

## Техническая безопасность

- HTML всех музейных материалов очищается при сохранении HTMLPurifier.
- Статическая страница повторно очищает HTML с помощью sanitize-html.
- Скрипты, iframe, javascript:-ссылки и атрибуты JS-событий запрещены.
- 15.10.2026: npm audit --omit=dev — ноль известных предупреждений для production зависимостей. Полный npm audit сообщает о пяти high для dev-цепочки ESLint/Next.js; исправление сейчас требует нежелательного major downgrade. Не запускать npm audit fix --force автоматически.
- Для production потребуются согласованный пентест и повторный dependency audit.

## CP-33D — уточнение по реальным lock-файлам

Подтверждено на Mac mini: moonshine/tinymce 2.0.0 имеет MIT у обёртки по composer.lock и её LICENSE.md, но вложенный JavaScript TinyMCE имеет **отдельную GPL-2.0-or-later** в vendor/moonshine/tinymce/public/license.md. Это нельзя смешивать или объявлять исключительной собственностью компании. Перед окончательной передачей кода юрист должен согласовать выполнение условий GPL, структуру поставки либо замену редактора.

ezyang/htmlpurifier v4.19.1 — LGPL-2.1-or-later по composer.lock. php laravel/framework v13.36.0, moonshine/moonshine 4.19.5 — MIT. По package-lock.json Next.js 16.4.1, React/React DOM 19.3.0 и sanitize-html 2.18.1 — MIT. Два pinned Python инструмента: python-pptx 1.0.2 (MIT metadata), pypdf 5.6.1 (BSD family classifier, exact license text needs confirmation). Native librsvg вне этих application lock-файлов.

Это ограниченная проверка выбранных прямых компонентов, **не полный SBOM**. Декларация лицензии не равна успешному исполнению условий или юридическому разрешению передать сторонний код как собственный. См. docs/handoff/DEPENDENCY_RIGHTS_REPORT.md и docs/CP33_FORMATS_RIGHTS_AUDIT.md.
