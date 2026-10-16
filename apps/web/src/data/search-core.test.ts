import assert from "node:assert/strict";
import test from "node:test";
import { indexableText, normalizeSearch, rankSearch, type SearchItem } from "./search-core.ts";

const published: SearchItem[] = [
  { title: "История хлеба", href: "/museum/history/", section: "Музей", excerpt: "Старинные рецепты", bodyText: "В экспозиции представлены формы для выпечки" },
  { title: "Выставка пекарей", href: "/events/pekar/", section: "Афиша", excerpt: "Завтра открытие выставки", bodyText: "Большая хлебная мастерская" },
  { title: "Документы", href: "/documents/rules/", section: "Документы", excerpt: "Правила посещения", bodyText: "Доступная среда" },
];

test("Russian spelling, case, punctuation and ё/е are normalized", () => {
  assert.equal(normalizeSearch("  Ёлка, ХЛЕБ!\n"), "елка хлеб");
  assert.equal(normalizeSearch("Санкт–Петербург"), "санкт петербург");
  assert.equal(rankSearch([{ ...published[0], title: "Ёлка" }], "елка").length, 1);
});

test("public HTML becomes plain text, without tags or script contents", () => {
  assert.equal(indexableText('<h2>Музей &laquo;Хлеб&raquo;</h2><script>alert(1)</script><p>Печь&nbsp;и &#1092;&#x43e;&#1088;&#1084;&#1099;</p>'),
    "Музей «Хлеб» Печь и формы");
  assert.equal(indexableText('<style>body{display:none}</style><p>Экспонаты</p>'), "Экспонаты");
  assert.equal(indexableText('<img onerror="alert(1)" src=x>'), "");
});

test("all words are required, match across title, category, excerpt, and BODY", () => {
  assert.deepEqual(rankSearch(published, "ИСТОРИЯ формы").map((item) => item.href), ["/museum/history/"]);
  assert.deepEqual(rankSearch(published, "пекарей мастерская").map((item) => item.href), ["/events/pekar/"]);
  assert.deepEqual(rankSearch(published, "доступная посещения").map((item) => item.href), ["/documents/rules/"]);
  assert.deepEqual(rankSearch(published, "пекарей рецепты"), []);
});

test("exact titles outrank body-only matches, deterministic tie-breaks and limits", () => {
  const input = [
    { title: "Афиша", href: "/events", section: "Раздел", excerpt: "" },
    { title: "Новости", href: "/news", section: "Новости", excerpt: "Афиша" },
    { title: "Другое", href: "/other", section: "Новости", excerpt: "Афиша" },
  ];
  assert.equal(rankSearch(input, "афиша")[0]?.href, "/events");
  assert.equal(rankSearch(input, "афиша", 1).length, 1);
  assert.equal(rankSearch(input, "афиша", 0).length, 0);
  assert.deepEqual(rankSearch(input, " "), []);
  const ties = rankSearch(input, "новости");
  assert.equal(ties[0]?.href, "/news");
});

test("duplicate URLs never appear twice; invalid or missing matches do not interfere", () => {
  const input = [
    { title: "Незначимый", href: "/same/", section: "Раздел", excerpt: "" },
    { title: "Хлеб", href: "/same/", section: "Материал", excerpt: "" },
    { title: "Хлеб", href: "/unique/", section: "Материал", excerpt: "" },
  ];
  assert.equal(rankSearch(input, "хлеб").length, 2);
  assert.equal(rankSearch(input, "хлеб").filter((x) => x.href === "/same/").length, 1);
});
