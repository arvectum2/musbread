import programs from "./official-excursion-programs.json";

export type OfficialMuseumProgram = {
  slug: string;
  category_slug: string;
  source_url: string;
  title: string;
  source_label: string;
  captured_utc: string;
  intro: string;
  html: string;
  html_sha256: string;
  text_length: number;
  image_links: {url:string;alt:string}[];
  document_links: {url:string;label:string}[];
  photos_rights_confirmed: false;
};
export const originalMuseumPrograms = programs.programs as OfficialMuseumProgram[];
export const excursionSourceCategories = [
  "excursion-interactive", "excursion-thematic", "excursion-theatrical",
] as const;
export function sourceProgramsForCategory(category:string): OfficialMuseumProgram[] {
  return originalMuseumPrograms.filter(p=>p.category_slug===category);
}
export function isProgramCategory(category:string):boolean {
  return excursionSourceCategories.some(slug=>slug===category);
}
export const originalMuseumProgramSlugs = new Set(originalMuseumPrograms.map(p=>p.slug));
