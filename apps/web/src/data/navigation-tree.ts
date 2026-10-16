import type { PublishedSection } from "./types";

/** No CMS permissions, draft text or database IDs exist in this tree. */
export type PublicNavigationNode = {
  slug: string;
  title: string;
  parentSlug: string | null;
  children: PublicNavigationNode[];
};

/** Construct a nested, deterministic menu without editing React for new sections.
 * The CMS exporter performs server-side ancestor/status checks; fail CLOSED here
 * on an inconsistent static snapshot rather than accidentally showing or looping.
 */
export function buildPublicNavigationTree(sections: readonly PublishedSection[]): PublicNavigationNode[] {
  const bySlug = new Map<string, PublicNavigationNode>();
  for (const section of sections) {
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(section.slug) || bySlug.has(section.slug)) {
      throw new Error("Invalid or duplicate published navigation slug");
    }
    bySlug.set(section.slug, {slug: section.slug, title: section.title, parentSlug: section.parent_slug, children: []});
  }
  // Validate complete ancestry (missing parents and cycles fail closed).
  for (const section of sections) {
    const seen = new Set<string>();
    let cursor: string | null = section.slug;
    while (cursor) {
      if (seen.has(cursor)) throw new Error("Published navigation cycle");
      seen.add(cursor);
      const current = bySlug.get(cursor);
      if (!current) throw new Error("Published navigation ancestor missing");
      cursor = current.parentSlug;
    }
  }
  const sortKey = new Map(sections.map(s => [s.slug, s.sort_order]));
  const compare = (a: PublicNavigationNode, b: PublicNavigationNode) =>
    (sortKey.get(a.slug) ?? 0) - (sortKey.get(b.slug) ?? 0) || a.title.localeCompare(b.title,"ru") || a.slug.localeCompare(b.slug);
  const roots: PublicNavigationNode[] = [];
  for (const node of bySlug.values()) {
    if (node.parentSlug) bySlug.get(node.parentSlug)!.children.push(node);
    else roots.push(node);
  }
  const sortBranch = (branch: PublicNavigationNode[]) => {
    branch.sort(compare);
    for (const node of branch) sortBranch(node.children);
  };
  sortBranch(roots);
  return roots;
}

export function findPublicNavigationNode(roots: readonly PublicNavigationNode[], slug: string): PublicNavigationNode | undefined {
  for (const node of roots) {
    if (node.slug === slug) return node;
    const nested = findPublicNavigationNode(node.children, slug);
    if (nested) return nested;
  }
  return undefined;
}
