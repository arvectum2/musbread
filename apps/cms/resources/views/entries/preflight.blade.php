<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <title>Проверка материалов и событий перед публикацией — MusBread CMS</title>
    <style>
        :root{font:16px/1.5 system-ui,sans-serif;color:#20323e;background:#f4f7f8}
        *{box-sizing:border-box}body{margin:0}header{background:#193642;padding:1rem max(1rem,calc((100% - 1050px)/2));color:#fff}
        header a{color:#fff}main{max-width:1050px;margin:2rem auto;padding:0 1rem 4rem}
        h1{margin:0 0 .5rem}h2{font-size:1.15rem;margin:0}a{color:#06616c}
        a:focus-visible{outline:3px solid #1877ad;outline-offset:3px}
        .intro{max-width:70ch;color:#435966}.stats{display:flex;flex-wrap:wrap;gap:.65rem;margin:1.4rem 0}
        .stats span{background:#fff;padding:.5rem .8rem;border:1px solid #ced9dd;border-radius:6px}
        .record{padding:1.15rem;background:#fff;border:1px solid #c8d6dd;border-radius:9px;margin:1rem 0;scroll-margin-top:1rem}
        .record h3{font-size:1.1rem;margin:0}.record.has-errors{border-inline-start:4px solid #b34435}.record.has-warnings{border-inline-start:4px solid #a16b15}
        .meta{font-size:.88rem;color:#52616a}.actions{display:flex;gap:1rem;flex-wrap:wrap;margin:.55rem 0}
        .issues{padding-left:1.5rem;margin:.65rem 0}.issues li{padding:.3rem .1rem}
        .issue-error{color:#8a2517}.issue-warning{color:#6c4b14}
        .state{font-weight:650}code{font-size:.92em;background:#eef2f5;padding:.1rem .3rem;border-radius:3px}
        .notice{padding:.8rem 1rem;background:#f0f5fc;border:1px solid #98aec5;border-radius:5px}
        @media(max-width:700px){main{margin:1rem auto}.record{padding:.8rem}}
    </style>
</head>
<body>
<header><strong>MusBread · Закрытый редакторский контур</strong>
    <p><a href="/admin/resource/museum-entry-resource/museum-entry-index-page">← К материалам музея</a></p>
</header>
<main>
    <h1>Проверка перед публикацией</h1>
    <p><a href="{{ route('museum.content.compare') }}">Сравнить версии перед выпуском →</a> · <a href="#events-check">К проверке событий афиши ↓</a></p>
    <p class="intro">Это предварительная проверка сохранённых записей и файлов. Она ничего не публикует и не изменяет. «Готово к экспорту» означает доступность записи для следующей выгрузки, а не подтверждение её размещения на сайте музея.</p>
    @if(session('museum_export_queue_result'))
    <p role="status" class="notice">{{ session('museum_export_queue_result') }}</p>
    @endif
    @if($mayRequestExport)
    <section aria-label="Подготовка выгрузки по кнопке">
        <h2>Публикация по событию</h2>
        <p class="intro">Кнопка запускает <strong>только подготовку закрытой выгрузки CMS</strong>. Она не отправляет пакет на публичные серверы музея и не заменяет формального согласования.</p>
        @if($exportQueueConfigured && $report['errors'] === 0)
        <form method="post" action="{{ route('museum.content.queue-publication') }}">
            @csrf
            <button type="submit">Опубликовать — подготовить пакет в очереди</button>
        </form>
        @else
        <p role="status" class="notice">Запуск выгрузки недоступен: {{ !$exportQueueConfigured ? 'постоянная очередь не настроена.' : 'есть критические ошибки в готовых материалах.' }}</p>
        @endif
    </section>
    @endif
    <div class="stats" aria-label="Итог проверки">
        <span>Доступных записей: <strong>{{ $report['total'] }}</strong></span>
        <span>Готовы к выгрузке: <strong>{{ $report['ready'] }}</strong></span>
        <span>Критических ошибок готовых записей: <strong>{{ $report['errors'] }}</strong></span>
        <span>Событий афиши: <strong>{{ $report['events_total'] }}</strong></span>
        <span>Событий к выгрузке: <strong>{{ $report['events_ready'] }}</strong></span>
        <span>Критических ошибок готовых событий: <strong>{{ $report['event_errors'] }}</strong></span>
        <span>Всех предупреждений: <strong>{{ $report['warnings'] }}</strong></span>
    </div>
    <p class="notice">Ошибки в черновиках можно исправить до назначения публикации. Для окончательной проверки из терминала: <code>php artisan museum:preflight --strict</code>. Строгий экспорт <code>museum:export --preflight-strict</code> останавливается до записи файлов при критических ошибках в готовых записях.</p>
    <h2>Материалы и страницы</h2>
    @forelse($report['records'] as $record)
        <article id="entry-{{ $record['id'] }}" class="record @if($record['error_count'] > 0)has-errors @elseif($record['warning_count'] > 0)has-warnings @endif">
            <h2>{{ $record['title'] ?: 'Без названия' }}</h2>
            <p class="meta">{{ \App\Models\MuseumEntry::TYPES[$record['type']] ?? 'Неизвестный тип' }} · <code>{{ $record['slug'] }}</code> · {{ $record['section'] ?? 'Без раздела' }}</p>
            <p><span class="state">{{ \App\Support\MuseumEntryPublicationState::OPTIONS[$record['state']] ?? $record['state'] }}</span>
                · Ошибок: {{ $record['error_count'] }} · Предупреждений: {{ $record['warning_count'] }}</p>
            <nav class="actions" aria-label="Действия над материалом">
                <a href="/admin/resource/museum-entry-resource/museum-entry-form-page/{{ $record['id'] }}">Исправить в CMS</a>
                <a href="{{ route('museum.entries.preview', ['entry' => $record['id']]) }}">Предпросмотр</a>
                <a href="{{ route('museum.entries.relations.edit', ['entry' => $record['id']]) }}">Связи</a>
            </nav>
            @if($record['issues'] === [])
                <p>Автоматическая проверка замечаний не обнаружила.</p>
            @else
                <ul class="issues">
                @foreach($record['issues'] as $issue)
                    <li class="issue-{{ $issue['level'] }}"><strong>{{ $issue['level'] === 'error' ? 'Ошибка' : 'Рекомендация' }}:</strong> {{ $issue['message'] }}</li>
                @endforeach
                </ul>
            @endif
        </article>
    @empty
        <p>В доступных вам разделах пока нет материалов для проверки.</p>
    @endforelse
    <h2 id="events-check">События афиши</h2>
    <p class="intro">Здесь отображаются события, доступные вам в существующем редакторе «События». Связанные неопубликованные страницы отмечаются без раскрытия их названий.</p>
    @forelse($report['events'] as $record)
        <article id="event-{{ $record['id'] }}" class="record @if($record['error_count'] > 0)has-errors @elseif($record['warning_count'] > 0)has-warnings @endif">
            <h3>{{ $record['title'] ?: 'Без названия' }}</h3>
            <p class="meta">{{ $record['category'] ?: 'Без категории' }} · {{ $record['starts_at'] ?? 'Без даты' }} · <code>{{ $record['slug'] }}</code></p>
            <p><span class="state">{{ \App\Support\MuseumEntryPublicationState::OPTIONS[$record['state']] ?? $record['state'] }}</span>
                · Ошибок: {{ $record['error_count'] }} · Предупреждений: {{ $record['warning_count'] }}</p>
            <nav class="actions" aria-label="Действия над событием">
                <a href="/admin/resource/museum-event-resource/museum-event-form-page/{{ $record['id'] }}">Исправить событие</a>
                <a href="{{ route('museum.events.preview', ['event' => $record['id']]) }}">Предпросмотр события</a>
            </nav>
            @if($record['issues'] === [])
                <p>Автоматическая проверка замечаний не обнаружила.</p>
            @else
                <ul class="issues">
                @foreach($record['issues'] as $issue)
                    <li class="issue-{{ $issue['level'] }}"><strong>{{ $issue['level'] === 'error' ? 'Ошибка' : 'Рекомендация' }}:</strong> {{ $issue['message'] }}</li>
                @endforeach
                </ul>
            @endif
        </article>
    @empty
        <p>События афиши пока не созданы.</p>
    @endforelse
</main>
</body>
</html>
