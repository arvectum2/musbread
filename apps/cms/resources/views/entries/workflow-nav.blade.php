<section aria-label="Следующие шаги редактора" style="padding:1rem 1.2rem;margin:1rem 0;border:1px solid #9daec2;border-radius:10px;background:#f4f7fc;color:#172433">
    <strong>Маршрут редактора</strong>
    @if($entry instanceof \App\Models\MuseumEntry && $entry->exists)
        <p>Работа с материалом: <strong>{{ $entry->title }}</strong>. После каждого изменения сохраните форму, прежде чем переходить к другим действиям.</p>
        <nav aria-label="Действия по текущему материалу" style="display:flex;gap:.75rem;flex-wrap:wrap">
            <a href="{{ route('museum.media.index', ['entry' => $entry->id]) }}">Изображения</a>
            <a href="{{ route('museum.documents.index', ['entry' => $entry->id]) }}">Документы</a>
            <a href="{{ route('museum.entries.relations.edit', ['entry' => $entry->id]) }}">Связи</a>
            <a href="{{ route('museum.entries.preview', ['entry' => $entry->id]) }}" target="_blank" rel="noopener noreferrer">Предпросмотр ↗</a>
            <a href="{{ route('museum.content.preflight') }}#entry-{{ $entry->id }}">Проверка перед публикацией</a>
        </nav>
        <p style="font-size:.88rem">Предпросмотр показывает <strong>последнюю сохранённую редакцию</strong>, а не текущие несохранённые поля. Одобрение и закрытая выгрузка — отдельные действия уполномоченного сотрудника.</p>
    @else
        <p>1. Заполните обязательные поля и <strong>сохраните новый материал</strong>.
           2. После сохранения здесь появятся прямые переходы к изображениям, документам, предпросмотру и проверке.</p>
    @endif
</section>
