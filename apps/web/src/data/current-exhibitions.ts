import type { MuseumEvent } from "./types";
import { eventsForPeriod, validCalendarDay } from "./event-archive.ts";

/** The museum's published CMS event type, not content scraped or invented.
 * An exhibition is current ONLY if its start has arrived and its inclusive
 * end date has not passed. An exhibition without ends_on lasts one day.
 */
export function currentlyRunningExhibitions(events: readonly MuseumEvent[], today: string): MuseumEvent[] {
  if (!validCalendarDay(today)) return [];
  return eventsForPeriod(events.filter((event) =>
    event.category.trim().toLocaleLowerCase("ru") === "выставка"
    && validCalendarDay(event.date)
    && event.date <= today
  ), today, "upcoming");
}

export function futureExhibitions(events: readonly MuseumEvent[], today: string): MuseumEvent[] {
  if (!validCalendarDay(today)) return [];
  return eventsForPeriod(events.filter((event) =>
    event.category.trim().toLocaleLowerCase("ru") === "выставка"
    && validCalendarDay(event.date)
    && event.date > today
  ), today, "upcoming");
}
