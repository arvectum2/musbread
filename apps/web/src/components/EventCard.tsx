import Link from "next/link";
import type { MuseumEvent } from "@/data/types";
export default function EventCard({ event, index = 0 }: { event: MuseumEvent; index?: number }) {
  return <article className="event-card">
    <div className={`event-visual visual-${index % 3}`} aria-hidden="true">
      <div className="visual-grain">✳</div><span>{String(index + 1).padStart(2,"0")}</span>
    </div>
    <div className="event-card-content">
      <div className="event-meta">{event.category} <span aria-hidden="true">·</span> {event.date}{event.ends_on && event.ends_on !== event.date ? ` — ${event.ends_on}` : ""}</div>
      <h3><Link href={`/events/${event.slug}/`}>{event.title}</Link></h3>
      <p>{event.excerpt}</p>
      <Link className="text-link" href={`/events/${event.slug}/`}>Подробнее <span aria-hidden="true">↗</span></Link>
    </div>
  </article>;
}
