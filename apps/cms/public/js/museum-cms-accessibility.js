/**
 * Accessibility fixes for upstream MoonShine-generated controls only.
 * No event interception, data submission, analytics or network actions.
 * Runs again for the MoonShine AJAX fragments and TomSelect rebuilding.
 * Remove mappings after upgrading to a vendor release with native labels.
 */
(() => {
  'use strict';
  const names = {
    type: 'Тип материала',
    museum_section_id: 'Раздел сайта',
    status: 'Статус материала',
  };
  const setName = (selector, label) => {
    document.querySelectorAll(selector).forEach(el => {
      if (!el.getAttribute('aria-label') && !el.getAttribute('aria-labelledby')) {
        el.setAttribute('aria-label', label);
      }
    });
  };
  function fix() {
    setName('.search-form-submit', 'Найти материал');
    setName('.search-form-clear', 'Очистить поиск');
    setName('a.js-detail-button', 'Просмотреть материал');
    setName('a.btn-square.btn-error', 'Удалить запись');
    document.querySelectorAll('.ts-control[role="combobox"]').forEach(control => {
      if (control.hasAttribute('aria-label') || control.hasAttribute('aria-labelledby')) return;
      const group = control.closest('.ts-wrapper')?.parentElement;
      const source = group?.querySelector('select.tomselected,select[name]');
      const nativeName = source?.getAttribute('name') ?? '';
      const label = names[nativeName] || (
        source?.id && document.querySelector('label[for="' + CSS.escape(source.id) + '"]')?.textContent.trim()
      ) || group?.querySelector('label')?.textContent.trim();
      if (label) control.setAttribute('aria-label', label);
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fix, {once:true});
  } else {
    fix();
  }
  // MoonShine renders fragments asynchronously: coalesce DOM changes into
  // at most one recheck per animation frame, including complex Jodit edits.
  let scheduled = false;
  const watch = new MutationObserver(() => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      fix();
    });
  });
  watch.observe(document.documentElement, {childList:true,subtree:true});
})();
