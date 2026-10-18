import source from "./official-museum-news.json";
import archive from "./official-museum-news-archive.json";

export type OfficialMuseumNewsItem = {
  slug:string;
  source_url:string;
  title:string;
  published_on:string; // date in original news URL, NOT the event date
  intro:string;
  html:string;
  html_sha256:string;
  image_links:{url:string;alt:string}[];
  photos_rights_confirmed:false;
  image_only?: boolean;
};
export const officialMuseumNews = source.articles as OfficialMuseumNewsItem[];
export const officialMuseumArchiveNews = archive.articles as OfficialMuseumNewsItem[];
export const officialMuseumNewsSlugs = new Set(officialMuseumNews.map(i=>i.slug));
export const museumNewsSourceIndex = source.index_url;
export const museumNewsSourceSnapshot = source.snapshot_utc;
