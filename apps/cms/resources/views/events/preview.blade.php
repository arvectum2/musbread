<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <title>Предпросмотр события: {{ $event->title }} — MusBread CMS</title>
    <style>
        :root{color-scheme:light;font:16px/1.65 system-ui,sans-serif;color:#26323a;background:#f3f7f8}
        *{box-sizing:border-box}body{margin:0}header{padding:1rem max(1rem,calc((100% - 820px)/2));background:#1c3941;color:white}
        main{max-width:820px;margin:2rem auto;padding:0 1rem 3rem}
        article{padding:2rem;background:white;border:1px solid #d3dfe4;border-radius:14px;overflow-wrap:anywhere}
        h1{line-height:1.2}a{color:#086c75}a:focus-visible{outline:3px solid #007b85;outline-offset:3px}
        .notice{background:#fff8dc;border:2px solid #80621a;border-radius:9px;padding:1rem;margin-bottom:1.5rem}
        .meta{color:#4e5d65}article p{max-width:75ch}
        @media(max-width:650px){main{margin:1rem auto}article{padding:1.2rem}}
    </style>
</head>
<body>
<header><strong>MusBread · Закрытый предпросмотр события</strong></header>
<main>
    <aside class="notice" aria-label="Статус предпросмотра">
        <strong>Сохранённая версия события, только для редактора. Это не публичная страница.</strong>
        <p>Статус в CMS: {{ $event->status === 'draft' ? 'Черновик' : 'Помечен к публикации' }}.
            @if($event->published_at) Дата публикации: {{ $event->published_at->format('d.m.Y H:i') }}. @endif</p>
    </aside>
    <article>
        <p class="meta">{{ $event->category }} · Дата события: {{ $event->starts_at?->format('d.m.Y') ?? 'не назначена' }}</p>
        <h1>{{ $event->title }}</h1>
        @if($event->excerpt)<p class="meta">{{ $event->excerpt }}</p>@endif
        <div class="museum-preview-body">{!! $cleanBody !!}</div>
    </article>
</main>
</body>
</html>
