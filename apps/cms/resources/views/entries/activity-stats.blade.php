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
<label>ID сотрудника (необязательно) <input type="number" name="actor_id" min="1" value="{{ $actorId ?? '' }}"></label>
<button type="submit">Показать</button><a href="{{ route('museum.activity.stats') }}">Сбросить</a>
</form>
<div class="cards"><div class="card">Записей<br><strong>{{ $total }}</strong></div><div class="card">Сотрудников<br><strong>{{ $uniqueActors }}</strong></div></div>
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
<p class="muted">Это предварительный административный отчёт без анализа отклонённых попыток входа, SLA, фактического использования заказчиком и согласованного срока хранения журналов.</p>
</main></body></html>
