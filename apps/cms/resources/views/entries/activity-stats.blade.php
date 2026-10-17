<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><title>Статистика действий — закрытая CMS</title>
<style>
:root{font:16px/1.5 system-ui,sans-serif;color:#183242;background:#f4f7f8}body{margin:0}header{background:#193642;color:white;padding:1rem max(1rem,calc((100% - 1100px)/2))}header a{color:white}main{max-width:1100px;margin:1.4rem auto;padding:0 1rem 4rem}a{color:#06576a}a:focus-visible,input:focus-visible,button:focus-visible{outline:3px solid #a86a1e;outline-offset:2px}
.cards{display:flex;flex-wrap:wrap;gap:1rem}.card{background:white;border:1px solid #d4e2e7;padding:1rem;min-width:10rem;border-radius:5px}.card strong{font-size:1.7rem}.wrap{overflow:auto;background:#fff;border:1px solid #d1dce2;border-radius:6px}table{width:100%;border-collapse:collapse;min-width:500px}th,td{padding:.55rem .8rem;text-align:left;border-bottom:1px solid #e6edef}th{background:#eaf0f4}form{display:flex;align-items:end;gap:.7rem;flex-wrap:wrap;padding:1rem 0}label{display:flex;flex-direction:column;gap:.25rem}input,button{font:inherit;padding:.45rem;border:1px solid #879da9;border-radius:4px}button{background:#143f56;color:#fff;cursor:pointer}h2{margin:1.6rem 0 .6rem}.muted{color:#405e6b}
</style></head><body><header><strong>MusBread · закрытый административный контур</strong> · <a href="/admin">CMS</a></header>
<main><h1>Статистика действий сотрудников</h1>
<p class="muted">На основании локального аудита операций создания, изменения и удаления материалов, входов и выходов из CMS. Без паролей, IP-адресов и содержимого пользовательских записей. Данные до появления аудита недоступны; не включает просмотры посетителей и отклонённые попытки входа.</p>
<form method="get" action="{{ route('museum.activity.stats') }}">
<label>С даты <input type="date" name="from" value="{{ $from->toDateString() }}"></label>
<label>По дату (включительно) <input type="date" name="to" value="{{ $to->toDateString() }}"></label>
<label>ID сотрудника (необязательно) <input type="number" name="actor_id" min="1" value="{{ $actorId ?? '' }}"></label>
<button type="submit">Показать</button><a href="{{ route('museum.activity.stats') }}">Сбросить</a>
</form>
<p class="muted">Период аудита включительно: {{ $from->format('d.m.Y') }} — {{ $to->format('d.m.Y') }}.
@if($actorId !== null) Фильтр: сотрудник #{{ $actorId }}.@endif
Итоги относятся только к действиям, попавшим в этот период.</p>
<div class="cards"><div class="card">Записей<br><strong>{{ $total }}</strong></div><div class="card">Сотрудников<br><strong>{{ $uniqueActors }}</strong></div></div>
<h2>Динамика по дням</h2>
<p class="muted">Число зарегистрированных действий по датам. Дни без записей не представлены; время учитывается в часовом поясе БД.</p>
<div class="wrap"><table><thead><tr><th>День</th><th>Действий</th></tr></thead><tbody>
@forelse($daily as $row)<tr><td>{{ $row->day }}</td><td>{{ $row->total }}</td></tr>@empty<tr><td colspan="2">За выбранный период нет зарегистрированных действий</td></tr>@endforelse
</tbody></table></div>
<h2>Действия</h2><div class="wrap"><table><thead><tr><th>Действие</th><th>Количество</th></tr></thead><tbody>
@forelse($actions as $action=>$count)<tr><td>{{ ['created'=>'Создание','updated'=>'Изменение','deleted'=>'Удаление','login'=>'Вход в CMS','logout'=>'Выход из CMS'][$action] ?? $action }}</td><td>{{ $count }}</td></tr>@empty<tr><td colspan="2">Нет записей за выбранный период</td></tr>@endforelse
</tbody></table></div>
<h2>Объекты</h2><div class="wrap"><table><thead><tr><th>Тип объекта</th><th>Количество</th></tr></thead><tbody>
@forelse($subjects as $subject=>$count)<tr><td>{{ $subject }}</td><td>{{ $count }}</td></tr>@empty<tr><td colspan="2">Пока нет данных</td></tr>@endforelse
</tbody></table></div>
<h2>Сотрудники — до 50 наиболее активных</h2><div class="wrap"><table><thead><tr><th>ID сотрудника</th><th>Операций</th></tr></thead><tbody>
@forelse($users as $row)<tr><td>#{{ $row->actor_id }}</td><td>{{ $row->total }}</td></tr>@empty<tr><td colspan="2">Нет действий</td></tr>@endforelse
</tbody></table></div>
<h2>Последние 100 операций</h2><div class="wrap"><table><thead><tr><th>Время</th><th>Сотрудник</th><th>Объект</th><th>Действие</th></tr></thead><tbody>
@forelse($recent as $row)<tr><td>{{ $row->created_at?->format('d.m.Y H:i:s') }}</td><td>{{ $row->actor_id === null ? 'Система' : '#'.$row->actor_id }}</td><td>{{ $row->subject_type }} #{{ $row->subject_id }}</td><td>{{ $row->action }}</td></tr>@empty<tr><td colspan="4">Нет операций</td></tr>@endforelse
</tbody></table></div>
<h2>Состояние материалов и разделов CMS</h2>
<p class="muted">Это текущее состояние закрытой БД; показатели ниже не зависят от фильтра даты и сотрудника. Черновики не означают готовность к публичной выдаче.</p>
<div class="cards">
<div class="card">Черновики материалов<br><strong>{{ $inventory['entry_drafts'] }}</strong></div>
<div class="card">Материалы готовы к следующей выгрузке<br><strong>{{ $inventory['entry_ready'] }}</strong></div>
<div class="card">Материалы ожидают даты публикации<br><strong>{{ $inventory['entry_scheduled'] }}</strong></div>
<div class="card">Материалы сняты по сроку<br><strong>{{ $inventory['entry_expired'] }}</strong></div>
<div class="card">Черновики событий<br><strong>{{ $inventory['event_drafts'] }}</strong></div>
<div class="card">События готовы к следующей выгрузке<br><strong>{{ $inventory['event_ready'] }}</strong></div>
<div class="card">События ожидают даты публикации<br><strong>{{ $inventory['event_scheduled'] }}</strong></div>
<div class="card">События сняты по сроку<br><strong>{{ $inventory['event_expired'] }}</strong></div>
<div class="card">Черновики разделов<br><strong>{{ $inventory['sections_draft'] }}</strong></div>
<div class="card">Опубликованные разделы CMS<br><strong>{{ $inventory['sections_published'] }}</strong></div>
</div>
<h2>Публикации статического сайта</h2>
<p class="muted">Это результаты попыток очереди из таблицы запусков: не обращения посетителей и не подтверждение публикации на производственном сервере. Данные не связаны с выбранным ID сотрудника или периодом.</p>
<div class="wrap"><table><thead><tr><th>Статус запуска</th><th>Количество</th></tr></thead><tbody>
@forelse($publicationStatuses as $status=>$count)<tr><td>{{ ['queued'=>'В очереди','running'=>'Выполняется','succeeded'=>'Успешно подготовлен','failed'=>'Ошибка','abandoned'=>'Прекращён'][$status] ?? $status }}</td><td>{{ $count }}</td></tr>@empty<tr><td colspan="2">Запусков пока нет</td></tr>@endforelse
</tbody></table></div>
<h2>Последние 20 запусков публикации</h2>
<div class="wrap"><table><thead><tr><th>Номер</th><th>Статус</th><th>Начат</th><th>Завершён</th><th>Попыток</th></tr></thead><tbody>
@forelse($recentPublications as $run)<tr>
<td>#{{ $run->id }}</td><td>{{ $run->status }}</td>
<td>{{ $run->started_at?->format('d.m.Y H:i:s') ?? '—' }}</td>
<td>{{ $run->finished_at?->format('d.m.Y H:i:s') ?? '—' }}</td>
<td>{{ $run->attempts }}</td>
</tr>@empty<tr><td colspan="5">Запусков пока нет</td></tr>@endforelse
</tbody></table></div>
<p class="muted">Статистика описывает только события, которые система фактически записала. Не включает просмотры посетителей, отклонённые входы, SLA или действия до включения аудита; срок хранения журнала утверждается заказчиком.</p>
</main></body></html>
