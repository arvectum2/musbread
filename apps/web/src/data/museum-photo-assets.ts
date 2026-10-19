import photoIndex from "./official-museum-photo-assets.json";
import newsIndexPhotos from "./official-news-index-photo-assets.json";
import deeperNewsPhotos from "./official-deep-news-image-assets.json";
import originalExhibitionPhotos from "./official-historical-exhibition-image-assets.json";
import reviewedAlts from "./official-museum-reviewed-alt.json";

/** Map actual old official museum photo URLs to permanently self-hosted files. */
const photoLookup={...photoIndex.photos,...newsIndexPhotos.photos,...deeperNewsPhotos.photos,...originalExhibitionPhotos.photos} as Record<string,{path:string;static_sha256:string}>;
export function localMuseumPhoto(url:string):string|null {
  try {
    // Drupal HTML often stores original links as root-relative /sites/default/files/…
    // Resolve those against the known museum origin, not the preview hostname.
    const u=new URL(url,"https://muzei-xleb.ru");
    // Historical original article HTML sometimes uses obsolete http://...
    if(!["http:","https:"].includes(u.protocol) || u.hostname!=="muzei-xleb.ru")return null;
    const path=u.pathname.replace(/^\/sites\/default\/files\/styles\/[^/]+\/public\//,"/sites/default/files/");
    if(!path.startsWith("/sites/default/files/") || !/\.(jpe?g|png|webp)$/i.test(path))return null;
    const stableKey="https://muzei-xleb.ru"+path;
    const local=photoLookup[stableKey]?.path;
    return local && /^\/media\/museum-source\/[a-f0-9]{64}\.webp$/.test(local)?local:null;
  }catch{return null;}
}

/** Editorial drafts based on visually inspected ORIGINAL museum images.
 * Not official museum captions: keep any nonempty official source alt first.
 */
export function reviewedMuseumPhotoAlt(staticPath:string):string|null {
  if(!/^\/media\/museum-source\/[a-f0-9]{64}\.webp$/.test(staticPath))return null;
  const photos=reviewedAlts.photos as Record<string,string>;
  return photos[staticPath]?.trim() || null;
}

/** Manually read from ORIGINAL historical notices, NOT current opening hours. */
export function museumArchivalImageText(staticPath:string):string|null {
  if(!/^\/media\/museum-source\/[a-f0-9]{64}\.webp$/.test(staticPath))return null;
  const texts=reviewedAlts.archival_image_text as Record<string,string>;
  return texts[staticPath]?.trim() || null;
}
