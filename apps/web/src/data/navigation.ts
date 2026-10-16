import { buildPublicNavigationTree } from "./navigation-tree";
import { content } from "./content";
import {
  guidePages as referencePages,
  menuGroups as referenceGroups,
  type GuidePage,
  type MenuGroup,
  type SitePage,
} from "./museum-reference";

/**
 * MoonShine's approved section tree is authoritative when the export includes
 * it. Otherwise the date-stamped reference menu from the old museum site
 * remains a safe, explicit pre-award fallback.
 *
 * Every page retains stable /guide/<slug>/ URLs so moving a section does not
 * invalidate its URL. Deeply nested pages are presented beneath their root
 * top-level category; breadcrumbs include each actual ancestor.
 */
export type NavPage = GuidePage & {
  ancestors: readonly { slug: string; title: string }[];
};
type Section = NonNullable<typeof content.sections>[number];
const cmsSectionsPresent = content.sections !== undefined;
export const navigationTree = cmsSectionsPresent ? buildPublicNavigationTree(content.sections ?? []) : [];
const incoming = content.sections ?? [];
const bySlug = new Map(incoming.map((section) => [section.slug, section]));
const sort = (a: Section, b: Section) =>
  a.sort_order - b.sort_order || a.title.localeCompare(b.title, "ru");
const groupFor = (section: Section): Section | null => {
  let current: Section = section;
  const seen = new Set<string>([current.slug]);
  for (let depth = 0; current.parent_slug && depth <= incoming.length; depth++) {
    const parent = bySlug.get(current.parent_slug);
    if (!parent || seen.has(parent.slug)) return null;
    current = parent;
    seen.add(current.slug);
  }
  return current.parent_slug ? null : current;
};
const ancestry = (section: Section): { slug: string; title: string }[] => {
  const list: { slug: string; title: string }[] = [];
  let parentSlug = section.parent_slug;
  const visited = new Set<string>([section.slug]);
  while (parentSlug && !visited.has(parentSlug)) {
    const parent = bySlug.get(parentSlug);
    if (!parent) break;
    list.unshift({ slug: parent.slug, title: parent.title });
    visited.add(parent.slug);
    parentSlug = parent.parent_slug;
  }
  return list;
};
const roots = incoming.filter((s) => s.parent_slug === null).sort(sort);
const dynamicGroups: readonly MenuGroup[] = roots.map((root) => ({
  slug: root.slug,
  title: root.title,
  children: incoming
    .filter((section) => section.slug !== root.slug && groupFor(section)?.slug === root.slug)
    .sort(sort)
    .map((section): SitePage => ({
      slug: section.slug, title: section.title,
      legacyPath: section.legacy_path || undefined,
      tenderOnly: !section.legacy_path,
    })),
}));
const groupMap = new Map(dynamicGroups.map((group) => [group.slug, group]));
const dynamicPages: readonly NavPage[] = incoming
  .filter((section) => section.parent_slug !== null)
  .flatMap((section): NavPage[] => {
    const root = groupFor(section);
    const group = root ? groupMap.get(root.slug) : undefined;
    if (!group) return [];
    return [{
      slug: section.slug,
      title: section.title,
      legacyPath: section.legacy_path || undefined,
      tenderOnly: !section.legacy_path,
      group,
      href: "/guide/" + section.slug + "/",
      ancestors: ancestry(section),
    }];
  });

export const menuGroups: readonly MenuGroup[] = cmsSectionsPresent
  ? dynamicGroups : referenceGroups;
export const guidePages: readonly NavPage[] = cmsSectionsPresent
  ? dynamicPages : referencePages.map((page) => ({
      ...page,
      ancestors: [{ slug: page.group.slug, title: page.group.title }],
    }));
export const findGuidePage = (slug: string) => guidePages.find((p) => p.slug === slug);
export const findMenuGroup = (slug: string) => menuGroups.find((g) => g.slug === slug);
export const usesCmsNavigation = cmsSectionsPresent;
