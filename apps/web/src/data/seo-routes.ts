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

/** Two independent explicit approvals must exist before any SEO publishing.
 * Prevent enabling public indexing by changing a single prototype env flag.
 */
export function siteSeoApproved(value: string | undefined, releaseHost: string | undefined): boolean {
  return value==="true" && releaseHost==="muzei-xleb.ru";
}

/** Only proven ORIGINAL source-backed pages can override default demo noindex;
 * robots.txt and the global prototype metadata retain the block otherwise.
 */
export function verifiedSourceRobots(approval:string|undefined,releaseHost:string|undefined){
 const published=siteSeoApproved(approval,releaseHost);
 return {index:published,follow:published};
}

export function sitemapUrls(paths: readonly string[], approved: boolean, base = "https://muzei-xleb.ru") {
  if (!approved) return [];
  if (base !== "https://muzei-xleb.ru") throw new Error("Only the original customer museum domain may enter canonical sitemap");
  if (new Set(paths).size!==paths.length || paths.some(path=>!/^\/(?:[a-z0-9-]+\/)*[a-z0-9-]+\/?$|^\/$/.test(path))){
    throw new Error("Only distinct clean original museum URL paths permitted in production sitemap");
  }
  return paths.map(path=>({url:base+path,changeFrequency:"weekly" as const}));
}

export function robotsRules(approved:boolean) {
  return { rules:[{userAgent:"*",allow: approved ? "/" : undefined,
    disallow:approved?undefined:"/"}], sitemap:approved?"https://muzei-xleb.ru/sitemap.xml":undefined };
}
