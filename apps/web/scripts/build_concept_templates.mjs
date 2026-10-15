import { chromium } from "@playwright/test";
import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

const output = resolve(process.cwd(), "../../docs/design/templates");
await mkdir(output, { recursive: true });

const decks = [
  { id: "01", accent: "#735a41", title: "Направление 01", note: "Вопросы к первому концептуальному направлению" },
  { id: "02", accent: "#44685f", title: "Направление 02", note: "Вопросы ко второму концептуальному направлению" },
  { id: "03", accent: "#754c65", title: "Направление 03", note: "Вопросы к третьему концептуальному направлению" },
];

const content = [
  {
    title: "Исходная гипотеза",
    kicker: "01 / СТРАТЕГИЯ",
    lead: "Какую проверяемую идею должно раскрыть это направление?",
    cards: [
      ["Позиционирование", "[Заполнить после интервью]"],
      ["Отличие от других музеев", "[Факты и референсы после интервью]"],
      ["Главная цель посетителя", "[Сценарий для подтверждения]"],
    ],
  },
  {
    title: "Аудитории и смысл",
    kicker: "02 / ПОЛЬЗОВАТЕЛЬ",
    lead: "Что узнает, почувствует и сделает посетитель?",
    cards: [
      ["Приоритетные аудитории", "[Определить вместе с музеем]"],
      ["Тон коммуникации", "[Тезисы, запреты и примеры]"],
      ["Доступность", "[Критерии контраста и чтения]"],
    ],
  },
  {
    title: "Логотип и языковые версии",
    kicker: "03 / ЗНАК",
    lead: "Здесь позже будут реально разработанные и проверенные эскизы.",
    cards: [
      ["Русская версия", "[Место для двух векторных вариантов]"],
      ["Английская версия", "[Проверить официальное написание]"],
      ["Проверки применения", "[Размер / инверсия / монохром / лицензии]"],
    ],
  },
  {
    title: "Визуальная система",
    kicker: "04 / СИСТЕМА",
    lead: "Результат заполняется только после выбора направления.",
    cards: [
      ["Цвета и градиенты", "[Палитра RGB, CMYK, Pantone и HEX]"],
      ["Шрифты и иконки", "[Открытые лицензии; набор из 10 иконок]"],
      ["Паттерны и композиции", "[Не менее 3 паттернов и сетки]"],
    ],
  },
  {
    title: "Носители и решение",
    kicker: "05 / ПРОВЕРКА",
    lead: "Заказчик сравнивает направления по единым критериям.",
    cards: [
      ["Digital", "[Главная сайта, событие, мобильный экран]"],
      ["Музей, печать и сувениры", "[Билет, указатель, афиша, предмет]"],
      ["Решение и доработки", "[Место для протокола, НЕ согласовано]"],
    ],
  },
];

const css = [
  "@page { size: 297mm 210mm; margin: 0; }",
  "* { box-sizing: border-box; }",
  "html, body { margin: 0; padding: 0; font-family: Arial, 'Helvetica Neue', sans-serif; color: #27302c; }",
  "body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }",
  ".slide { width: 297mm; height: 210mm; page-break-after: always; break-after: page; overflow: hidden;",
  " padding: 19mm 23mm 16mm; background: #faf9f5; display: flex; flex-direction: column; position: relative; }",
  ".slide:last-of-type { page-break-after: auto; break-after: auto; }",
  ".stripe { position:absolute; top:0;left:0;right:0;height:5mm;background:var(--accent); }",
  ".eyebrow { font-size: 11pt; font-weight:700;letter-spacing:2px;color:var(--accent);margin-top:4mm; }",
  "h1 { margin: 9mm 0 0; font-size: 32pt; letter-spacing:-1px; line-height:1.12; }",
  ".lead {font-size:16pt;color:#4a5751;margin:5mm 0 11mm;max-width:245mm;}",
  ".cards { display:grid; grid-template-columns: repeat(3,1fr); gap:7mm; flex:1; align-items:start; }",
  ".card { border:1.2px dashed #aaaea7; border-top:3px solid var(--accent);border-radius:5px;",
  "background:#fff;min-height:75mm;padding:9mm 7mm; }",
  ".card h2 {font-size:14pt;color:var(--accent);margin:0 0 7mm;line-height:1.25;}",
  ".card p {font-size:13pt;line-height:1.5;color:#58635e;}",
  ".footer {font-size:9pt;color:#67716b;border-top:1px solid #d6d9d2;padding-top:6mm;",
  "display:flex;justify-content:space-between;align-items:center;}",
  ".watermark {position:absolute;right:23mm;top:17mm;font-weight:700;color:#9a9d96;font-size:10pt;}",
].join("\n");

function esc(value) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function makeHtml(deck) {
  const slides = content.map((slide, index) => {
    const cards = slide.cards.map(([heading, note]) =>
      '<div class="card"><h2>' + esc(heading) + '</h2><p>' + esc(note) + '</p></div>'
    ).join("");
    return '<section class="slide" style="--accent:' + deck.accent + '">' +
      '<div class="stripe"></div><div class="watermark">ШАБЛОН · НЕ УТВЕРЖДЕНО</div>' +
      '<p class="eyebrow">' + esc(slide.kicker) + '</p>' +
      '<h1>' + esc(slide.title) + '</h1><p class="lead">' + esc(slide.lead) + '</p>' +
      '<div class="cards">' + cards + '</div>' +
      '<div class="footer"><span>MusBread · ' + esc(deck.title) + ' · ' + esc(deck.note) +
      '</span><span>Каркас презентации · ' + (index + 1) + ' / 5</span></div></section>';
  }).join("");
  return '<!doctype html><html lang="ru"><head><meta charset="utf-8"><style>' +
    css + '</style></head><body>' + slides + '</body></html>';
}

const browser = await chromium.launch({ channel: "chrome", headless: true });
try {
  for (const deck of decks) {
    const page = await browser.newPage();
    const html = makeHtml(deck);
    const prefix = "musbread_concept_" + deck.id + "_TEMPLATE";
    await writeFile(resolve(output, prefix + ".html"), html, "utf8");
    await page.setContent(html, { waitUntil: "load" });
    await page.pdf({
      path: resolve(output, prefix + ".pdf"),
      width: "297mm",
      height: "210mm",
      preferCSSPageSize: true,
      printBackground: true,
      margin: { top: "0", right: "0", bottom: "0", left: "0" },
    });
    await page.close();
    console.log(prefix + " PDF/HTML written");
  }
} finally {
  await browser.close();
}
