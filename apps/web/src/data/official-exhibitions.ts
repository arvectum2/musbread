import indexes from "./official-exhibition-indexes.json";
import details from "./official-exhibition-details.json";
import archive from "./official-exhibition-archive.json";
import newsLinked from "./official-exhibition-news-linked.json";
import nodeLinked from "./official-node-linked-exhibitions.json";

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
  image_links:{url:string;alt:string}[];
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
  image_links:{url:string;alt:string}[];
  html_sha256:string;
  captured_utc:string;
  photos_rights_confirmed:false;
  image_only?:boolean;
};
export const officialExhibitionIndexes = indexes.indexes as MuseumExhibitionIndex[];
export const officialExhibitionNewsLinked = newsLinked.exhibitions as MuseumExhibitionSource[];
export const officialExhibitionNodeLinked = nodeLinked.exhibitions as MuseumExhibitionSource[];
export const officialExhibitionDetails = [...details.exhibitions,...archive.exhibitions,...officialExhibitionNewsLinked,...officialExhibitionNodeLinked] as MuseumExhibitionSource[];
export const officialExhibitionSourceSlugs = new Set(officialExhibitionDetails.map(x=>x.slug));
export function exhibitionSourceIndex(slug:string):MuseumExhibitionIndex|undefined {
  return officialExhibitionIndexes.find(x=>x.slug===slug);
}
