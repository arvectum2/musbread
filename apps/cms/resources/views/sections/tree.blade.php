<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <title>Дерево разделов — MusBread CMS</title>
    <style>
        :root{color-scheme:light;font:16px/1.5 system-ui,sans-serif;color:#22323b;background:#f3f6f8}
        *{box-sizing:border-box}body{margin:0}
        header{background:#193643;color:white;padding:1rem max(1rem,calc((100% - 1100px)/2))}
        header a{color:white}main{max-width:1100px;margin:1.7rem auto;padding:0 1rem 4rem}
        h1{margin:.2rem 0}h2{font-size:1.1rem;margin:0}a{color:#056272}
        a:focus-visible,button:focus-visible{outline:3px solid #147ac7;outline-offset:3px}
        .stats{display:flex;flex-wrap:wrap;gap:.6rem;margin:1.2rem 0}
        .stats span{background:white;border:1px solid #c1ced4;padding:.4rem .7rem;border-radius:6px}
        .hint{color:#455660;max-width:75ch}
        .tree{list-style:none;padding:0;margin:1.2rem 0}
        .tree>li{background:white;border:1px solid #cad6dd;border-inline-start:4px solid #7b979f;margin:.35rem 0;padding:.65rem .8rem;border-radius:5px}
        .tree>li.visible{border-inline-start-color:#168052}
        .tree>li.blocked{border-inline-start-color:#a36b16;background:#fff9ea}
        .tree>li.draft{border-inline-start-color:#687582;background:#f9fafb}
        .info{display:flex;flex-wrap:wrap;gap:.5rem;align-items:baseline}
        .name{font-weight:700}.meta{font-size:.83rem;color:#4c5e67}
        .status{font-weight:650;font-size:.82rem;border:1px solid #86969d;border-radius:5px;padding:.1rem .4rem}
        .row-actions{display:flex;align-items:center;flex-wrap:wrap;gap:.75rem;margin-top:.35rem}
        .row-actions form{display:inline}.row-actions button{font:inherit;font-size:.85rem;cursor:pointer;color:#035d6d;background:white;border:1px solid #8398a1;border-radius:5px;padding:.25rem .6rem}
        .row-actions button:disabled{opacity:.42;cursor:not-allowed}
        .notice{background:#eef9f0;border:1px solid #147f47;padding:.7rem;border-radius:6px}
        .empty{padding:2rem;background:white;border:1px solid #c1ced4}
        @media(max-width:650px){main{padding:0 .65rem 2rem}.tree>li{padding:.55rem}.row-actions{gap:.45rem}}
    </style>
</head>
<body>
<header>
    <strong>MusBread · Дерево разделов (закрытая CMS)</strong>
    <p><a href="/admin/resource/museum-section-resource/museum-section-index-page">← К таблице разделов MoonShine</a></p>
</header>
<main>
    <h1>Карта структуры сайта</h1>
    <p class="hint">Разделы упорядочены с учётом родителя и поля «Порядок». Изменения вступят в публичную версию только после отдельной проверенной публикации. Права редакторов на дочерние разделы не наследуются.</p>
    <div class="stats" aria-label="Сводка структуры">
        <span>Всего разделов: <strong>{{ $total }}</strong></span>
        <span>Видно на сайте: <strong>{{ $visible }}</strong></span>
        <span>Черновиков: <strong>{{ $draft }}</strong></span>
        <span>Скрыто предком: <strong>{{ $blocked }}</strong></span>
        <span>Публикуемых материалов: <strong>{{ $visibleEntries }}</strong></span>
    </div>
    @if(session('status'))<p role="status" class="notice">{{ session('status') }}</p>@endif
    @if($total === 0)
        <p class="empty">Разделы ещё не созданы. Добавьте первый раздел через таблицу MoonShine.</p>
    @else
        <ol class="tree" aria-label="Иерархия разделов">
        @foreach($rows as $row)
            @php($section = $row['section'])
            <li class="{{ $row['status'] }}" style="margin-inline-start:{{ min($row['depth'] * 1.2, 12) }}rem" data-section="{{ $section->slug }}" data-depth="{{ $row['depth'] }}">
                <div class="info">
                    <span class="name">{{ $section->title }}</span>
                    <span class="meta">/{{ $section->slug }}/ · уровень {{ $row['depth'] + 1 }}</span>
                    @if($row['status'] === 'visible')<span class="status">Опубликован</span>
                    @elseif($row['status'] === 'blocked')<span class="status">Скрыт неопубликованным предком</span>
                    @else<span class="status">Черновик</span>@endif
                </div>
                <div class="meta">Материалов: {{ $section->entries_count }} · Публикуемых: {{ $row['visible_entries'] }} · Назначенных редакторов: {{ $section->editors_count }} · Порядок: {{ $section->sort_order }}</div>
                <div class="row-actions">
                    <a href="/admin/resource/museum-section-resource/museum-section-form-page/{{ $section->id }}">Редактировать раздел</a>
                    <form method="post" action="{{ route('museum.sections.reorder', ['section' => $section->id]) }}">
                        @csrf
                        <input type="hidden" name="direction" value="up">
                        <button type="submit" aria-label="Поднять раздел {{ $section->title }} среди соседних" @disabled(! $row['can_move_up'])>↑ Выше</button>
                    </form>
                    <form method="post" action="{{ route('museum.sections.reorder', ['section' => $section->id]) }}">
                        @csrf
                        <input type="hidden" name="direction" value="down">
                        <button type="submit" aria-label="Опустить раздел {{ $section->title }} среди соседних" @disabled(! $row['can_move_down'])>↓ Ниже</button>
                    </form>
                </div>
            </li>
        @endforeach
        </ol>
    @endif
</main>
</body>
</html>
