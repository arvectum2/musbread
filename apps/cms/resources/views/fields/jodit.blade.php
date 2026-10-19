@props(['value' => '', 'label' => ''])
<div class="museum-jodit-field" data-museum-jodit-field>
    <x-moonshine::form.textarea
        :attributes="$attributes->merge([
            'aria-label' => $label ?? 'Визуальный редактор HTML',
            'data-museum-jodit' => 'true',
        ])"
    >{!! e($value ?? '') !!}</x-moonshine::form.textarea>
    <p class="text-xs">Заголовки, текст, списки и ссылки. Исходный HTML — кнопка «Источник». Для видео используйте [[museum-video:код]], для изображений — медиатеку.</p>
</div>
