import type { MuseumSnapshot } from "./types";

/** TZ-191: sitemap records are built solely from the verified public snapshot. */
export function publishedSitemapPaths(
  snapshot: MuseumSnapshot,
  menuGroups: readonly { slug: string }[],
  guidePages: readonly { href: string }[],
  usesCmsNavigation: boolean,
): string[] {
  const typeRoutes: Record<string,string> = {
    page: "museum", news: "news", excursion: "excursions",
    exhibition: "exhibitions", document: "documents",
  };
  const slugs = Object.values(typeRoutes);
  const paths = ["/", "/events/", ...slugs.map(s=>`/${s}/`),
    ...(usesCmsNavigation ? menuGroups.map(g=>`/guide/${g.slug}/`) : []),
    ...(usesCmsNavigation ? guidePages.map(g=>g.href) : []),
    ...snapshot.events.map(e=>`/events/${e.slug}/`),
    ...snapshot.entries.flatMap(e => {
      const route = typeRoutes[e.type];
      if (!route) return [];
      const links=[`/${route}/${e.slug}/`];
      if (e.translations?.en) links.push(`/en/${route}/${e.slug}/`);
      return links;
    }),
  ];
  // Independent of initial CMS insert order; stable metadata across builds.
  const clean = (path: string) => /^\/(?:[a-z0-9-]+\/)*$/.test(path);
  if (paths.some(path => !clean(path))) throw new Error("Unsafe sitemap path in published snapshot");
  return [...new Set(paths)].sort((a,b)=>a.localeCompare(b,"en"));
}

/** Pre-contract build MUST block indexing. Post-contract release opt-in only. */
export function siteSeoApproved(value: string | undefined): boolean { return value === "true"; }

export function sitemapUrls(paths: readonly string[], approved: boolean, base = "https://musbread.ru") {
  if (!approved) return [];
  if (base !== "https://musbread.ru") throw new Error("Approval required to change tender domain");
  return paths.map(path=>({url:base+path,changeFrequency:"weekly" as const}));
}

export function robotsRules(approved:boolean) {
  return { rules:[{userAgent:"*",allow: approved ? "/" : undefined,
    disallow:approved?undefined:"/"}], sitemap:approved?"https://musbread.ru/sitemap.xml":undefined };
}
