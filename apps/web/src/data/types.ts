export interface MuseumEvent {
  slug: string;
  title: string;
  category: string;
  date: string;
  excerpt: string;
  body: string;
}
export interface MuseumPublishedImage {
  src: string;
  alt: string;
  caption: string | null;
  width: number;
  height: number;
}
export interface MuseumPublishedDocument {
  href: string;
  label: string;
  format: "pdf" | "docx" | "xlsx";
  size_bytes: number;
}
export interface MuseumEntryEnglish {
  title: string;
  excerpt: string | null;
  body: string;
  seo_title: string | null;
  seo_description: string | null;
}
export interface MuseumEntry {
  type: "page" | "news" | "excursion" | "exhibition" | "document";
  slug: string;
  title: string;
  h1: string | null;
  parent_slug: string | null;
  section_slug?: string;
  excerpt: string | null;
  body: string;
  seo_title: string | null;
  seo_description: string | null;
  sort_order: number;
  media?: MuseumPublishedImage[];
  documents?: MuseumPublishedDocument[];
  translations?: { en: MuseumEntryEnglish };
}
export interface PublishedSection {
  slug: string;
  title: string;
  parent_slug: string | null;
  sort_order: number;
  legacy_path: string | null;
}
export interface MuseumSnapshot {
  schema_version: number;
  site: { name: string; subtitle: string; description: string };
  events: MuseumEvent[];
  entries: MuseumEntry[];
  sections?: PublishedSection[];
}
