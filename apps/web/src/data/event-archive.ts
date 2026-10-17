import type { MuseumEvent } from "./types";

export type EventPeriod = "upcoming" | "archive" | "all";

/** Museum events have a calendar START date, not an end time or booking deadline. */
export function validCalendarDay(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00.000Z`);
  return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

/** A visitor's calendar day (timezone aware), independent from the static build date. */
export function localCalendarDay(now: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** Past events remain in the published snapshot, sitemap and detail URLs. */
export function eventsForPeriod(
  events: readonly MuseumEvent[],
  today: string,
  period: EventPeriod,
): MuseumEvent[] {
  const date = validCalendarDay(today) ? today : localCalendarDay(new Date());
  return events.filter((event) => {
    const unknown = !validCalendarDay(event.date);
    const end = event.ends_on && validCalendarDay(event.ends_on) ? event.ends_on : event.date;
    if (period === "archive") return !unknown && end < date;
    if (period === "upcoming") return unknown || end >= date;
    return true;
  }).sort((left, right) => {
    const first = validCalendarDay(left.date) ? left.date : "9999-12-31";
    const second = validCalendarDay(right.date) ? right.date : "9999-12-31";
    const delta = period === "archive" ? second.localeCompare(first) : first.localeCompare(second);
    return delta || left.slug.localeCompare(right.slug);
  });
}

/** Categories come ONLY from the approved CMS snapshot. We do not infer a
 * museum's programmes, group by substring, or manufacture unseen categories. */
export function eventCategories(events: readonly MuseumEvent[]): string[] {
  return Array.from(new Set(events.map((event) => event.category.trim())
    .filter((category) => category.length > 0)))
    .sort((a, b) => a.localeCompare(b, "ru"));
}

export function eventsForCategory(
  events: readonly MuseumEvent[], category: string,
): MuseumEvent[] {
  if (category === "") return [...events];
  return events.filter((event) => event.category.trim() === category);
}
