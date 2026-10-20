<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Конфликт редактирования — Музей Хлеба</title>
  <style>
    :root {font: 16px/1.5 system-ui,-apple-system,sans-serif; color-scheme:light; background:#f6f7fa; color:#1f2937;}
    * {box-sizing:border-box}
    body {margin:0; padding:clamp(1rem,3vw,2rem)}
    main {max-width:1100px; margin:auto}
    h1 {font-size:clamp(1.35rem,3vw,2rem);line-height:1.2}
    h2 {font-size:1.15rem}
    .notice {padding:1rem 1.25rem; background:#fff4e5; border-left:4px solid #ae5700; border-radius:6px}
    .actions {display:flex; gap:.75rem; flex-wrap:wrap; margin:1rem 0}
    .action {border:2px solid #35426d; border-radius:7px; padding:.7rem 1rem; background:#fff; color:#172554;
      text-decoration:none; cursor:pointer; font:inherit; font-weight:600}
    .action.primary {background:#172554;color:#fff}
    .action:focus-visible,textarea:focus-visible {outline:3px solid #f59e0b;outline-offset:2px}
    .field {margin:1.5rem 0; padding:1rem; border:1px solid #d6dbe4; border-radius:8px;background:white}
    .field.changed {border-left:4px solid #ac6200}
    .columns {display:grid;grid-template-columns:1fr 1fr; gap:1rem}
    .col-heading {font-weight:700;margin-bottom:.5rem}
    textarea {display:block;width:100%;min-height:7rem;padding:.75rem;border:1px solid #6b7280;
      border-radius:5px;background:#fcfcfd; color:inherit;font:13px/1.6 ui-monospace,SFMono-Regular,Consolas,monospace;
      resize:vertical}
    textarea.long {min-height:14rem}
    .muted {color:#444b57}
    .changed-mark {font-size:.85rem;color:#814500;font-weight:700}
    #copy-status {min-height:1.6em}
    @media(max-width:700px){.columns{grid-template-columns:1fr}}
    @media print {.actions {display:none} textarea {overflow:visible}}
  </style>
  <script defer src="{{ asset('js/museum-editor-conflict.js') }}"></script>
</head>
<body>
<main>
  <h1>Другой редактор изменил материал</h1>
  <div class="notice" role="alert">
    <p><strong>Ваша правка не перезаписана и не опубликована.</strong></p>
    <p>{{ $explanation }}</p>
    <p>Для каждого поля показаны ваш несохранённый вариант и актуальная редакция.
       Скопируйте нужные фрагменты или сохраните черновик на своё устройство, прежде чем закрыть страницу.</p>
  </div>
  <p class="muted">Материал: <strong>{{ $entry->title }}</strong>. Сравнение доступно только в этом ответе;
     мы не записываем ваш несохранённый черновик в базу или в постоянное хранилище браузера.</p>
  <nav class="actions" aria-label="Действия при конфликте">
    <button type="button" class="action primary" id="download-draft">Сохранить мой черновик (.json)</button>
    <a class="action" href="{{ $editorUrl }}" target="_blank" rel="noopener noreferrer">Открыть актуальную редакцию в новой вкладке</a>
  </nav>
  <p id="copy-status" role="status" aria-live="polite"></p>
  <h2>Сравнение полей</h2>
  @foreach ($fields as $field)
    <section class="field {{ $field['different'] ? 'changed' : '' }}" aria-labelledby="field-label-{{ $field['key'] }}">
      <h3 id="field-label-{{ $field['key'] }}">{{ $field['label'] }}
        @if ($field['different'])
          <span class="changed-mark">(отличается)</span>
        @endif
      </h3>
      <div class="columns">
        <div>
          <div class="col-heading" id="draft-label-{{ $field['key'] }}">Мой несохранённый вариант</div>
          <textarea class="{{ in_array($field['key'], ['body','body_en']) ? 'long' : '' }}"
                    id="draft-{{ $field['key'] }}" data-conflict-draft="{{ $field['key'] }}"
                    aria-labelledby="field-label-{{ $field['key'] }} draft-label-{{ $field['key'] }}"
                    readonly>{{ $field['submitted'] }}</textarea>
          <button type="button" class="action" data-copy-draft="{{ $field['key'] }}">Скопировать моё поле</button>
        </div>
        <div>
          <div class="col-heading" id="current-label-{{ $field['key'] }}">Текущая редакция</div>
          <textarea class="{{ in_array($field['key'], ['body','body_en']) ? 'long' : '' }}"
                    aria-labelledby="field-label-{{ $field['key'] }} current-label-{{ $field['key'] }}"
                    readonly>{{ $field['current'] }}</textarea>
        </div>
      </div>
    </section>
  @endforeach
  <p class="muted">Если изменения касаются связанных изображений или документов, откройте актуальную редакцию
    и проверьте их отдельно. Автоматического объединения и перезаписи здесь нет.</p>
</main>
</body>
</html>
