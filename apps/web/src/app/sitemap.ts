import type { MetadataRoute } from "next";
export const dynamic = "force-static";
import { content, events, sections } from "@/data/content";
import { guidePages, menuGroups, usesCmsNavigation } from "@/data/navigation";

/** Only actual published CMS/event pages, never interview-dependent guide placeholders. */
export default function sitemap(): MetadataRoute.Sitemap {
  if (process.env.MUSBREAD_SITE_APPROVED !== "true") return [];
  const base = "https://musbread.ru";
  const paths = [
    "/",
    ...(usesCmsNavigation ? menuGroups.map((group) => "/guide/" + group.slug + "/") : []),
    ...(usesCmsNavigation ? guidePages.map((page) => page.href) : []),
    ...Object.keys(sections).map((section) => "/" + section + "/"),
    ...events.map((event) => "/events/" + event.slug + "/"),
    ...content.entries.flatMap((entry) => Object.entries(sections)
      .filter(([, section]) => section.type === entry.type)
      .map(([section]) => "/" + section + "/" + entry.slug + "/")),
  ];
  return [...new Set(paths)].map((path) => ({
    url: base + path,
    changeFrequency: "weekly" as const,
  }));
}
