/**
 * Self-hosted original museum image library. The SOURCE URL is provenance only.
 * Old Drupal/muzei-xleb.ru image requests must never appear in new site's HTML;
 * after cutover, all image bytes are served from our static Next.js deployment.
 */
import {localMuseumPhoto} from "@/data/museum-photo-assets";
import MuseumAnchor from "@/components/MuseumAnchor";

export type OriginalMuseumPhoto = {url:string;alt?:string};

export default function OfficialMuseumSourcePhotos({photos:items,label,limit=4}:{
  photos:readonly OriginalMuseumPhoto[]|undefined;
  label:string;
  limit?:number;
}){
  const checked=(items||[]).map(item=>({item,src:localMuseumPhoto(item.url)}))
    .filter((p):p is {item:OriginalMuseumPhoto;src:string}=>p.src!==null).slice(0,limit);
  if(checked.length===0)return null;
  return <div className="official-museum-source-photos" aria-label={`Фотографии музея: ${label}`}>
    {checked.map(({item,src},index)=><MuseumAnchor href={src} key={item.url}
      target="_blank" rel="noopener noreferrer"
      title={`Открыть фотографию ${index+1}: ${item.alt?.trim() || label}`}
      aria-label={`Открыть фотографию ${index+1}: ${item.alt?.trim() || label}`}>
      {/* All exported bytes are stored in this website's own static files. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={item.alt?.trim() || `${label} — фотография ${index+1}`}
        loading="lazy" decoding="async" width="420" height="280" />
    </MuseumAnchor>)}
  </div>;
}
