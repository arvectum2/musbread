/* Jodit CE 4.18.4 MIT, self-hosted. Server always sanitizes saved HTML. */
(function () {
  'use strict';
  const selector = 'textarea[data-museum-jodit="true"]';
  const instances = new WeakMap();
  function boot() {
    if (!window.Jodit) return;
    document.querySelectorAll(selector).forEach(element => {
      if (instances.has(element)) return;
      const editor = window.Jodit.make(element, {
        language: 'ru', height: 400, toolbarSticky: false,
        toolbarAdaptive: false,
        buttons: 'undo,redo,|,bold,italic,underline,|,ul,ol,|,link,unlink,|,source,eraser',
        removeButtons: ['image', 'file', 'video'],
        disablePlugins: ['file', 'speechRecognize'],
        uploader: {insertImageAsBase64URI: false},
        askBeforePasteHTML: false, askBeforePasteFromWord: false,
        showCharsCounter: false, showWordsCounter: false,
      });
      instances.set(element, editor);
      element.dataset.museumJoditReady = 'true';
      const sync = () => { element.value = editor.value; };
      editor.events.on('change', sync);
      const form = element.closest('form');
      if (form) {
        form.addEventListener('submit', sync, {capture: true});
        form.addEventListener('formdata', event => {
          sync();
          if (element.name) event.formData.set(element.name, element.value);
        });
      }
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, {once:true});
  } else boot();
  let scheduled=false;
  new MutationObserver(() => {
    if (scheduled) return;
    scheduled=true;
    queueMicrotask(() => { scheduled=false; boot(); });
  }).observe(document.documentElement, {childList:true,subtree:true});
  document.addEventListener('moonshine:page-load', boot);
})();
