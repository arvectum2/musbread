import type { MetadataRoute } from "next";
import {content} from "@/data/content";
import {guidePages,menuGroups,usesCmsNavigation} from "@/data/navigation";
import {publishedSitemapPaths,siteSeoApproved,sitemapUrls} from "@/data/seo-routes";
export const dynamic = "force-static";

/** Only approved, actually published pages; draft sitemap remains empty. */
export default function sitemap(): MetadataRoute.Sitemap {
  const approved = siteSeoApproved(process.env.MUSBREAD_SITE_APPROVED);
  if (!approved) return [];
  return sitemapUrls(publishedSitemapPaths(content,menuGroups,guidePages,usesCmsNavigation),approved);
}
