import type {MetadataRoute} from "next";
import {robotsRules,siteSeoApproved} from "@/data/seo-routes";
export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return robotsRules(siteSeoApproved(process.env.MUSBREAD_SITE_APPROVED));
}
