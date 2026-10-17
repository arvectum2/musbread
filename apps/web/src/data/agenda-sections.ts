import type { MuseumEvent } from "./types";

/** Section-specific agendas from the published CMS snapshot ONLY.
 * Never infer ticket eligibility, age suitability or invent museum events.
 * Category names are explicit editor options; slug is exact CMS section id. */
export const agendaSectionCategories = {
  "agenda-excursions": ["Экскурсия", "Обзорная экскурсия", "Интерактивная экскурсия", "Тематическая экскурсия"],
  "agenda-children": ["Детям", "Для детей", "Детская экскурсия", "Детский мастер-класс", "Детское мероприятие"],
  "agenda-exhibitions": ["Выставка", "Передвижная выставка", "Временная выставка"],
  "agenda-meetings": ["Встреча", "Лекция", "Презентация"],
  "agenda-festivals": ["Фестиваль"],
  "agenda-workshops": ["Мастер-класс", "Мастер-класс для взрослых", "Мастер-класс для детей"],
} as const;

export type AgendaSection = keyof typeof agendaSectionCategories | "agenda-archive";
export function isAgendaSection(value: string): value is AgendaSection {
  return value === "agenda-archive" || Object.hasOwn(agendaSectionCategories, value);
}
const childSections = new Set([
  "children", "agenda-children", "children-interactive",
  "children-thematic", "children-workshops",
]);

export function publishedEventsForAgendaSection(
  source: readonly MuseumEvent[], section: AgendaSection,
): MuseumEvent[] {
  if (section === "agenda-archive") return [...source];
  return source.filter(event => {
    // An explicitly approved CMS child-page assignment outranks a generic
    // "Экскурсия" category. But it does not imply that random excursions
    // belong to children's programmes.
    if (section === "agenda-children" && event.section_slug && childSections.has(event.section_slug))
      return true;
    if (event.section_slug === section) return true;
    const allowed: readonly string[] = agendaSectionCategories[section];
    return allowed.includes(event.category.trim());
  });
}
