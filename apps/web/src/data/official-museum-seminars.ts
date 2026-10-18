import source from "./official-museum-seminars.json";

/** Real original museum seminars with actual dates and VK recording references.
 * Original-site presence is NOT a full-rights or caption/CC confirmation.
 */
export type OfficialSeminarVideo={
  original_iframe_src:string;
  embed_url:string;
  owner_id:string;
  is_museum_vk_channel:boolean;
  part_label:string;
};
export type OfficialMuseumSeminar={
  id:string;
  title:string;
  date_start:string;
  date_end:string|null;
  dated_range:boolean;
  index_source_url:string;
  index_detail_path:string;
  source_url:string;
  page_html_sha256:string;
  original_body_text:string;
  video_count:number;
  videos:OfficialSeminarVideo[];
  media_rehosted:false;
  photo_rights_confirmed:false;
};
export const officialMuseumSeminars=source.seminars as OfficialMuseumSeminar[];
export const officialSeminarSlugs=new Set(officialMuseumSeminars.map(s=>s.id));
export const officialSeminarIndex=source.index_url;
export const officialSeminarCount=source.count;
export const officialSeminarVideoCount=source.video_count;
