export interface MuseumRelatedEntry {
  title: string;
  type: "page" | "news" | "excursion" | "exhibition" | "document";
  href: string;
}
export interface MuseumRelatedEvent {
  title: string;
  href: string;
}
export interface MuseumEvent {
  slug: string;
  title: string;
  h1?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
  category: string;
  section_slug?: string;
  date: string;
  ends_on?: string | null;
  related_entries?: MuseumRelatedEntry[];
  excerpt: string;
  body: string;
}
export interface MuseumPublishedImage {
  src: string;
  alt: string;
  caption: string | null;
  long_description?: string | null;
  width: number;
  height: number;
}
export interface MuseumPublishedDocument {
  href: string;
  label: string;
  format: "pdf" | "docx" | "xlsx";
  size_bytes: number;
  accessibility_reviewed?: boolean;
  accessibility_note?: string | null;
}
export interface MuseumEntryEnglish {
  title: string;
  excerpt: string | null;
  body: string;
  seo_title: string | null;
  seo_description: string | null;
  h1?: string | null;
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
  related_entries?: MuseumRelatedEntry[];
  related_events?: MuseumRelatedEvent[];
  media?: MuseumPublishedImage[];
  documents?: MuseumPublishedDocument[];
  translations?: { en: MuseumEntryEnglish };
}
export interface PublishedSection {
  slug: string;
  title: string;
  h1?: string | null;
  seo_title?: string | null;
  seo_description?: string | null;
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
  visitor_contacts?: {
    address: string; metro: string; phone: string; phone_href: string;
    email: string; opening_hours: string; admission_hours: string;
    closed_day: string; sanitary_day: string;
  };
  fixed_page_seo?: Record<string, {
    seo_title?: string | null;
    seo_description?: string | null;
    h1?: string | null;
  }>;
}
