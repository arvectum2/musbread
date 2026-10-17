/**
 * TZ-235: shared drag-and-drop enhancement for the two private CMS libraries.
 * Never uploads automatically. Only gives hints: Laravel's validation, ACL,
 * format inspector and media sanitizer remain the authoritative checks.
 */
(() => {
  "use strict";
  for (const zone of document.querySelectorAll("[data-museum-file-drop]")) {
    const input = zone.querySelector('input[type="file"]');
    const feedback = zone.querySelector('[data-museum-file-feedback]');
    if (!input || !feedback || !zone.dataset.maxBytes) continue;

    const allowed = (zone.dataset.extensions || "").split(",").map(s => s.trim()).filter(Boolean);
    const maximum = Number(zone.dataset.maxBytes);
    const describe = (file) => {
      if (!file) { feedback.textContent = "Файл не выбран."; return false; }
      const extension = file.name.toLowerCase().split(".").pop();
      if (!allowed.includes(extension)) {
        feedback.textContent = "Недопустимый формат файла. Используйте указанные выше типы.";
        input.value = "";
        return false;
      }
      if (file.size <= 0 || file.size > maximum) {
        feedback.textContent = "Размер файла должен быть больше нуля и не превышать "
          + Math.round(maximum / 1048576) + " МБ.";
        input.value = "";
        return false;
      }
      feedback.textContent = "Выбран файл «" + file.name + "» ("
        + Math.ceil(file.size / 1024) + " КБ). Для загрузки нажмите кнопку сохранения.";
      return true;
    };
    input.addEventListener("change", () => describe(input.files?.[0]));
    zone.addEventListener("dragenter", event => {
      event.preventDefault();
      zone.classList.add("drag");
    });
    zone.addEventListener("dragover", event => {
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
      zone.classList.add("drag");
    });
    zone.addEventListener("dragleave", event => {
      if (event.relatedTarget && zone.contains(event.relatedTarget)) return;
      zone.classList.remove("drag");
    });
    zone.addEventListener("drop", event => {
      event.preventDefault();
      zone.classList.remove("drag");
      const files = event.dataTransfer?.files;
      if (!files || files.length === 0) return;
      if (files.length !== 1) {
        input.value = "";
        feedback.textContent = "Загружайте по одному файлу, чтобы задать описание и привязку.";
        return;
      }
      if (describe(files[0])) {
        try { input.files = files; }
        catch { feedback.textContent = "Не удалось прикрепить файл: выберите его через поле ниже."; }
      }
    });
  }
})();
