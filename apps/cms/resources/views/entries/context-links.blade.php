<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>Выбор контекстной ссылки — CMS Музея хлеба</title>
  <style>
    :root{font:16px/1.5 system-ui,sans-serif;color:#192b32;background:#f5f7f8}
    *{box-sizing:border-box}body{margin:0}header{background:#172b35;color:white;padding:1rem max(1rem,calc((100% - 1080px)/2))}
    header a{color:#fff}main{max-width:1080px;margin:auto;padding:1rem 1rem 3rem}
    .intro{background:#e7f1ee;padding:1.1rem;border-left:4px solid #0b655e}
    .grid{display:grid;gap:.8rem;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));margin-top:1.2rem}
    article{background:#fff;border:1px solid #bccdd0;border-radius:.3rem;padding:1rem;min-width:0}
    label{display:block;margin:.7rem 0 .25rem;font-weight:650}
    input{font:inherit;width:100%;padding:.5rem;border:1px solid #627a81;border-radius:.25rem}
    input:focus-visible,a:focus-visible{outline:3px solid #0757cf;outline-offset:3px}
    h2{font-size:1.05rem;line-height:1.35;margin:0;overflow-wrap:anywhere}
    small{font-size:.82rem;color:#405159}
  </style>
</head>
<body>
<header><a href="/admin">← В MoonShine</a></header>
<main>
  <h1>Контекстные ссылки на опубликованные материалы</h1>
  <p class="intro">Показаны только материалы и события, доступные в следующей статической выгрузке.
    В черновиках и закрытых разделах сведения не раскрываются. Выделите URL из поля, скопируйте и
    вставьте в команду <strong>«Ссылка»</strong> редактора Jodit, выделив осмысленный фрагмент
    текста публикации. Здесь ничего не изменяется автоматически.</p>
  @if($links->isEmpty())
    <p role="status">Подходящих опубликованных материалов пока нет. Сначала подготовьте и утвердите публикации.</p>
  @else
    <p role="status">Доступных адресов: {{ $links->count() }}. Адреса не раскрывают черновики.</p>
    <div class="grid">
      @foreach($links as $item)
        <article>
          <h2>{{ $item['title'] }}</h2>
          <small>{{ $item['type'] }}</small>
          <label for="link-{{ $loop->index }}">Внутренняя ссылка</label>
          <input id="link-{{ $loop->index }}" type="text" readonly
             value="{{ $item['url'] }}" aria-label="URL публикации {{ $item['title'] }}">
        </article>
      @endforeach
    </div>
  @endif
  <p>Перед выпуском используйте <a href="{{ route('museum.content.preflight') }}">проверку ссылок и готовности материалов</a>.
    Смысловую уместность связей и тексты утверждает редактор музея.</p>
</main>
</body>
</html>
