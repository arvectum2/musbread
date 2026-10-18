/** Only independently source-verified original museum canonical page URLs.
 * Historic Drupal /node/N URLs belong to the 301 map, never sitemap.
 * Placeholder/stale demo CMS pages and old event sessions are excluded.
 */
import latestNews from "./official-museum-news.json";
import historicNews from "./official-museum-news-archive.json";
import currentExhibitions from "./official-exhibition-details.json";
import archivedExhibitions from "./official-exhibition-archive.json";
import newsExhibitions from "./official-exhibition-news-linked.json";
import nodeExhibitions from "./official-node-linked-exhibitions.json";
import museumExcursions from "./official-excursion-programs.json";
import museumWorkshops from "./official-workshop-pages.json";
import museumRooms from "./official-exposition-rooms.json";
import originalSections from "./official-original-legacy-sections.json";
import linkedPages from "./official-museum-crosslink-pages.json";
import deeperPages from "./official-deep-museum-pages.json";

const officialSourceUrls=[
 ...latestNews.articles,...historicNews.articles,
 ...currentExhibitions.exhibitions,...archivedExhibitions.exhibitions,
 ...newsExhibitions.exhibitions,...nodeExhibitions.exhibitions,
 ...museumExcursions.programs,...museumWorkshops.programs,
 ...museumRooms.rooms,...originalSections.sections,
 ...linkedPages.pages,...deeperPages.pages,
].map(item=>item.source_url);

/** For future *approved* domain cutover only. Current prototype stays noindex. */
export function verifiedOriginalMuseumPaths():string[]{
 const result=officialSourceUrls.map(url=>{
   const parsed=new URL(url);
   if(parsed.protocol!=="https:"||parsed.hostname!=="muzei-xleb.ru"
      ||parsed.search||parsed.hash||parsed.username||parsed.password){
     throw new Error("Museum source provenance URL is not the official canonical domain: "+url);
   }
   if(!/^\/(?:[a-z0-9-]+\/)*[a-z0-9-]+$/.test(parsed.pathname)){
     throw new Error("Unsafe canonical original museum source page path: "+url);
   }
   return parsed.pathname;
 });
 if(result.length!==467||new Set(result).size!==467){
   throw new Error("All 467 original source URLs must remain distinct and verified before sitemap inclusion");
 }
 return [...result].sort((a,b)=>a.localeCompare(b,"en"));
}
