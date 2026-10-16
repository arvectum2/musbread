<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive">
<title>Редакторские замечания к версии · MusBread</title>
<style>
:root{font:16px/1.5 system-ui,sans-serif;color:#263c46;background:#f3f6f7}*{box-sizing:border-box}body{margin:0}
header{background:#193642;color:white;padding:1rem max(1rem,calc((100% - 1040px)/2))}header a{color:white}
main{max-width:1040px;margin:2rem auto;padding:0 1rem 3rem}h1{margin:.2rem 0}h2{font-size:1.3rem;margin:2rem 0 .5rem}h3{margin:0 0 .3rem;font-size:1.05rem}
a{color:#075c6c}p{max-width:85ch}.muted{color:#52626b}.warning{background:#fff7e9;border:1px solid #c7a369;padding:.7rem 1rem;border-radius:7px}
article{background:white;border:1px solid #cad6dc;border-radius:8px;padding:1rem;margin:.7rem 0}
code{overflow-wrap:anywhere}.notes{padding-left:1.5rem}.notes li{padding:.35rem 0}
fieldset{margin-top:.8rem;border:1px solid #cbd7dc;border-radius:6px;padding:1rem;display:grid;gap:.6rem;max-width:650px}
select,textarea,button{font:inherit;max-width:100%;padding:.5rem}textarea{width:100%;min-height:82px}button{background:#144b5d;color:white;border:0;border-radius:6px;cursor:pointer;justify-self:start}button:focus-visible,a:focus-visible,select:focus-visible,textarea:focus-visible{outline:3px solid #2a7995;outline-offset:2px}
</style></head><body>
<header><strong>MusBread · Внутренняя редакторская проверка</strong><p><a href="{{ route('museum.content.compare') }}">← Вернуться к сравнению версий</a></p></header>
<main><h1>Замечания и решения по версии</h1>
<p class="warning">Это журнал <strong>внутреннего рассмотрения прототипа</strong>, а не юридическое утверждение материалов музеем и не разрешение на релиз. Записи сохраняются неизменяемой историей.</p>
@if($comparison['scope'] === 'assigned')
<p class="warning">Показаны только материалы ваших назначенных разделов, которыми вы вправе управлять сейчас. События, дерево разделов и замечания по чужим материалам доступны только администратору.</p>
@endif
<p class="muted">Локальный исходный снимок: <code>{{ $comparison['baseline_sha256'] }}</code>. Подготовленный снимок: <code>{{ $comparison['candidate_sha256'] }}</code>.</p>
<section aria-label="Сводка редакторской проверки" id="review-summary">
<h2>Сводка редакторской проверки</h2>
<p class="muted">Учитывается последнее решение для каждого изменённого объекта только в текущем проверяемом снимке и в пределах ваших прав. Это не разрешение на публикацию.</p>
<ul>
<li>Требуются исправления: <strong>{{ $summary['counts']['needs_changes'] }}</strong></li>
<li>Есть замечания: <strong>{{ $summary['counts']['comment'] }}</strong></li>
<li>Ещё не рассмотрено: <strong>{{ $summary['counts']['unreviewed'] }}</strong></li>
<li>Проверено внутри команды: <strong>{{ $summary['counts']['checked'] }}</strong></li>
</ul>
<h3>Что требует внимания ({{ count($summary['attention']) }})</h3>
@if($summary['attention'] === [])
<p>Открытых пунктов в доступных материалах нет. Это не подтверждает согласование музеем.</p>
@else
<ol>
@foreach($summary['attention'] as $item)
<li><strong>{{ ['needs_changes' => 'Требуются исправления', 'comment' => 'Есть замечания', 'unreviewed' => 'Не рассмотрено'][$item['status']] }}</strong> · <a href="#review-{{ substr(hash('sha256', $item['group'].':'.$item['key']), 0, 16) }}">{{ $item['title'] }}</a> ({{ $item['group'] }})</li>
@endforeach
</ol>
@endif
</section>
<section aria-label="Очередь редакторских задач" id="review-tasks">
<h2>Очередь редакторских задач</h2>
<p class="muted">В работе: {{ $taskStats['in_progress'] }} · Открыто: {{ $taskStats['open'] }} · Выполнено внутри команды: {{ $taskStats['done'] }}. Порядок: незавершённые выше выполненных, затем по приоритету. Задачи действуют только для текущей версии и не утверждают выпуск.</p>
@if($taskList === [])<p>Назначенных задач пока нет. Создать задачу можно в карточке изменённого материала ниже.</p>
@else
<ol>
@foreach($taskList as $task)
<li><strong>{{ ['open'=>'Открыта','in_progress'=>'В работе','done'=>'Выполнена внутри команды'][$task['status']] }}</strong>
 · {{ ['high'=>'Высокий','normal'=>'Обычный','low'=>'Низкий'][$task['priority']] }} приоритет
 · сотрудник #{{ $task['assignee_id'] }}
 · <a href="#review-{{ substr(hash('sha256', $task['group'].':'.$task['key']),0,16) }}">{{ $task['title'] }}</a></li>
@endforeach
</ol>
@endif
</section>
@if($priorCount > 0)<p class="muted">Исторических замечаний к другим версиям: {{ $priorCount }}. Они не переносятся на текущую версию автоматически.</p>@endif
@if($errors->any())<p role="alert" class="warning">{{ $errors->first() }}</p>@endif
@php($decisions = ['comment' => 'Замечание', 'needs_changes' => 'Требуются изменения', 'checked' => 'Проверено внутри команды (не утверждено музеем)'])
@foreach(['entries'=>'Материалы','events'=>'События','sections'=>'Разделы'] as $group=>$label)
@if(isset($comparison['groups'][$group]))
<section aria-label="{{ $label }}"><h2>{{ $label }}</h2>
@forelse($comparison['groups'][$group] as $row)
@if($row['action'] !== 'unchanged')
<article id="review-{{ substr(hash('sha256', $group.':'.$row['key']), 0, 16) }}"><h3>{{ $row['title'] }}</h3><p class="muted">Текущее внутреннее состояние: {{ ['unreviewed'=>'Не рассмотрено','comment'=>'Есть замечания','needs_changes'=>'Требуются исправления','checked'=>'Проверено внутри команды'][$summary['state'][$group.':'.$row['key']] ?? 'unreviewed'] }}</p><p>{{ $row['action'] }} · <code>{{ $row['key'] }}</code></p>
@if($row['changed_fields'] !== [])<p>Поля: {{ implode(', ', $row['changed_fields']) }}</p>@endif
@php($itemNotes = $current->get($group.':'.$row['key'], collect()))
@if($itemNotes->isNotEmpty())<ol class="notes">@foreach($itemNotes as $entry)<li><strong>{{ $decisions[$entry->decision] ?? $entry->decision }}</strong> · {{ $entry->created_at?->format('d.m.Y H:i') }} · сотрудник #{{ $entry->actor_id }}<p>{{ $entry->note }}</p></li>@endforeach</ol>@else<p class="muted">По этой версии замечаний пока нет.</p>@endif
@php($taskKey = $group.':'.$row['key'])
@php($taskEvents = $taskHistory->get($taskKey, collect()))
@php($lastTask = $taskEvents->last())
<section aria-label="Задача по материалу">
<h4>Задача по материалу</h4>
@if($lastTask)
<p>Текущая задача: <strong>{{ ['open'=>'Открыта','in_progress'=>'В работе','done'=>'Выполнена внутри команды'][$lastTask->task_status] }}</strong>
 · приоритет {{ ['high'=>'высокий','normal'=>'обычный','low'=>'низкий'][$lastTask->priority] }}
 · ответственный #{{ $lastTask->assignee_id }}.</p>
<details><summary>История задачи ({{ $taskEvents->count() }})</summary>
<ol>@foreach($taskEvents as $update)<li>{{ $update->created_at?->format('d.m.Y H:i') }} · сотрудник #{{ $update->actor_id }}
 → ответственный #{{ $update->assignee_id }}, {{ ['open'=>'открыта','in_progress'=>'в работе','done'=>'сделано внутри команды'][$update->task_status] }},
 {{ ['high'=>'высокий','normal'=>'обычный','low'=>'низкий'][$update->priority] }} приоритет · {{ $update->note }}</li>@endforeach</ol>
</details>
@else<p class="muted">Задача ещё не назначена.</p>@endif
@if($user->isSuperUser() || !$lastTask || (int)$lastTask->assignee_id === (int)$user->getKey())
<form method="post" action="{{ route('museum.content.editorial-task.store') }}">
@csrf
<input type="hidden" name="baseline_sha256" value="{{ $comparison['baseline_sha256'] }}">
<input type="hidden" name="candidate_sha256" value="{{ $comparison['candidate_sha256'] }}">
<input type="hidden" name="item_group" value="{{ $group }}"><input type="hidden" name="item_key" value="{{ $row['key'] }}">
<fieldset><legend>Назначить или обновить задачу</legend>
<label>Ответственный <select name="assignee_id" required>
@foreach($taskOwners[$taskKey] as $assigneeId=>$assigneeName)
<option value="{{ $assigneeId }}" @selected((int)($lastTask?->assignee_id ?? $user->getKey())===(int)$assigneeId)>{{ $assigneeName }}</option>
@endforeach
</select></label>
<label>Приоритет <select name="priority" required>
@foreach(['high'=>'Высокий','normal'=>'Обычный','low'=>'Низкий'] as $priority=>$label)
<option value="{{ $priority }}" @selected(($lastTask?->priority ?? 'normal')===$priority)>{{ $label }}</option>
@endforeach</select></label>
<label>Состояние <select name="task_status" required>
@foreach(['open'=>'Открыта','in_progress'=>'В работе','done'=>'Выполнена внутри команды'] as $status=>$label)
<option value="{{ $status }}" @selected(($lastTask?->task_status ?? 'open')===$status)>{{ $label }}</option>
@endforeach</select></label>
<label>Отчёт о работе (3–1200 символов)<textarea name="note" required minlength="3" maxlength="1200" placeholder="Что сделать или что исправлено?"></textarea></label>
<button type="submit">Сохранить состояние задачи</button></fieldset></form>
@else<p class="muted">Задача назначена другому сотруднику. Передачу задачи выполняет администратор.</p>@endif
</section>
<form method="post" action="{{ route('museum.content.editorial-review.store') }}">
@csrf
<input type="hidden" name="baseline_sha256" value="{{ $comparison['baseline_sha256'] }}">
<input type="hidden" name="candidate_sha256" value="{{ $comparison['candidate_sha256'] }}">
<input type="hidden" name="item_group" value="{{ $group }}">
<input type="hidden" name="item_key" value="{{ $row['key'] }}">
<fieldset><legend>Добавить запись в историю</legend><label>Результат внутренней проверки
<select name="decision" required>@foreach($decisions as $value=>$name)<option value="{{ $value }}">{{ $name }}</option>@endforeach</select></label>
<label>Комментарий (до 1200 символов)<textarea name="note" required minlength="3" maxlength="1200" placeholder="Что нужно проверить или исправить?"></textarea></label>
<button type="submit">Записать замечание</button></fieldset>
</form></article>
@endif
@empty<p>Объектов нет.</p>@endforelse
</section>
@endif
@endforeach
<p class="warning">Смена текста, статуса или раздела создаёт новый SHA-256 подготовленной версии. Старые замечания остаются в базе для аудита, но не считаются рассмотрением новой версии. Команда <code>museum:verify-review</code> проверяет актуальность пакета отдельно.</p>
</main></body></html>
