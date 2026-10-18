import photoIndex from "./official-museum-photo-assets.json";
import newsIndexPhotos from "./official-news-index-photo-assets.json";

/** Map actual old official museum photo URLs to permanently self-hosted files. */
const photoLookup={...photoIndex.photos,...newsIndexPhotos.photos} as Record<string,{path:string;static_sha256:string}>;
export function localMuseumPhoto(url:string):string|null {
  try {
    const u=new URL(url);
    // Historical original article HTML sometimes uses obsolete http://...
    if(!["http:","https:"].includes(u.protocol) || u.hostname!=="muzei-xleb.ru")return null;
    const path=u.pathname.replace(/^\/sites\/default\/files\/styles\/[^/]+\/public\//,"/sites/default/files/");
    if(!path.startsWith("/sites/default/files/") || !/\.(jpe?g|png|webp)$/i.test(path))return null;
    const stableKey="https://muzei-xleb.ru"+path;
    const local=photoLookup[stableKey]?.path;
    return local && /^\/media\/museum-source\/[a-f0-9]{64}\.webp$/.test(local)?local:null;
  }catch{return null;}
}
