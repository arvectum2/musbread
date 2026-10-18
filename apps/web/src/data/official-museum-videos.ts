import source from "./official-museum-videos.json";

/** The actual published source categories and original VK/player links;
 * source URL is proof of museal use, not a license to rehost media.
 */
export type OfficialMuseumVideo = {
  id:string;
  title:string;
  source_page:string;
  source_iframe_src:string;
  embed_url:string|null;
  kind:"vk"|"external-mp4-link";
  video_owner_id?:string;
  hosted_in_museum_vk_group?:boolean;
  direct_file_url?:string;
  third_party_embed_requires_click:true;
};
export type OfficialVideoCategory={
  slug:"museum"|"exhibitions"|"unusual-tour";
  title:string;
  source_url:string;
  source_html_sha256:string;
  count:number;
  videos:OfficialMuseumVideo[];
};
export const originalMuseumVideos=source.groups as OfficialVideoCategory[];
export const originalMuseumVideosCount=source.video_count;
export const originalMuseumVkCount=source.vk_embeds;
export const originalMuseumDirectCount=source.external_mp4_file_links;
export const originalMuseumVideoCaptureDate=source.snapshot_utc;
