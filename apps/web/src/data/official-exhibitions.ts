import indexes from "./official-exhibition-indexes.json";
import details from "./official-exhibition-details.json";
import archive from "./official-exhibition-archive.json";

/** Verified current museum site. No photos republished without source rights. */
export type MuseumExhibitionIndexItem = {
  source_url:string;
  path:string;
  title:string;
  date_text:string|null;
};
export type MuseumExhibitionIndex = {
  slug:string;
  path:string;
  source_url:string;
  title:string;
  captured_utc:string;
  html_sha256:string;
  linked_exhibitions:MuseumExhibitionIndexItem[];
  images_rights_confirmed:false;
};
export type MuseumExhibitionSource = {
  slug:string;
  category_slug:string;
  source_url:string;
  path:string;
  title:string;
  intro:string;
  html:string;
  html_sha256:string;
  captured_utc:string;
  photos_rights_confirmed:false;
  image_only?:boolean;
};
export const officialExhibitionIndexes = indexes.indexes as MuseumExhibitionIndex[];
export const officialExhibitionDetails = [...details.exhibitions,...archive.exhibitions] as MuseumExhibitionSource[];
export const officialExhibitionSourceSlugs = new Set(officialExhibitionDetails.map(x=>x.slug));
export function exhibitionSourceIndex(slug:string):MuseumExhibitionIndex|undefined {
  return officialExhibitionIndexes.find(x=>x.slug===slug);
}
