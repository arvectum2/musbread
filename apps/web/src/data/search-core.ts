/** Deterministic offline search over ALREADY PUBLISHED static content only. */
export type SearchItem = {
  title: string;
  href: string;
  section: string;
  excerpt: string;
  /** Plain, public text. Never rendered as HTML or fetched from the CMS. */
  bodyText?: string;
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
