import RichText from "@/components/RichText";
import MuseumInlineVideo from "@/components/MuseumInlineVideo";
import type {MuseumPublishedVideo} from "@/data/types";
import {trustedMuseumVideoEmbed} from "@/data/museum-video-security";

/** WYSIWYG-independent placement: a paragraph containing ONLY
 * [[museum-video:code]] is replaced by a verified approved video.
 * The CMS exporter refuses unknown/unapproved markers. Never parses iframe
 * HTML from editor and never trusts unapproved published.json rows.
 */
export default function MuseumRichBody({html,videos=[]}:{
  html:string; videos?:MuseumPublishedVideo[];
}){
  const parts=html.split(/<p(?:\s[^>]*)?>\s*\[\[museum-video:([a-z0-9]+(?:-[a-z0-9]+)*)\]\]\s*<\/p>/gi);
  if(parts.length===1)return <RichText html={html}/>;
  const byCode=new Map(videos.map(v=>[v.code,v]));
  return <div className="museum-rich-video-content">
    {parts.map((part,index)=>{
      if(index%2===0)return part.trim()
        ? <RichText key={"text-"+index} html={part}/>
        : null;
      const video=byCode.get(part);
      // Published snapshots should already have been rejected by the CMS
      // exporter; fail closed in the static frontend if someone edits JSON.
      return video && trustedMuseumVideoEmbed(video.embed_url)
        ? <MuseumInlineVideo key={"video-"+index} video={video}/>
        : <p key={"video-"+index} role="status">
            Видеоматериал недоступен: публикация не подтверждена.
          </p>;
    })}
  </div>;
}
