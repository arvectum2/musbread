<!doctype html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <title>Журнал одобрений — закрытая CMS музея</title>
    <style>
        :root{font:16px/1.5 system-ui,sans-serif;color:#21353f;background:#f3f7f8}
        body{max-width:1000px;margin:2rem auto;padding:0 1rem}
        a{color:#086772}a:focus-visible{outline:3px solid #086772;outline-offset:3px}
        table{border-collapse:collapse;background:white;width:100%;font-size:.88rem}
        th,td{border-bottom:1px solid #cad7dc;padding:.65rem;text-align:left;word-break:break-word}
        .scroll{overflow-x:auto}code{overflow-wrap:anywhere}
        .notice{background:#eaf3f5;border:1px solid #b3ccd4;padding:1rem}
    </style>
</head>
<body>
<main>
    <p><a href="{{ route('museum.content.preflight') }}">← Предпубликационная проверка</a></p>
    <h1>Журнал одобрений редакций</h1>
    <p class="notice">Только зафиксированное решение администратора о конкретной редакции.
        Постановка на закрытую выгрузку <strong>не является</strong> доказательством появления страницы на сайте
        или соблюдения срока 60 минут. Время указано в UTC.</p>
    <p>Последние 100 событий. Записи этого журнала не редактируются через интерфейс.</p>
    <div class="scroll">
        <table>
            <thead><tr><th>Событие</th><th>ID материала</th><th>UTC одобрения</th><th>SHA-256 редакции</th><th>Запрос выгрузки</th><th>ID запуска</th></tr></thead>
            <tbody>
            @forelse($approvals as $approval)
                <tr>
                    <td>{{ $approval->id }}</td>
                    <td>{{ $approval->museum_entry_id }}</td>
                    <td><time datetime="{{ $approval->approved_at->utc()->toIso8601String() }}">{{ $approval->approved_at->utc()->format('Y-m-d H:i:s') }}</time></td>
                    <td><code>{{ $approval->revision_sha256 }}</code></td>
                    <td>{{ $approval->dispatch_status }}</td>
                    <td>{{ $approval->publication_run_id ?? '—' }}</td>
                </tr>
            @empty
                <tr><td colspan="6">Подтверждённых одобрений пока нет.</td></tr>
            @endforelse
            </tbody>
        </table>
    </div>
</main>
</body>
</html>
