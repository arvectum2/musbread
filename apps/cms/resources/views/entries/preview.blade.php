<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <title>Предпросмотр: {{ $entry->title }} — MusBread CMS</title>
    <style>
        :root{color-scheme:light;font:16px/1.65 system-ui,sans-serif;color:#26323a;background:#f3f7f8}
        *{box-sizing:border-box}body{margin:0}header{padding:1rem max(1rem,calc((100% - 820px)/2));background:#1c3941;color:white}
        header a{color:white}main{max-width:820px;margin:2rem auto;padding:0 1rem 3rem}
        article{padding:2rem;background:white;border:1px solid #d3dfe4;border-radius:14px;overflow-wrap:anywhere}
        h1{line-height:1.2;margin-top:.25rem}h2,h3{line-height:1.3}a{color:#086c75}
        a:focus-visible{outline:3px solid #007b85;outline-offset:3px}
        .notice{background:#fff8dc;border:2px solid #80621a;border-radius:9px;padding:1rem;margin-bottom:1.5rem}
        .meta{color:#4e5d65}article p{max-width:75ch}blockquote{border-left:4px solid #879ea5;padding-left:1rem;margin-left:0}
        @media(max-width:650px){main{margin:1rem auto}article{padding:1.2rem}}
    </style>
</head>
<body>
<header><strong>MusBread · Закрытый предпросмотр</strong>
    <p><a href="/admin/resource/museum-entry-resource/museum-entry-form-page/{{ $entry->id }}">← Вернуться к редактированию материала</a></p>
</header>
<main>
    <aside class="notice" aria-label="Статус предпросмотра">
        <strong>Только для редактора. Это сохранённая версия материала, а не публичная страница.</strong>
        <p>Статус в CMS: {{ $entry->status === 'draft' ? 'Черновик' : 'Помечен к публикации' }}.
            @if($entry->published_at) Дата публикации: {{ $entry->published_at->format('d.m.Y H:i') }}. @endif
            Изменения в открытой форме редактора необходимо сначала сохранить.</p>
    </aside>
    <nav class="notice" aria-label="Дальнейшие действия редактора">
        <strong>Следующие шаги</strong>
        <p><a href="{{ route('museum.media.index', ['entry' => $entry->id]) }}">Проверить изображения</a>
            · <a href="{{ route('museum.documents.index', ['entry' => $entry->id]) }}">Проверить документы</a>
            · <a href="{{ route('museum.content.preflight') }}#entry-{{ $entry->id }}">Проверить готовность к закрытой выгрузке</a></p>
        <p class="meta">Предпросмотр не публикует материал. После проверки уполномоченный сотрудник отдельно одобряет редакцию для закрытой выгрузки.</p>
    </nav>
    <article aria-labelledby="preview-title">
        <p class="meta">{{ \App\Models\MuseumEntry::TYPES[$entry->type] ?? 'Материал музея' }}</p>
        <h1 id="preview-title">{{ $entry->h1 ?: $entry->title }}</h1>
        @if($entry->excerpt)<p class="meta">{{ $entry->excerpt }}</p>@endif
        <div class="museum-preview-body">{!! $cleanBody !!}</div>
    </article>
</main>
</body>
</html>
