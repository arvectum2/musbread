import {content, events, sections} from "./content";
import {menuGroups, guidePages} from "./navigation";
import {menuGroups as referenceGroups, guidePages as referencePages} from "./museum-reference";

/** TZ-189: a supplementary destination tooltip; it must never replace
 * the visible link name, aria-label or keyboard-accessible activation.
 * Unknown URLs are described by their host, NEVER trusted as museum content.
 */
export function museumLinkTitle(href:string):string|undefined{
  const value=href.trim();
  if(!value || value.startsWith("javascript:") || value.startsWith("data:")) return undefined;
  if(value==="#main") return "Перейти к основному содержимому страницы";
  if(value.startsWith("#")) return "Перейти к разделу текущей страницы";
  if(value.startsWith("tel:")) return "Позвонить по указанному номеру";
  if(value.startsWith("mailto:")) return "Отправить письмо по указанному адресу";
  if(/^https?:\/\//i.test(value)){
    try{
      const url=new URL(value);
      const host=url.hostname.replace(/^www\./,"");
      return "Перейти на внешний сайт "+host;
    }catch{return undefined;}
  }
  if(!value.startsWith("/") || value.startsWith("//")) return undefined;
  // URL query/hash never changes the destination article's canonical title.
  const path=value.split(/[?#]/,1)[0];
  if(path==="/") return "Открыть главную страницу Музея хлеба";
  const fixed:Record<string,string>={
    "/events/":"Открыть афишу музея и архив мероприятий",
    "/search/":"Открыть поиск по сайту музея",
    "/forms/feedback/":"Открыть форму связи с музеем",
    "/forms/excursion/":"Открыть форму запроса экскурсии",
  };
  if(fixed[path]) return fixed[path];
  const clean=path.replace(/^\/|\/$/g,"");
  const parts=clean.split("/");
  if(parts.length===1){
    const section=sections[parts[0] as keyof typeof sections];
    if(section) return "Открыть раздел «"+section.title+"»";
  }
  if(parts.length===2 && parts[0]==="events"){
    const event=events.find(e=>e.slug===parts[1]);
    if(event) return "Открыть событие «"+event.title+"»";
  }
  if(parts.length===2 && parts[0]==="guide"){
    const title=content.sections?.find(x=>x.slug===parts[1])?.title
      || menuGroups.find(x=>x.slug===parts[1])?.title
      || guidePages.find(x=>x.slug===parts[1])?.title
      // The stable reference footer/contacts can outlive a CMS-backed menu.
      // A reference label is not an assertion that the section was approved.
      || referenceGroups.find(x=>x.slug===parts[1])?.title
      || referencePages.find(x=>x.slug===parts[1])?.title;
    if(title) return "Открыть раздел «"+title+"»";
  }
  if(parts.length===2 && sections[parts[0] as keyof typeof sections]){
    const type=sections[parts[0] as keyof typeof sections].type;
    const entry=content.entries.find(e=>e.type===type && e.slug===parts[1]);
    if(entry) return "Открыть материал «"+entry.title+"»";
  }
  if(parts.length===3 && parts[0]==="en"){
    const type=sections[parts[1] as keyof typeof sections]?.type;
    const entry=content.entries.find(e=>e.type===type && e.slug===parts[2]);
    if(entry?.translations?.en) return "Open article: "+entry.translations.en.title;
  }
  return undefined; // never fabricate an unapproved page's title.
}
