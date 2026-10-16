import assert from "node:assert/strict";
import test from "node:test";
import { buildPublicSearchIndex, indexableText, normalizeSearch, rankSearch, type SearchItem } from "./search-core.ts";

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


test("TZ-120/177: every public route, EN translation and attachment title join the index", () => {
  const hash = "a".repeat(64);
  const publishedFile = `/documents/${hash}.pdf`;
  const demoSnapshot = {
    schema_version: 1, site: { name: "Музей", subtitle: "История", description: "История хлеба в городе" },
    events: [{ slug: "lecture", title: "Лекция", category: "Наука", date: "2026-11-09", excerpt: "Программа", body: "Старинные печи" }],
    entries: [{
      type: "document" as const, slug: "rules", title: "Документы для посещения", h1: "Справки", parent_slug: null,
      excerpt: "Памятка посетителю", body: "<p>Часы работы музея</p>", sort_order: 0,
      seo_title: null, seo_description: null,
      documents: [
        { href: publishedFile, label: "Правила посещения с коляской", format: "pdf" as const, size_bytes: 100 },
        { href: "/documents/private-draft.pdf", label: "Чужой скрытый файл", format: "pdf" as const, size_bytes: 400 },
        { href: "/https://example.com/leak.pdf", label: "Недопустимая ссылка", format: "pdf" as const, size_bytes: 500 },
      ],
      media: [{ src: "/media/picture.webp", alt: "Вход для посетителей", caption: "Колокольня рядом", width: 40, height: 40 }],
      translations: { en: { title: "Visitor rules", excerpt: "Accessible entrance", body: "<p>Wheelchair ramp</p>", seo_title: null, seo_description: null } },
    }],
  };
  const tree = {
    menuGroups: [{ slug: "museum", title: "Музей", children: [{ title: "История" }] }],
    guidePages: [{ title: "История", href: "/guide/museum-history/", group: { title: "Музей" } }],
    guideSearchText: { "/guide/museum-history/": "195009, Михайлова, 2" },
  };
  const index = buildPublicSearchIndex(demoSnapshot, tree);
  const by = (q: string) => rankSearch(index, q, 50).map(item => item.href);
  assert.ok(by("правила коляской").includes(publishedFile), "public attached PDF directly discoverable");
  assert.ok(by("правила коляской").includes("/documents/rules/"), "parent page also searchable by attached metadata");
  assert.ok(by("wheelchair ramp").includes("/en/documents/rules/"), "English route only for published full translation");
  assert.ok(by("колокольня").includes("/documents/rules/"), "public photo description searchable via parent");
  assert.ok(by("печи").includes("/events/lecture/"));
  assert.ok(by("город").includes("/"));
  assert.ok(by("история").includes("/guide/museum-history/"));
  assert.ok(by("Михайлова").includes("/guide/museum-history/"));
  assert.ok(by("документы").includes("/documents/"));
  assert.ok(by("афиша").includes("/events/"));
  assert.equal(index.find(item => item.href === publishedFile)?.download, true);
  assert.equal(by("чужой скрытый файл").length, 0, "invalid/unpublished file paths never get indexed");
  assert.equal(index.some(item => item.href.includes("private-draft") || item.href.includes("https://")), false);
  assert.equal(new Set(index.map(item => item.href)).size, index.length, "index URLs are unique in this fixture");
  assert.ok(index.every(item => item.href.startsWith("/") && !item.href.startsWith("//")));
});

test("TZ-177: drafts and incomplete translations are not magically indexed", () => {
  const snapshot = { schema_version: 1, site: {name: "Тест", description: "Тест", subtitle: ""}, events: [], entries: [
    { type: "news" as const, slug: "russian-only", title: "Публичная новость", h1: null, parent_slug: null,
      excerpt: "", body: "Русский текст", seo_title: null, seo_description: null, sort_order: 0 },
  ] };
  const index = buildPublicSearchIndex(snapshot, { menuGroups: [], guidePages: [] });
  assert.ok(index.some(item => item.href === "/news/russian-only/"));
  assert.equal(index.some(item => item.href.startsWith("/en/")), false);
  assert.deepEqual(rankSearch(index,"приватный черновик"),[]);
});
