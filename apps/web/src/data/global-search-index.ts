import { content, events, sections } from "./content";
import { guidePages, menuGroups } from "./navigation";
import { indexableText, rankSearch, type SearchItem } from "./search-core";

/** Content is from the public SHA256-verified snapshot; never query private CMS. */
export const searchItems: readonly SearchItem[] = [
  ...menuGroups.map((g) => ({ title: g.title, href: "/guide/" + g.slug + "/", section: "Раздел", excerpt: g.children.map((x) => x.title).join(", ") })),
  ...guidePages.map((p) => ({ title: p.title, href: p.href, section: p.group.title, excerpt: p.legacyPath ? "Справочный раздел музея" : "Раздел нового сайта" })),
  ...events.map((e) => ({ title: e.title, href: "/events/" + e.slug + "/", section: "Афиша", excerpt: e.excerpt, bodyText: indexableText(e.body) })),
  ...content.entries.flatMap((entry) => Object.entries(sections)
    .filter(([, section]) => section.type === entry.type)
    .map(([section]) => ({ title: entry.title, href: "/" + section + "/" + entry.slug + "/", section: sections[section as keyof typeof sections].title, excerpt: entry.excerpt ?? "", bodyText: indexableText(entry.body) }))),
];

export function museumSearch(query: string, limit = 8): SearchItem[] {
  return rankSearch(searchItems, query, limit);
}
