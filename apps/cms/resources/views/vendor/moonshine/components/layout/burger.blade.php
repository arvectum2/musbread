@props([
    'toggleMethod' => 'toggleSidebar',
    'toggleState' => 'isSidebarOpen',
    'sidebar' => false,
    'topbar' => false,
    'mobileBar' => false,
])

<button
    type="button"
    aria-label="{{ $sidebar ? 'Открыть или закрыть боковое меню' : ($topbar ? 'Открыть или закрыть верхнее меню' : 'Открыть или закрыть мобильное меню') }}"
    :aria-expanded="$store.menu[@js($toggleState)] ? 'true' : 'false'"
    {{ $attributes->merge(['class' => 'btn-burger btn-fit']) }}
    @if(!$attributes->has('@click.prevent'))
        @click.prevent="$store.menu[@js($toggleMethod)]()"
    @endif
>
    <svg x-show="!$store.menu[@js($toggleState)]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
    </svg>
    <svg x-cloak x-show="$store.menu[@js($toggleState)]" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
    </svg>
</button>
