# CP-JODIT-01 — замена TinyMCE на бесплатный Jodit CE без лицензионного платежа

**19.10.2026. Закупка №0372200172326000015.** Внутренняя доконтрактная CMS на Mac mini; рабочая база музея, его сайт, DNS и дизайн не затронуты.

## Решение и статус

**ВЫПОЛНЕНО:** Jodit Community **4.18.4**, **MIT**, self-hosted WYSIWYG вместо TinyMCE. Исходное ТЗ требует WYSIWYG, HTML и удобство редактирования, но не бренд конкретного редактора. *Обязательной лицензии PRO, подписки, платного ключа и доступа к внешнему API нет.* Лицензия MIT **не равна отсутствию обязательств вообще**: текст MIT и copyright notice включены в исходники и должны сохраняться в каждой переданной копии.

| Контроль | Доказательство |
|---|---|
| Бесплатная коммерческая лицензия | В оригинальном `jodit@4.18.4` npm tarball MIT, оригинальный `LICENSE.txt`, `package.json` dependencies `{}`; платные Jodit PRO assets не скачивались |
| Переход текущей MoonShine формы | Собственное поле `App\\MoonShine\\Fields\\Jodit` заменило `MoonShine\\TinyMce`; `MUSEUM_ENTRY_BODY_EDITOR=jodit` по умолчанию; `html-source` остаётся резервом |
| Совместимость с данными | **То же `body` HTML** и модели SQLite/Laravel, без миграции БД; HTMLPurifier/XSS whitelist, разрешения и предварительное одобрение сохранены |
| UX и источник HTML | Настоящая панель Jodit: текст, H2, списки, ссылка, source HTML, кнопки undo/redo. Обязательные функции проверены в Chrome в рамках **8 CMS браузерных E2E** |
| Сквозной QA, а не макет | HTTP MoonShine → редактирование через Jodit → SQLite → JSON/manifest SHA → Next.js HTML, запрет утечки черновиков; 8 browser сценариев PASS, доставка и rollback в изолированном QA PASS |
| Backend | **343 теста Laravel, 3573 проверки**, включая редактор, ролевую модель и безопасность, PASS |
| TinyMCE из поставки | `moonshine/tinymce` **отсутствует** в `apps/cms/composer.json`, `composer.lock`, установленном `vendor/`, публичных CMS asset-ресурсах и разрешённых namespace Nginx |
| Полный инвентарь | `docs/handoff/SBOM_CYCLONEDX.json` — **559 записей**, Jodit MIT вместо GPL TinyMCE, 82 Composer production, 33 dev, 440 web lock, 2 pinned design Python и 1 native tool. Две библиотеки Composer имеют GPL/BSD альтернативы; это **не embedded TinyMCE**, и нет утверждения, что все лицензии системы свободны от условий. |
| Публичность исходников | Файлы `jodit.min.js`, `jodit.min.css`, `museum-jodit-init.js` и `LICENSE.txt` закреплены непосредственно в Git, **несмотря на общее правило `.gitignore` для `vendor/`**; новая установка из Git не требует повторной загрузки редактора с CDN |

SHA-256 файлов **официального npm-архива `jodit@4.18.4`**:

| Файл | SHA-256 |
|---|---|
| npm tarball | `e55b1247f9e4c2479b3918692481119b5ff0ce6a0481c69a0ecf76dc139bf056` |
| `public/vendor/museum-jodit/jodit.min.js` | `d65fd78a72e6acfdae4cb0f47fef3c90f72ff8b40d5043313b49c4757db62008` |
| `public/vendor/museum-jodit/jodit.min.css` | `4195186166912468e2a361c6be27d42f5b78b7487fb54f14155ca83d3a6e9035` |
| `public/vendor/museum-jodit/LICENSE.txt` | `b6eccb41553c575c01f6a1261e87fdc7b842a721d6ba9daa88bdbd9259865d55` |

Источники: https://github.com/xdan/jodit и https://github.com/xdan/jodit/blob/main/LICENSE.txt . **Регистрация Jodit в реестре российского ПО не подтверждена.** Наличие российского разработчика не заменяет официальную запись.

## Безопасность и ограничения

- Доступ в CMS ограничен авторизацией/CSRF, на публичном Next нет PHP редактора. Собственный Jodit field загружает JS/CSS **только с CMS**, без CDN, API-ключей и облачной записи документов.
- Нет кнопок прямой загрузки `image/file/video`, отключён `insertImageAsBase64URI` и загрузчик; изображения должны попадать в проверенную CMS-медиатеку и публиковаться только после обычного утверждения. Никакой режим WYSIWYG не обходит серверную очистку HTML.
- Сквозной Playwright работает только с временными учётными данными/SQLite и тестовым сервером `127.0.0.1`, не создаёт контент музея и не меняет его сайт.
- В `infra/nginx/private-cms.conf` разрешены только `/vendor/moonshine/` и `/vendor/museum-jodit/` для JS/CSS/картинок. PHP, исходные текстовые notices и прочие vendor-каталоги не раскрываются через HTTP. Лицензия MIT входит **в поставляемый репозиторий/отдельные notices**.
- Технические вендорные проверки оставляют открытым использование шрифтов `Gilroy`, прав на музейные фото и другие условия сторонних зависимостей; это **не вопрос лицензии Jodit**, но требуется для окончательного TZ-313.
- **Доставка:** четыре файла Jodit принудительно добавлены в Git, несмотря на глобальный `.gitignore` для `vendor/`, поэтому обычный `git clone` сохраняет полностью автономный WYSIWYG. Отдельный доконтрактный «source-only demo ZIP» сознательно *не* включает любые `public/vendor/`-ассеты и не является полноценной инсталляцией CMS; он не должен выдаваться за готовую поставку. Для реального стенда/приёмки использовать репозиторий со всеми четырьмя файлами и проверить MIT `LICENSE.txt`/хеши.

## Светофор ТЗ после решения

**TZ-313 «Результаты не должны нарушать права третьих лиц»: 🔴 → 🟡.** Вложенный вопрос **лицензирования редактора — выполнен**, всё правоотношение по стороннему контенту — **не закрыто**. Для 🟢 необходимы права на фактические изображения/брендбук/шрифты и правильное исключение стороннего кода из акта исключительных прав. TZ-308/309 (редакторское обучение и приёмка) остаются частичными до договора, несмотря на успешную локальную проверку Jodit. Других обязательств сверх ТЗ не добавлено.

Сводный счётчик **🟢84 / 🟡116 / 🔴125** из 325.

## Воспроизведение на Mac mini

```sh
cd /Volumes/ArvectumSSD/arvectum/repos/musbread
.venv/bin/python -m unittest tests/test_jodit_mit_cms_migration.py tests/test_build_dependency_sbom.py tests/test_audit_dependency_rights.py tests/test_audit_built_artifacts.py -q
cd apps/cms && php artisan test --compact
cd ../.. && .venv/bin/python scripts/qa_cms_browser.py
.venv/bin/python scripts/build_dependency_sbom.py --verify-generated
```

Все smoke/E2E сценарии выполнены **без передачи пользовательских или музейных ПДн во внешнюю сеть**. До договора и официальной приёмки музея промышленный сайт не меняется, дизайн по решению пользователя остаётся на паузе.
