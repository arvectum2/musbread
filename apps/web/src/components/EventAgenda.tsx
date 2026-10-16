"use client";

import { useEffect, useMemo, useState } from "react";
import EventCard from "@/components/EventCard";
import { eventsForPeriod, localCalendarDay } from "@/data/event-archive";
import type { EventPeriod } from "@/data/event-archive";
import type { MuseumEvent } from "@/data/types";

/** Archive visibility changes by the visitor's calendar date, without a rebuild. */
export default function EventAgenda({
  events, buildDay, variant = "index",
}: {
  events: MuseumEvent[];
  buildDay: string;
  variant?: "index" | "featured";
}) {
  // Same initial day on server and client avoids a midnight hydration mismatch.
  const [today, setToday] = useState(buildDay);
  const [period, setPeriod] = useState<EventPeriod>("upcoming");
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const refresh = () => setToday(localCalendarDay(new Date()));
    const initial = window.setTimeout(() => { refresh(); setReady(true); }, 0);
    // Refresh when the tab is reopened or while kept open across midnight.
    const onVisibility = () => { if (!document.hidden) refresh(); };
    document.addEventListener("visibilitychange", onVisibility);
    const tick = window.setInterval(refresh, 60_000);
    return () => {
      window.clearTimeout(initial);
      document.removeEventListener("visibilitychange", onVisibility);
      window.clearInterval(tick);
    };
  }, []);
  const upcoming = useMemo(() => eventsForPeriod(events, today, "upcoming"), [events, today]);
  const archived = useMemo(() => eventsForPeriod(events, today, "archive"), [events, today]);
  const filtered = useMemo(() => eventsForPeriod(events, today, period), [events, today, period]);
  const visible = variant === "featured" ? upcoming.slice(0, 3) : filtered;

  return <section className="event-agenda" aria-label={variant === "featured" ? "Ближайшие мероприятия" : "Список мероприятий"} data-ready={ready ? "true" : "false"}>
    {variant === "index" && <>
      <div className="event-periods" role="group" aria-label="Период мероприятий">
        <button type="button" aria-pressed={period === "upcoming"} onClick={() => setPeriod("upcoming")}>Предстоящие <span>({upcoming.length})</span></button>
        <button type="button" aria-pressed={period === "archive"} onClick={() => setPeriod("archive")}>Архив <span>({archived.length})</span></button>
        <button type="button" aria-pressed={period === "all"} onClick={() => setPeriod("all")}>Все <span>({events.length})</span></button>
      </div>
      <p className="event-period-explain">{period === "archive" ? "Прошедшие мероприятия — от новых к старым." : period === "upcoming" ? "Ближайшие мероприятия, включая сегодняшние." : "Все опубликованные мероприятия."}</p>
    </>}
    {visible.length > 0
      ? <div className="events-grid">{visible.map((event, index) => <EventCard event={event} index={index} key={event.slug} />)}</div>
      : <p className="event-period-empty" role="status">{variant === "featured" || period === "upcoming" ? "Предстоящих мероприятий пока нет. Проверьте архив или вернитесь позже." : period === "archive" ? "В архиве пока нет прошедших мероприятий." : "Опубликованных мероприятий пока нет."}</p>}
  </section>;
}
