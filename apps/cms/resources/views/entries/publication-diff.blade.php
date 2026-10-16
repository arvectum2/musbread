<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive">
<title>Сравнение версий сайта — MusBread CMS</title>
<style>
:root{font:16px/1.5 system-ui,sans-serif;color:#243744;background:#f4f7f8}*{box-sizing:border-box}body{margin:0}
header{background:#193642;color:white;padding:1rem max(1rem,calc((100% - 1050px)/2))}header a{color:white}
main{max-width:1050px;margin:2rem auto;padding:0 1rem 3rem}h1{margin:0 0 .35rem}h2{margin:2rem 0 .8rem;font-size:1.25rem}
p{max-width:80ch}a{color:#095f71}a:focus-visible{outline:3px solid #1769a0;outline-offset:2px}
.summary{display:flex;gap:.65rem;flex-wrap:wrap;margin:1rem 0}.summary span{padding:.5rem .8rem;background:white;border:1px solid #cbd8dd;border-radius:6px}
.warning{border:1px solid #d5ac61;border-radius:6px;padding:.8rem 1rem;background:#fff8e9}.context{color:#435666;font-size:.92rem}
article{padding:1rem;margin:.6rem 0;background:white;border:1px solid #d2dce1;border-radius:8px}
article[data-action="removed"]{border-inline-start:4px solid #9a3c26}article[data-action="changed"]{border-inline-start:4px solid #b87a24}article[data-action="added"]{border-inline-start:4px solid #176d4d}
article h3{font-size:1.05rem;margin:0 0 .3rem}article p{margin:.3rem 0}.state{font-weight:650}code{overflow-wrap:anywhere}
</style>
</head>
<body><header><strong>MusBread · Закрытая CMS</strong><p><a href="/admin/museum-content/preflight">← К предпубликационной проверке</a></p></header>
<main>
<h1>Сравнение подготовленной и предыдущей версий</h1>
<p>Сравниваем текущие опубликованные в CMS записи, готовые к следующей выгрузке, с содержимым <strong>последнего локального проверенного релиза</strong>. Это не данные действующего сайта музея и не подтверждение фактического развёртывания. Просмотр не меняет релиз, CMS или очередь публикаций.</p>
@if($error)
<p role="alert" class="warning">{{ $error }}</p>
@elseif(! $comparison['baseline_available'])
<p role="alert" class="warning">Подтверждённый локальный базовый снимок недоступен. Сравнение добавлений и удалений скрыто, чтобы не показывать ложные изменения. Для локального стенда администратор может проверить релиз и заархивировать исходный снимок командой <code>python3 scripts/release_site.py archive-current</code>, если его SHA-256 совпадает с текущим релизом.</p>
<p class="context">Хэш подготовленного снимка: <code>{{ $comparison['candidate_sha256'] }}</code></p>
@else
<p class="context">Локальный релиз: <code>{{ $comparison['baseline_release'] }}</code> · SHA-256 исходного снимка: <code>{{ $comparison['baseline_sha256'] }}</code> · SHA-256 подготовленного: <code>{{ $comparison['candidate_sha256'] }}</code>.</p>
@if($comparison['scope'] === 'assigned')
<p class="warning">Редактору доступны изменения только в назначенных ему разделах; события отображаются по текущей модели полномочий MoonShine. Полный отчёт, включая структуру, доступен администратору.</p>
@endif
<div class="summary" aria-label="Итоги различий">
<span>Добавлено: <strong>{{ $comparison['summary']['added'] }}</strong></span>
<span>Изменено: <strong>{{ $comparison['summary']['changed'] }}</strong></span>
<span>Удаляется из следующей версии: <strong>{{ $comparison['summary']['removed'] }}</strong></span>
<span>Без изменений: <strong>{{ $comparison['summary']['unchanged'] }}</strong></span>
</div>
<p class="context">Удаление из следующей версии означает исчезновение материала из нового снимка (например, перевод в черновик), а не удаление записи в CMS. Изменённые поля перечислены без вывода приватного HTML.</p>
@if($comparison['removed_urls'] !== [])
<section aria-label="Адреса, которые исчезнут из следующей публикации">
<h2>Адреса, которые требуют решения</h2>
<p class="warning">Ниже перечислены URL, которые есть в последнем локальном релизе, но отсутствуют в подготовленной версии. Это ещё не настроенные перенаправления: новый адрес нужно определить и согласовать отдельно.</p>
<p><a href="{{ route('museum.content.removed-urls') }}">Скачать CSV для проверки перенаправлений</a></p>
<ul>
@foreach($comparison['removed_urls'] as $item)
<li><code>{{ $item['path'] }}</code> · {{ $item['locale'] }} · {{ $item['title'] }}</li>
@endforeach
</ul>
</section>
@endif
@foreach(['entries'=>'Материалы сайта','events'=>'События афиши','sections'=>'Структура разделов'] as $key=>$label)
@if(array_key_exists($key, $comparison['groups']))
<section aria-label="{{ $label }}"><h2>{{ $label }}</h2>
@forelse($comparison['groups'][$key] as $row)
<article data-action="{{ $row['action'] }}">
<h3>{{ $row['title'] }}</h3>
<p><span class="state">{{ ['added'=>'Добавится','changed'=>'Изменится','removed'=>'Исчезнет из новой версии','unchanged'=>'Без изменений'][$row['action']] }}</span> · <code>{{ $row['key'] }}</code></p>
@if($row['changed_fields'] !== [])<p>Изменённые поля: {{ implode(', ', $row['changed_fields']) }}.</p>@endif
</article>
@empty<p>Объектов в этом разделе нет.</p>@endforelse
</section>
@endif
@endforeach
@endif
@if($comparison)
<p class="warning">Проверка перед выпуском: критических замечаний по подготовленным материалам и событиям — <strong>{{ $comparison['preflight']['errors'] }}</strong>; предупреждений — <strong>{{ $comparison['preflight']['warnings'] }}</strong>. <a href="{{ route('museum.content.preflight') }}">Открыть подробный отчёт</a>. Даже при нуле ошибок изменения не публикуются автоматически.</p>
@endif
</main></body></html>
