<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="robots" content="noindex,nofollow">
    <title>Медиатека — MusBread CMS</title>
    <style>
        :root { color-scheme: light; font: 16px/1.5 system-ui,sans-serif; color:#202a33; background:#f5f7f8; }
        * { box-sizing:border-box; }
        body { margin:0; }
        header { background:#1d2935; color:#fff; padding:1rem max(1rem,calc((100% - 1080px)/2)); display:flex; align-items:center; justify-content:space-between; gap:1rem; }
        header a { color:#fff; }
        main { max-width:1080px; margin:2rem auto; padding:0 1rem 4rem; }
        h1 { margin-top:0; }
        .panel { background:#fff; border:1px solid #d8e0e4; border-radius:14px; padding:1.4rem; margin-bottom:1.5rem; }
        label { display:block; font-weight:600; margin:.75rem 0 .25rem; }
        input:not([type=hidden]), select { font:inherit; width:100%; padding:.65rem; border:1px solid #8c9ba6; border-radius:8px; background:#fff; }
        input:focus-visible,select:focus-visible,button:focus-visible,a:focus-visible { outline:3px solid #168d97; outline-offset:3px; }
        .drop { border:2px dashed #738d99; border-radius:10px; padding:1.4rem; background:#f5fafa; text-align:center; }
        .drop.drag { border-color:#007d83; background:#e1f5f4; }
        .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(235px,1fr)); gap:1rem; }
        .item { background:white; border:1px solid #d8e0e4; border-radius:12px; overflow:hidden; }
        .item img { display:block; width:100%; height:170px; object-fit:cover; background:#f5f5f5; }
        .item-body { padding:1rem; overflow-wrap:anywhere; }
        .meta { color:#566575; font-size:.84rem; }
        button { font:inherit; background:#056a70; color:white; border:0; border-radius:8px; padding:.7rem 1.3rem; cursor:pointer; margin-top:1rem; }
        .notice { padding:1rem; border:1px solid #0f7272; background:#e9f8f5; border-radius:8px; }
        .error { color:#922b26; }
        .danger { background:#8c2b22; margin-top:.5rem; padding:.4rem .7rem; }
        .small { font-size:.9rem; }
        @media(max-width:650px){main{margin:1rem auto}.panel{padding:1rem}header{flex-wrap:wrap}}
    </style>
</head>
<body>
<header>
    <strong>MusBread · Медиатека (закрытый контур)</strong>
    <a href="/admin">← Вернуться в MoonShine</a>
</header>
<main>
    <h1>Изображения материалов</h1>
    <p><a href="{{ route('museum.documents.index') }}">К библиотеке PDF/DOCX/XLSX →</a></p>
    <p>Файлы до 5 МБ: JPG, PNG, WebP, GIF (только первый кадр, без анимации). Изображение привязывается к странице или новости. EXIF и другие метаданные удаляются при перекодировании в WebP. Файлы в черновиках не попадают на публичный сайт.</p>
    @if(session('status')) <p role="status" class="notice">{{ session('status') }}</p> @endif
    @if($errors->any())
        <div role="alert" class="panel error">
            <strong>Файл не добавлен:</strong>
            <ul>@foreach ($errors->all() as $error)<li>{{ $error }}</li>@endforeach</ul>
        </div>
    @endif
    <section class="panel" aria-labelledby="new-media">
        <h2 id="new-media">Добавить изображение</h2>
        <form method="post" action="{{ route('museum.media.store') }}" enctype="multipart/form-data">
            @csrf
            <label for="entry">Материал музея *</label>
            <select id="entry" name="museum_entry_id" required>
                <option value="">Выберите материал</option>
                @foreach($entries as $entry)
                    <option value="{{ $entry->id }}" @selected(old('museum_entry_id') == $entry->id)>
                        {{ $entry->title }} ({{ $entry->slug }}, {{ $entry->status }})
                    </option>
                @endforeach
            </select>
            <label for="alt">Описание изображения (alt) *</label>
            <input id="alt" name="alt" required minlength="3" maxlength="255" value="{{ old('alt') }}" placeholder="Например: историческая печь в экспозиции музея">
            <label for="caption">Подпись под изображением</label>
            <input id="caption" name="caption" maxlength="255" value="{{ old('caption') }}">
            <label for="image">Изображение *</label>
            <div class="drop" id="drop">
                <p>Перетащите изображение сюда или выберите файл</p>
                <input id="image" name="image" type="file" accept="image/png,image/jpeg,image/webp,image/gif" required>
            </div>
            <button type="submit">Загрузить изображение</button>
        </form>
    </section>
    <section aria-labelledby="media-list">
        <h2 id="media-list">Загруженные изображения ({{ $media->total() }})</h2>
        @if($media->isEmpty())
            <p>Здесь пока нет изображений.</p>
        @else
            <div class="grid">
            @foreach($media as $item)
                <article class="item">
                    <img loading="lazy" src="{{ route('museum.media.preview', $item) }}" alt="{{ $item->alt }}">
                    <div class="item-body">
                        <strong>{{ $item->alt }}</strong>
                        @if($item->caption)<p class="small">{{ $item->caption }}</p>@endif
                        <p class="meta">Материал: {{ $item->entry?->title ?? 'Удалён' }}
                            ({{ $item->entry?->status ?? 'нет' }})</p>
                        <p class="meta">{{ $item->width }}×{{ $item->height }} · {{ round($item->size_bytes/1024) }} КБ</p>
                        <form method="post" action="{{ route('museum.media.update', $item) }}">
                            @csrf @method('PATCH')
                            <label for="edit-alt-{{ $item->id }}">Alt-текст</label>
                            <input id="edit-alt-{{ $item->id }}" name="alt" required minlength="3" maxlength="255" value="{{ $item->alt }}">
                            <label for="edit-caption-{{ $item->id }}">Подпись</label>
                            <input id="edit-caption-{{ $item->id }}" name="caption" maxlength="255" value="{{ $item->caption }}">
                            <label for="edit-entry-{{ $item->id }}">Привязать к материалу</label>
                            <select id="edit-entry-{{ $item->id }}" name="museum_entry_id" required>
                                @foreach($entries as $entry)
                                    <option value="{{ $entry->id }}" @selected($entry->id === $item->museum_entry_id)>{{ $entry->title }} ({{ $entry->status }})</option>
                                @endforeach
                            </select>
                            <button type="submit">Сохранить</button>
                        </form>
                        <form method="post" action="{{ route('museum.media.destroy', $item) }}" onsubmit="return confirm('Удалить изображение? В следующей публикации оно исчезнет с публичного сайта.')">
                            @csrf @method('DELETE')
                            <button class="danger" type="submit">Удалить</button>
                        </form>
                    </div>
                </article>
            @endforeach
            </div>
            <div style="margin-top:1.5rem">{{ $media->links() }}</div>
        @endif
    </section>
</main>
<script>
(() => {
    const drop = document.getElementById('drop');
    const input = document.getElementById('image');
    for (const name of ['dragenter','dragover']) drop.addEventListener(name, event => {
        event.preventDefault(); drop.classList.add('drag');
    });
    for (const name of ['dragleave','drop']) drop.addEventListener(name, event => {
        event.preventDefault(); drop.classList.remove('drag');
    });
    drop.addEventListener('drop', event => {
        const files = event.dataTransfer?.files;
        if (files?.length) input.files = files;
    });
})();
</script>
</body>
</html>
