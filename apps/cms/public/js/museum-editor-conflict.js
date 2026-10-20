/* Local, no dependencies, no server requests. Only a real user click saves data.
 * The server already escaped both columns. Never render unsaved HTML as markup.
 */
(function () {
  'use strict';
  const draftElements = document.querySelectorAll('[data-conflict-draft]');
  if (!draftElements.length) return;
  const status = document.getElementById('copy-status');
  const drafts = () => Object.fromEntries(Array.from(draftElements, el => [el.dataset.conflictDraft, el.value]));
  function announce(message) { if (status) status.textContent = message; }

  document.getElementById('download-draft')?.addEventListener('click', () => {
    const data = JSON.stringify({warning: 'Несохранённая редакция. Проверьте актуальную версию перед переносом.',
      fields: drafts()}, null, 2);
    const url = URL.createObjectURL(new Blob([data], {type: 'application/json;charset=utf-8'}));
    try {
      const link = document.createElement('a');
      link.href = url;
      link.download = 'museum-unsaved-draft.json';
      document.body.appendChild(link);
      link.click();
      link.remove();
      announce('Черновик подготовлен для сохранения на вашем устройстве.');
    } finally {
      setTimeout(() => URL.revokeObjectURL(url), 1200);
    }
  });

  document.querySelectorAll('[data-copy-draft]').forEach(button => {
    button.addEventListener('click', async () => {
      const fieldName = button.dataset.copyDraft;
      const input = document.getElementById('draft-' + fieldName);
      if (!input) return;
      try {
        await navigator.clipboard.writeText(input.value);
        announce('Поле скопировано. Вставьте его в открытую актуальную редакцию после проверки.');
      } catch (_) {
        input.focus();
        input.select();
        announce('Текст выделен. Скопируйте его сочетанием клавиш Ctrl+C или Command+C.');
      }
    });
  });
})();
