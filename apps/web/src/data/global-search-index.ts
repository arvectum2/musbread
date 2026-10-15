import { content, events, sections } from "./content";
import { guidePages, menuGroups } from "./navigation";

export type SearchItem = { title: string; href: string; section: string; excerpt: string };
export const searchItems: readonly SearchItem[] = [
  ...menuGroups.map((g) => ({ title: g.title, href: "/guide/" + g.slug + "/", section: "Раздел", excerpt: g.children.map((x) => x.title).join(", ") })),
  ...guidePages.map((p) => ({ title: p.title, href: p.href, section: p.group.title, excerpt: p.legacyPath ? "Справочный раздел музея" : "Раздел нового сайта" })),
  ...events.map((e) => ({ title: e.title, href: "/events/" + e.slug + "/", section: "Афиша", excerpt: e.excerpt })),
  ...content.entries.flatMap((entry) => Object.entries(sections)
    .filter(([, section]) => section.type === entry.type)
    .map(([section]) => ({ title: entry.title, href: "/" + section + "/" + entry.slug + "/", section: sections[section as keyof typeof sections].title, excerpt: entry.excerpt ?? "" }))),
];
export function museumSearch(query: string, limit = 8): SearchItem[] {
  const norm = (s: string) => s.toLocaleLowerCase("ru").replaceAll("ё", "е").trim();
  const q = norm(query);
  if (q.length < 2) return [];
  const scored = searchItems.map((item) => {
    const title = norm(item.title);
    const text = norm(item.excerpt + " " + item.section);
    const weight = title.startsWith(q) ? 3 : title.includes(q) ? 2 : text.includes(q) ? 1 : 0;
    return { item, weight };
  }).filter((row) => row.weight > 0).sort((a, b) => b.weight - a.weight || a.item.title.localeCompare(b.item.title, "ru"));
  return scored.slice(0, limit).map((row) => row.item);
}
