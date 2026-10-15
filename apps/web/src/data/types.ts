export interface MuseumEvent {
  slug: string;
  title: string;
  category: string;
  date: string;
  excerpt: string;
  body: string;
}
export interface MuseumSnapshot {
  schema_version: number;
  site: { name: string; subtitle: string; description: string };
  events: MuseumEvent[];
}
