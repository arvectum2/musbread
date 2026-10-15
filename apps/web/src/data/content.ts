import snapshot from "./published.json";
import type { MuseumEntry, MuseumSnapshot } from "./types";

const typedSnapshot = snapshot as MuseumSnapshot;
const allowedTypes = ["page", "news", "excursion", "exhibition", "document"] as const;
function parseType(type: string): MuseumEntry["type"] {
  if (!allowedTypes.some((candidate) => candidate === type)) {
    throw new Error("Unexpected content type in static publication: " + type);
  }
  return type as MuseumEntry["type"];
}

export const content: MuseumSnapshot = {
  ...typedSnapshot,
  sections: typedSnapshot.sections,
  entries: typedSnapshot.entries.map((entry) => ({
    ...entry,
    type: parseType(entry.type),
  })),
};
export const events = content.events;
export const findEvent = (slug: string) => events.find((event) => event.slug === slug);


export const sections = {
  museum: { title: "Музей", type: "page" },
  news: { title: "Новости", type: "news" },
  excursions: { title: "Экскурсии", type: "excursion" },
  exhibitions: { title: "Выставки", type: "exhibition" },
  documents: { title: "Документы", type: "document" },
} as const;
export type MuseumSection = keyof typeof sections;
export const isMuseumSection = (section: string): section is MuseumSection =>
  Object.prototype.hasOwnProperty.call(sections, section);
export const entriesInSection = (section: MuseumSection) =>
  content.entries.filter((entry) => entry.type === sections[section].type);
export const findEntry = (section: MuseumSection, slug: string) =>
  entriesInSection(section).find((entry) => entry.slug === slug);
