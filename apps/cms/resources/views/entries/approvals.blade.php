<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <title>Ход одобрений и закрытых выгрузок — MusBread CMS</title>
    <style>
        :root{font:16px/1.55 system-ui,sans-serif;color:#21353f;background:#f3f7f8}
        *{box-sizing:border-box}body{margin:0;padding:1rem}
        main{max-width:1050px;margin:1rem auto 3rem}
        h1{font-size:clamp(1.5rem,3vw,2rem)}h2{font-size:1.2rem}
        a{color:#075c6b}a:focus-visible{outline:3px solid #116c99;outline-offset:3px}
        .notice{background:#eaf3f5;border:1px solid #b3ccd4;border-radius:7px;padding:1rem;margin:1rem 0}
        .warning{background:#fff6e5;border-color:#bd9453}
        .steps{display:flex;gap:.6rem;flex-wrap:wrap;padding-left:1.4rem}
        .steps li{margin:0 .8rem .3rem 0;padding:.15rem}
        .run-list,.approvals{padding:0;list-style:none}
        .run,.approval{background:white;border:1px solid #c9d6dc;border-radius:8px;padding:1rem;margin:.8rem 0;overflow-wrap:anywhere;scroll-margin-top:1rem}
        .run h3,.approval h3{font-size:1.05rem;margin:0 0 .5rem}
        .status{font-weight:650}
        .error{color:#872e18}.success{color:#245f43}.pending{color:#745015}
        .meta{font-size:.9rem;color:#405767}
        .sha{font:12px/1.6 ui-monospace,SFMono-Regular,monospace;word-break:break-all}
        dl{display:grid;grid-template-columns:minmax(7rem,11rem) minmax(0,1fr);gap:.3rem .9rem}
        dt{font-weight:600}dd{margin:0}
        @media(max-width:520px){dl{grid-template-columns:1fr}dd{margin-bottom:.6rem}}
    </style>
</head>
<body>
<main>
    <nav aria-label="Навигация редактора">
        <a href="{{ route('museum.content.preflight') }}">← Предварительная проверка</a>
        · <a href="{{ route('museum.content.compare') }}">Сравнение подготовленных версий</a>
    </nav>
    <h1>Ход одобрений и закрытых выгрузок</h1>
    <div class="notice" role="note">
        <strong>Это внутренняя история CMS, не статус публичного сайта.</strong>
        <p>Сохранённая правка, прохождение проверки, одобрение конкретной редакции,
            регистрация задания и успешная подготовка приватного пакета — <strong>разные этапы</strong>.
            Подготовка закрытого пакета <strong>не является</strong> подтверждением размещения на сайте музея или соблюдения срока в 60 минут.</p>
    </div>
    <nav aria-label="Разделы журнала">
        <a href="#recent-runs">Последние задания выгрузки</a>
        · <a href="#approval-history">История одобрений редакций</a>
    </nav>
    <ol class="steps" aria-label="Порядок работы с материалом">
        <li>Сохранить материал</li>
        <li>Проверить предпросмотр и ошибки</li>
        <li>Администратор одобряет текущую редакцию</li>
        <li>Проверить очередь и результат приватной выгрузки</li>
        <li>Отдельно подтвердить боевое размещение</li>
    </ol>

    <section id="recent-runs" aria-labelledby="runs-title">
        <h2 id="runs-title">Последние задания закрытой выгрузки</h2>
        <p class="meta">Последние 25 записей. Время указано в UTC. Работник очереди может ещё не обработать запрос;
            для диагностики статуса обновите страницу вручную.</p>
        <ol class="run-list">
        @forelse($runs as $run)
            <li class="run" id="run-{{ $run->id }}">
                <h3>Запуск #{{ $run->id }} —
                    <span class="status {{ in_array($run->status, ['failed','abandoned']) ? 'error' : ($run->status === 'succeeded' ? 'success' : 'pending') }}">
                        {{ $runLabels[$run->status] ?? 'Неизвестный статус' }}
                    </span>
                </h3>
                <dl>
                    <dt>Попыток</dt><dd>{{ $run->attempts }}</dd>
                    <dt>Начат (UTC)</dt><dd>{{ $run->started_at?->utc()->format('d.m.Y H:i:s') ?? 'Пока не начат' }}</dd>
                    <dt>Завершён (UTC)</dt><dd>{{ $run->finished_at?->utc()->format('d.m.Y H:i:s') ?? 'Не завершён' }}</dd>
                    @if($run->status === 'succeeded' && $run->snapshot_sha256)
                        <dt>SHA-256 пакета</dt><dd class="sha">{{ $run->snapshot_sha256 }}</dd>
                        @if($run->content_verified_at !== null)
                            <dt>Проверка состава</dt><dd class="success">Подтверждено {{ $run->content_proof_count }} одобренных объектов по содержимому, SHA-256 записей и манифесту</dd>
                            <dt>SHA-256 манифеста</dt><dd class="sha">{{ $run->manifest_sha256 }}</dd>
                        @else
                            <dt>Проверка состава</dt><dd class="pending">Не проводилась (прежний запуск или режим без обязательных одобрений)</dd>
                        @endif
                    @endif
                    @if(in_array($run->status, ['failed','abandoned']))
                        <dt>Техническая причина</dt><dd>{{ $run->error_type ?: 'Не указана. Проверьте закрытый журнал обработчика.' }}</dd>
                    @endif
                </dl>
                @if($run->status === 'failed' || $run->status === 'abandoned')
                    <p class="notice warning" role="status">Приватный пакет не подтверждён как подготовленный. Проверьте очередь и ошибки, прежде чем повторять запрос.</p>
                @elseif($run->status === 'succeeded')
                    <p class="meta">Подготовка файла закончена. Это не доказательство доставки или видимости на публичном домене.</p>
                @endif
            </li>
        @empty
            <li>Запусков закрытой выгрузки пока нет.</li>
        @endforelse
        </ol>
    </section>

    <section id="approval-history" aria-labelledby="approvals-title">
        <h2 id="approvals-title">История одобрений редакций</h2>
        <p class="meta">Последние 100 одобрений; записи не удаляются и не изменяются редакторами.
            Каждое одобрение относится к SHA-256 сохранённой редакции, включая её связанные вложения.
            Если материал позже изменился или удалён, прежнее одобрение остаётся в истории, но не считается новым.</p>
        <ol class="approvals">
        @forelse($journey as $row)
            @php($approval = $row['approval'])
            @php($run = $row['run'])
            <li class="approval" id="approval-{{ $approval->id }}">
                <h3>Одобрение #{{ $approval->id }} · {{ $row['subject_label'] }}</h3>
                <dl>
                    <dt>Одобрено (UTC)</dt>
                    <dd><time datetime="{{ $approval->approved_at->utc()->toIso8601String() }}">{{ $approval->approved_at->utc()->format('d.m.Y H:i:s') }}</time></dd>
                    <dt>Актуальность</dt>
                    <dd class="status {{ str_starts_with($row['revision_status'], 'SHA-256 совпадает') ? 'success' : 'error' }}">{{ $row['revision_status'] }}</dd>
                    <dt>Запрос выгрузки</dt>
                    <dd>{{ $row['dispatch_label'] }}</dd>
                    <dt>Технический запуск</dt>
                    <dd>
                        @if($run)
                            <a href="#run-{{ $run->id }}">Запуск #{{ $run->id }}</a>:
                        @elseif($approval->publication_run_id !== null)
                            #{{ $approval->publication_run_id }}:
                        @endif
                        {{ $row['run_label'] }}
                    </dd>
                    <dt>Включение в пакет</dt>
                    <dd>
                        @if($row['included_proof'])
                            <strong class="success">Подтверждено в проверенном пакете</strong>
                            (запуск #{{ $row['included_proof']->publication_run_id }}).
                            <span class="meta">SHA-256 экспортированной записи:</span>
                            <code class="sha">{{ $row['included_proof']->export_record_sha256 }}</code>
                        @else
                            <span class="pending">Не подтверждено для связанного запуска</span>
                            <span class="meta">(ожидание, неудача, неподтверждённый состав или пакет другого запуска)</span>
                        @endif
                    </dd>
                    <dt>SHA-256 редакции</dt><dd class="sha">{{ $approval->revision_sha256 }}</dd>
                </dl>
                @if($run && $run->status === 'succeeded')
                    <p class="meta">Успешный запуск свидетельствует о приватной выгрузке.
                        Он сам по себе не подтверждает, что именно эта одобренная редакция вошла в пакет, особенно если запросы объединялись.</p>
                @endif
            </li>
        @empty
            <li>Одобрений пока нет. Проверка содержимого и сохранение редактором не создают одобрение автоматически.</li>
        @endforelse
        </ol>
    </section>
</main>
</body>
</html>
