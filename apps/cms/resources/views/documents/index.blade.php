<!doctype html>
<html lang="ru">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>Документы · MusBread CMS</title>
<style>
body{font:1rem/1.5 system-ui;color:#172433;background:#f5f7f8;margin:0}
main{max-width:63rem;margin:2rem auto;padding:1rem}
section{background:white;padding:1.5rem;margin:1rem 0;border:1px solid #c6cdd2;border-radius:.6rem}
label{display:block;margin-top:.7rem}
input,select,button{font:inherit;padding:.45rem}
input,select{max-width:100%}
table{border-collapse:collapse;width:100%}td,th{padding:.65rem;border-bottom:1px solid #d7dcdf;text-align:left}
button{cursor:pointer}a:focus-visible,button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible{outline:.2rem solid #1679be}
.warning{border-left:.35rem solid #c47411;padding:.8rem;background:#fff4dc}
.drop{border:.15rem dashed #687f8b;padding:1rem;background:#f2f9f9;border-radius:.55rem;margin:.5rem 0}
.drop.drag{border-color:#007e83;background:#d9f2ef}
.drop input{max-width:100%}
.drop p{margin:.35rem 0}
</style></head>
<body><main>
<a href="/admin">← MoonShine</a>
<h1>Документы материалов (закрытый контур)</h1>
<p class="warning">Предварительная версия. Поддерживаются PDF, DOCX и XLSX до 15 МБ. В разработке поддерживается XLS: конвертируется в XLSX без формул, макросов и объектов; на production загрузка XLS закрыта до проверки антивирусом. Документы публикуются только вместе с утверждённым материалом. Не загружайте реальные материалы музея без прав.</p>
@if(session('status')) <p role="status">{{ session('status') }}</p> @endif
@if($errors->any())<div role="alert"><ul>@foreach($errors->all() as $error)<li>{{ $error }}</li>@endforeach</ul></div>@endif
<section>
<h2>Добавить файл</h2>
<form action="{{ route('museum.documents.store') }}" method="post" enctype="multipart/form-data">
@csrf
<label for="entry">Связанный материал</label>
<select name="museum_entry_id" id="entry" required><option value="">Выберите материал</option>
@foreach($entries as $entry)<option value="{{ $entry->id }}" @selected(old('museum_entry_id') == $entry->id)>{{ $entry->title }} ({{ $entry->slug }})</option>@endforeach
</select>
<label for="label">Короткое доступное название файла</label><input name="label" id="label" maxlength="180" minlength="3" value="{{ old('label') }}" required>
<label for="document">Файл PDF / DOCX / XLSX (на локальном стенде также XLS)</label>
<div class="drop" id="document-drop" data-museum-file-drop data-max-bytes="15728640"
     data-extensions="pdf,docx,xlsx,xls">
  <p>Перетащите один документ сюда или выберите файл</p>
  <input type="file" name="document" id="document" accept=".pdf,.docx,.xlsx,.xls" required
    aria-describedby="document-feedback">
  <p id="document-feedback" data-museum-file-feedback role="status" aria-live="polite">Файл не выбран.</p>
</div>
<button type="submit">Сохранить в закрытой медиатеке</button>
</form></section>
<section><h2>Загружено: {{ $documents->total() }}</h2>
<table><thead><tr><th>Название</th><th>Формат</th><th>Материал</th><th>Действие</th></tr></thead><tbody>
@foreach($documents as $document)<tr>
<td>{{ $document->label }}</td><td>{{ strtoupper($document->file_type) }} @if($document->source_type === "xls")(из XLS, только значения)@endif ({{ round($document->size_bytes/1024) }} КБ)
<p>{{ $document->accessible_edition_sha256
  ? 'Проверенная полнотекстовая HTML-редакция'
  : ($document->accessibility_reviewed ? 'Проверено только пояснение (не полная HTML-редакция)' : 'Доступность не подтверждена') }}</p></td>
<td>{{ $document->entry?->title }}</td>
<td><a href="{{ route('museum.documents.download', $document) }}">Скачать</a>
<form action="{{ route('museum.documents.accessibility', $document) }}" method="post">
@csrf @method('PATCH')
<label for="accessibility-{{ $document->id }}">Пояснение по доступности (не равно полной HTML-версии)</label>
<textarea id="accessibility-{{ $document->id }}" name="accessibility_note" maxlength="2000"
  rows="3" style="width:100%">{{ $document->accessibility_note }}</textarea>
<input type="hidden" name="accessibility_reviewed" value="0">
<label for="reviewed-{{ $document->id }}"><input id="reviewed-{{ $document->id }}"
  name="accessibility_reviewed" type="checkbox" value="1"
  @checked($document->accessibility_reviewed)> Пояснение проверено редактором (не подтверждает эквивалентность HTML или PDF/UA)</label>
<button type="submit">Сохранить пояснение</button></form>
<form action="{{ route('museum.documents.accessible-edition', $document) }}" method="post">
@csrf @method('PATCH')
<input type="hidden" name="source_sha256" value="{{ $document->sha256 }}">
<label for="html-edition-{{ $document->id }}">Полнотекстовая доступная HTML-редакция исходного файла (до 200 КБ)</label>
<p id="html-guidance-{{ $document->id }}">
  <strong>Важно:</strong> вставьте только проверенный полный текст из оригинала.
  Не используйте аннотацию вместо документа. Допустимы заголовки h2–h4, абзацы,
  списки и таблицы. Статус черновика не делает текст публичным.
  После сверки каждой страницы оригинального PDF сотрудник музея может подтвердить эквивалентность.
  Любое изменение HTML или исходного PDF аннулирует подтверждение.
</p>
<textarea id="html-edition-{{ $document->id }}" name="accessible_html"
  maxlength="200000" rows="7" style="width:100%" aria-describedby="html-guidance-{{ $document->id }}">{{ old('accessible_html', $document->accessible_html) }}</textarea>
<input type="hidden" name="approve_equivalence" value="0">
<label for="approve-equivalence-{{ $document->id }}">
  <input type="checkbox" name="approve_equivalence" value="1" id="approve-equivalence-{{ $document->id }}"
    @checked($document->accessible_edition_sha256 !== null)>
  Я сопоставил содержимое HTML со всеми страницами именно этого исходного файла (SHA-256:
  <code>{{ $document->sha256 }}</code>) и подтверждаю содержательную эквивалентность для публикации.
</label>
<button type="submit">Сохранить HTML-редакцию / подтверждение</button>
</form>
<form action="{{ route('museum.documents.destroy', $document) }}" method="post">@csrf @method('DELETE')
<button type="submit">Удалить</button></form></td>
</tr>@endforeach
</tbody></table>{{ $documents->links() }}</section>
</main><script src="{{ asset('js/museum-file-drop.js') }}" defer></script>
</body></html>
