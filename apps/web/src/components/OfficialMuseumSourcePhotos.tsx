/**
 * Source-first prototype: show the very same photos published by the museum.
 * No generated substitute, no third-party stock; images stay at their original
 * muzei-xleb.ru URL so the current museum masters are used without rehosting.
 */
export type OriginalMuseumPhoto = {url:string;alt?:string};

function museumPhoto(url:string):boolean {
  try {
    const u=new URL(url);
    return u.protocol==="https:" && u.hostname==="muzei-xleb.ru"
      && u.pathname.startsWith("/sites/default/files/")
      && /\.(?:jpe?g|png|webp)$/i.test(u.pathname);
  }catch{return false;}
}

export default function OfficialMuseumSourcePhotos({photos, label,limit=4}:{
  photos:readonly OriginalMuseumPhoto[]|undefined;
  label:string;
  limit?:number;
}){
  const checked=(photos || []).filter(p=>museumPhoto(p.url)).slice(0,limit);
  if(checked.length===0)return null;
  return <div className="official-museum-source-photos" aria-label={`Фотографии музея: ${label}`}>
    {checked.map((photo,index)=><a href={photo.url} key={photo.url}
      target="_blank" rel="noopener noreferrer"
      aria-label={`Открыть оригинальное фото музея ${index+1}: ${photo.alt?.trim() || label}`}>
      {/* Original museum images are external documentary references, not app assets. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={photo.url} alt={photo.alt?.trim() || `${label} — фото музея ${index+1}`}
        loading="lazy" decoding="async" width="420" height="280"/>
    </a>)}
  </div>;
}
