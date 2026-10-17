import {content} from "./content";
import type {Metadata} from "next";

/** Editor-approved SEO for fixed routes only. Article/event SEO is owned by
 * the respective CMS record; closed/draft records are absent from export. */
export function fixedPageSeo(path:string){
  return content.fixed_page_seo?.[path];
}
export function fixedPageMetadata(path:string,fallbackTitle:string,fallbackDescription?:string):Metadata{
  const value=fixedPageSeo(path);
  return {
    title: value?.seo_title?.trim() || fallbackTitle,
    description: value?.seo_description?.trim() || fallbackDescription,
  };
}
export function fixedPageH1(path:string,fallback:string):string{
  return fixedPageSeo(path)?.h1?.trim() || fallback;
}
