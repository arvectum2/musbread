/** Secondary defence for a hand-edited static published.json. The producer
 * still validates all trusted iframe destinations in PHP before writing.
 */
export function trustedMuseumVideoEmbed(value:string):boolean{
  try{
    const u=new URL(value);
    if(u.protocol!=="https:"
      ||!["vk.com","vkvideo.ru"].includes(u.hostname)
      ||u.username||u.password||u.port||u.hash
      ||u.pathname!=="/video_ext.php")return false;
    const keys=[...u.searchParams.keys()];
    if(new Set(keys).size!==keys.length
      ||keys.some(k=>!["oid","id","hd","hash"].includes(k)))return false;
    const oid=u.searchParams.get("oid");
    const id=u.searchParams.get("id");
    const hd=u.searchParams.get("hd");
    const hash=u.searchParams.get("hash");
    return !!oid && !!id && /^-\d{1,12}$/.test(oid) && /^\d{5,16}$/.test(id)
      &&(hd===null||/^[123]$/.test(hd))
      &&(hash===null||/^[a-f0-9]{16,64}$/.test(hash));
  }catch{return false;}
}
