import source from "./official-science-sources.json";
import original from "./official-page-snapshots.json";

/** Institutional records only; NOT academic publications, seminars or object photos. */
export type MuseumScienceRecord={
  slug:string;
  source_url:string;
  title:string;
  captured_utc:string;
  html:string;
  html_sha256:string;
  text_length:number;
  documents:{url:string;label:string;format:"pdf"|"docx"}[];
  photos_rights_confirmed:false;
};
export const officialScienceInstitutionalRecords=source.pages as MuseumScienceRecord[];

/** The actual museum-published visitor-access policy, not an invented
 * researcher accreditation rule or guarantee of access to reserves. */
const officialPricingDocs=original.pages.find(p=>
  p.path==="/ceny-i-usloviya-predostavleniya-uslug")?.document_links??[];
export const museumCollectionsAccessDocument=officialPricingDocs.find(d=>
  d.url==="https://muzei-xleb.ru/sites/default/files/page/20260203112347-poryadok_dostupa.pdf");
