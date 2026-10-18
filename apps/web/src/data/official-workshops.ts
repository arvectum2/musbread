import source from "./official-workshop-pages.json";

export type OfficialMuseumWorkshop = {
  slug: string;
  path: string;
  source_url: string;
  title: string;
  intro: string;
  html: string;
  html_sha256: string;
  captured_utc: string;
  image_links:{url:string;alt:string}[];
  photos_rights_confirmed:false;
};
export const officialWorkshopIndex = source.index;
export const officialWorkshops = source.programs as OfficialMuseumWorkshop[];
export const officialWorkshopSlugs = new Set(officialWorkshops.map(p=>p.slug));
