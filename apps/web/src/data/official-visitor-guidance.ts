import snapshot from "./official-visitor-guidance.json";
import faq from "./official-visitor-faq.json";

type MuseumVisitorSnapshot = {
  path: string;
  source_url: string;
  title: string;
  html: string;
  html_sha256: string;
  captured_utc: string;
  document_links: {url:string;label:string}[];
};

export const officialVisitorGuidance = snapshot.pages as MuseumVisitorSnapshot[];
export const officialExcursionGuidance = officialVisitorGuidance.find(x=>x.path==="/ekskursii")!;
export const officialOpeningHours = officialVisitorGuidance.find(x=>x.path==="/chasy-raboty")!;
export type OfficialVisitorFAQ = {
  id:string;
  question:string;
  answer:string;
  source_path:string;
  source_url:string;
  source_html_sha256:string;
  source_phrases:string[];
};
export const officialVisitorFAQ = faq.questions as OfficialVisitorFAQ[];
