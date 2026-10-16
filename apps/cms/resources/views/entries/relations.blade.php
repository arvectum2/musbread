<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <title>Связанные материалы: {{ $entry->title }} — MusBread CMS</title>
    <style>
        :root{font:16px/1.5 system-ui,sans-serif;background:#f3f6f8;color:#202b33}
        *{box-sizing:border-box}body{margin:0}header{background:#1b3440;color:#fff;padding:1rem max(1rem,calc((100% - 800px)/2))}
        header a{color:#fff}main{max-width:800px;margin:2rem auto;padding:0 1rem 3rem}
        form{background:#fff;padding:1.5rem;border-radius:12px;border:1px solid #cdd8df}
        fieldset{border:1px solid #b5c4cc;border-radius:8px;padding:1rem;margin:1rem 0}
        legend{font-weight:700}label{display:block;margin-bottom:.35rem}select{font:inherit;width:100%;padding:.5rem;min-height:10rem}
        button{font:inherit;font-weight:650;background:#00676e;color:#fff;padding:.7rem 1.3rem;border:0;border-radius:6px;cursor:pointer}
        button:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid #1478ae;outline-offset:3px}
        .notice{background:#edf8ee;padding:1rem;border:1px solid #207246;border-radius:7px}
        .error{background:#fff1ef;padding:1rem;border:1px solid #b53c30;border-radius:7px}
        .muted{color:#455660}small{display:block;margin-top:.3rem}
    </style>
</head>
<body>
<header><strong>MusBread · Связи материалов (закрытый контур)</strong>
    <p><a href="/admin">← К административной панели</a></p>
</header>
<main>
    <h1>Связанные материалы</h1>
    <p><strong>{{ $entry->title }}</strong> · {{ $entry->type }} · {{ $entry->status }}</p>
    <p class="muted">Можно связать новость, страницу, экскурсию, выставку или страницу документа с другими материалами и событиями афиши. Отметьте нужные объекты (Ctrl/Cmd + нажатие для нескольких вариантов). Пустой выбор удаляет прежние связи.</p>
    @if(session('status'))<p role="status" class="notice">{{ session('status') }}</p>@endif
    @if($errors->any())<div role="alert" class="error"><strong>Связи не сохранены</strong><ul>@foreach($errors->all() as $error)<li>{{ $error }}</li>@endforeach</ul></div>@endif
    <form method="post" action="{{ route('museum.entries.relations.update', ['entry' => $entry->id]) }}">
        @csrf
        @method('PUT')
        <fieldset>
            <legend>Связанные страницы, экскурсии, выставки и документы</legend>
            <label for="related-entries">Материалы из доступных вам разделов</label>
            <select id="related-entries" name="related_entry_ids[]" multiple size="9">
                @foreach($editable as $candidate)
                    <option value="{{ $candidate->id }}" @selected(in_array($candidate->id, old('related_entry_ids', $selectedEntries)))>{{ $candidate->title }} ({{ $candidate->type }})</option>
                @endforeach
            </select>
            <small>Связанный документ отображается как ссылка на страницу с прикреплённым файлом, не как прямой доступ к закрытому хранилищу.</small>
        </fieldset>
        <fieldset>
            <legend>События афиши</legend>
            <label for="related-events">Связанные анонсы событий</label>
            <select id="related-events" name="related_event_ids[]" multiple size="7">
                @foreach($events as $candidate)
                    <option value="{{ $candidate->id }}" @selected(in_array($candidate->id, old('related_event_ids', $selectedEvents)))>{{ $candidate->title }} ({{ $candidate->category }})</option>
                @endforeach
            </select>
        </fieldset>
        <button type="submit">Сохранить связи</button>
    </form>
</main>
</body>
</html>
