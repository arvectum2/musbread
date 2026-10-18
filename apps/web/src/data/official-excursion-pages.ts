import source from "./official-excursion-pages.json";

/** Official current museum edition; pictures only captured as rights-unverified metadata. */
export type OfficialExcursionSource = {
  cms_slug: string;
  path: string;
  source_url: string;
  title: string;
  captured_utc: string;
  html: string;
  html_sha256: string;
  text_sha256: string;
  text_length: number;
  document_links: {url:string;label:string}[];
  image_links: {url:string;alt:string}[];
  photos_rights_confirmed: false;
};

export const officialExcursionPages = source.pages as OfficialExcursionSource[];
export function officialExcursionBySlug(slug:string){
  return officialExcursionPages.find(page => page.cms_slug === slug);
}
