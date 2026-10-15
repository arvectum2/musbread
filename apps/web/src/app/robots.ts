import type { MetadataRoute } from "next";
export const dynamic = "force-static";

/** Pre-award remains private from search engines; production requires explicit approval. */
export default function robots(): MetadataRoute.Robots {
  const approved = process.env.MUSBREAD_SITE_APPROVED === "true";
  return {
    rules: [{ userAgent: "*", allow: approved ? "/" : undefined, disallow: approved ? undefined : "/" }],
    sitemap: approved ? "https://musbread.ru/sitemap.xml" : undefined,
  };
}
