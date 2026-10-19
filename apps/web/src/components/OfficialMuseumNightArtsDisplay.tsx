"use client";

import { useEffect, useState, type ReactNode } from "react";
import MuseumAnchor from "@/components/MuseumAnchor";
import { localCalendarDay } from "@/data/event-archive";

const EVENT_DAY = "2026-11-03";

type Source = {
  title: string;
  published_on: string;
  source_url: string;
};

/** Only date-sensitive presentation hydrates in the browser.
 * Source HTML remains a server-rendered/sanitized React child.
 */
export default function OfficialMuseumNightArtsDisplay({
  buildDay, archiveOnly = false, original, children,
}: {
  buildDay: string;
  archiveOnly?: boolean;
  original: Source;
  children: ReactNode;
}) {
  const [today, setToday] = useState(buildDay);
  useEffect(() => {
    const refresh = () => setToday(localCalendarDay(new Date()));
    refresh();
    const onVisibility = () => { if (!document.hidden) refresh(); };
    document.addEventListener("visibilitychange", onVisibility);
    const tick = window.setInterval(refresh, 60_000);
    return () => {
      document.removeEventListener("visibilitychange", onVisibility);
      window.clearInterval(tick);
    };
  }, []);
  const isArchive = EVENT_DAY < today;
  if (archiveOnly && !isArchive) return null;

  return <section className="official-museum-programs official-source-event"
    aria-label="Официальный анонс Ночи искусств">
    <h2>{isArchive ? "Архив официальных анонсов" : "Подтверждённое событие по действующему сайту музея"}</h2>
    <article className="official-museum-program-card">
      <p className="official-museum-program-number">
        {isArchive ? "Мероприятие завершилось" : "Предстоящая программа по официальному источнику"}
      </p>
      <h3>{original.title}</h3>
      <p><strong>Программа «Петербург гостеприимный»</strong></p>
      <p><strong>3 ноября 2026 г., 18:00–20:00.</strong> Дата и часы — из текста
        действующего музея. Новость опубликована отдельно {original.published_on.split("-").reverse().join(".")}.</p>
      <details>
        <summary>Полное описание музейной программы</summary>
        <div className="official-museum-program-body">{children}</div>
      </details>
      <p><MuseumAnchor href={original.source_url} className="text-link"
        target="_blank" rel="noopener noreferrer">
        Официальный анонс музея ↗
      </MuseumAnchor></p>
      <p className="official-museum-program-warning">Перед посещением уточните
        запись, наличие мест и возможные изменения у музея.
        Эта карточка не осуществляет продажи билетов.</p>
    </article>
  </section>;
}
