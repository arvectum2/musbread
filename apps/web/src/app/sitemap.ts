import type { MetadataRoute } from "next";
import {siteSeoApproved,sitemapUrls} from "@/data/seo-routes";
import {verifiedOriginalMuseumPaths} from "@/data/verified-original-museum-paths";
export const dynamic = "force-static";

/** Only approved, actually published pages; draft sitemap remains empty. */
export default function sitemap(): MetadataRoute.Sitemap {
  const approved = siteSeoApproved(process.env.MUSBREAD_SITE_APPROVED,process.env.MUSBREAD_RELEASE_HOST);
  if (!approved) return [];
  return sitemapUrls(verifiedOriginalMuseumPaths(),approved);
}
