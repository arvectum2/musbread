import type { MuseumSnapshot, MuseumEntry } from "./types";

/** Deterministic offline search over ALREADY PUBLISHED static content only. */
export type SearchItem = {
  title: string;
  href: string;
  section: string;
  excerpt: string;
  /** Plain, public text. Never rendered as HTML or fetched from the CMS. */
  bodyText?: string;
  /** Content-addressed, downloadable public attachment, not a Next.js route. */
  download?: boolean;
};

const htmlEntities: Record<string, string> = {
  amp: "&", quot: '"', apos: "'", lt: "<", gt: ">", nbsp: " ",
  laquo: "«", raquo: "»", mdash: "—", ndash: "–", hellip: "…",
};

/** Convert sanitized publication HTML to searchable plain text, not to markup. */
export function indexableText(html: string): string {
  return html
    .replace(/<(script|style)\b[^>]*>[\s\S]*?<\/\1\s*>/gi, " ")
    .replace(/<[^>]*>/g, " ")
    .replace(/&(#(?:x[0-9a-f]+|\d+)|[a-z]+);/gi, (entity, code: string) => {
      if (!code.startsWith("#")) return htmlEntities[code.toLowerCase()] ?? " ";
      const numeric = code[1]?.toLowerCase() === "x"
        ? Number.parseInt(code.slice(2), 16) : Number.parseInt(code.slice(1), 10);
      return Number.isInteger(numeric) && numeric > 0 && numeric <= 0x10ffff &&
        !(numeric >= 0xd800 && numeric <= 0xdfff) && numeric >= 32
        ? String.fromCodePoint(numeric) : " ";
    })
    .replace(/\s+/g, " ").trim();
}

export function normalizeSearch(input: string): string {
  return input.toLocaleLowerCase("ru").replaceAll("ё", "е")
    .replace(/[^\p{L}\p{N}]+/gu, " ").trim().replace(/\s+/g, " ");
}

/** All query words are required, title matches rank ahead of body-only matches. */
export function rankSearch(items: readonly SearchItem[], query: string, limit = 8): SearchItem[] {
  const phrase = normalizeSearch(query);
  if (phrase.length < 2 || limit <= 0) return [];
  const words = [...new Set(phrase.split(" ").filter(Boolean))];
  if (!words.length) return [];
  const distinct = new Set<string>();
  const ranked: { item: SearchItem; score: number }[] = [];
  for (const item of items) {
    if (distinct.has(item.href)) continue;
    const title = normalizeSearch(item.title);
    const section = normalizeSearch(item.section);
    const excerpt = normalizeSearch(item.excerpt);
    const body = normalizeSearch(item.bodyText ?? "");
    if (!words.every((word) => [title, section, excerpt, body].some((s) => s.includes(word)))) continue;
    distinct.add(item.href);
    let score = title === phrase ? 200 : title.startsWith(phrase) ? 100 : title.includes(phrase) ? 60 : 0;
    for (const word of words) {
      if (title.includes(word)) score += 25;
      if (section.includes(word)) score += 10;
      if (excerpt.includes(word)) score += 6;
      if (body.includes(word)) score += 2;
    }
    ranked.push({ item, score });
  }
  ranked.sort((a, b) => b.score - a.score || a.item.title.localeCompare(b.item.title, "ru") || a.item.href.localeCompare(b.item.href));
  return ranked.slice(0, limit).map(({ item }) => item);
}


const sectionPaths: Readonly<Record<MuseumEntry["type"], { route: string; title: string }>> = {
  page: { route: "museum", title: "Музей" },
  news: { route: "news", title: "Новости" },
  excursion: { route: "excursions", title: "Экскурсии" },
  exhibition: { route: "exhibitions", title: "Выставки" },
  document: { route: "documents", title: "Документы" },
};

/** Exact content-addressed URLs of attachments allowed by the CMS exporter. */
const publicAttachment = /^\/documents\/[a-f0-9]{64}\.(?:pdf|docx|xlsx)$/;

type SearchNavigation = {
  guideSearchText?: Readonly<Record<string, string>>;
  menuGroups: readonly { slug: string; title: string; children: readonly { title: string }[] }[];
  guidePages: readonly { title: string; href: string; group: { title: string }; legacyPath?: string }[];
};

/**
 * Construct complete static search results from the same published snapshot
 * that powers actual routes. Never read database, draft records or OS files.
 * A document's LABEL is searchable; binary PDF/Office contents are NOT parsed.
 */
export function buildPublicSearchIndex(snapshot: MuseumSnapshot, navigation: SearchNavigation): SearchItem[] {
  const items: SearchItem[] = [
    { title: "Главная", href: "/", section: "Главная", excerpt: snapshot.site.description, bodyText: snapshot.site.name + " " + snapshot.site.subtitle },
    ...navigation.menuGroups.map((group) => ({
      title: group.title, href: `/guide/${group.slug}/`, section: "Раздел",
      excerpt: group.children.map((child) => child.title).join(", "),
    })),
    ...navigation.guidePages.map((page) => ({
      title: page.title, href: page.href, section: page.group.title,
      excerpt: page.legacyPath ? "Справочный раздел музея" : "Раздел нового сайта",
      bodyText: navigation.guideSearchText?.[page.href] ?? "",
    })),
    ...Object.values(sectionPaths).map((section) => ({
      title: section.title, href: `/${section.route}/`, section: "Категория",
      excerpt: `Опубликованные материалы раздела «${section.title}»`,
    })),
    { title: "Афиша мероприятий", href: "/events/", section: "Афиша", excerpt: "Все мероприятия, предстоящие события и архив" },
    ...snapshot.events.map((event) => ({
      title: event.title, href: `/events/${event.slug}/`, section: "Афиша",
      excerpt: event.excerpt, bodyText: indexableText(event.body) + " " + event.category,
    })),
  ];

  for (const entry of snapshot.entries) {
    const section = sectionPaths[entry.type];
    if (!section) continue;
    const href = `/${section.route}/${entry.slug}/`;
    const attachments = (entry.documents ?? []).filter((doc) => publicAttachment.test(doc.href)
      && doc.href.endsWith(`.${doc.format}`) && doc.label.trim().length > 0);
    const extra = [
      ...attachments.map((doc) => `${doc.label} ${doc.format.toUpperCase()} ${doc.accessibility_note ?? ""}`),
      ...(entry.media ?? []).map((image) => `${image.alt} ${image.caption ?? ""}`),
    ].join(" ");
    items.push({
      title: entry.title, href, section: section.title,
      excerpt: entry.excerpt ?? "", bodyText: [entry.h1 ?? "", indexableText(entry.body), extra].join(" "),
    });
    for (const attachment of attachments) items.push({
      title: attachment.label, href: attachment.href, section: "Файл · " + section.title,
      excerpt: `${attachment.format.toUpperCase()} · Приложение к материалу «${entry.title}»`,
      bodyText: `${attachment.accessibility_note ?? ""} ${entry.title}`,
      download: true,
    });
    // No fallback to unpublished translated drafts. A translation only exists
    // in snapshot when CMS accepted a complete publicly approved version.
    if (entry.translations?.en) items.push({
      title: entry.translations.en.title,
      href: `/en/${section.route}/${entry.slug}/`,
      section: `English · ${section.title}`,
      excerpt: entry.translations.en.excerpt ?? "",
      bodyText: indexableText(entry.translations.en.body),
    });
  }
  return items;
}
