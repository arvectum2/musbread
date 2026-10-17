import Link from "@/components/MuseumLink";
import Image from "next/image";
import type { MuseumEvent } from "@/data/types";

export default function EventCard({event,index=0}:{event:MuseumEvent;index?:number}) {
  return <article className="event-card">
    {event.cover_image
      ? <div className="event-visual event-cover">
          <Link className="event-cover-link" href={"/events/"+event.slug+"/"}>
            <Image unoptimized loading="lazy" src={event.cover_image.src}
              width={event.cover_image.width} height={event.cover_image.height}
              alt={event.cover_image.alt} />
          </Link>
        </div>
      : <div className={"event-visual visual-"+(index%3)} aria-hidden="true">
          <div className="visual-grain">✳</div><span>{String(index+1).padStart(2,"0")}</span>
        </div>}
    <div className="event-card-content">
      <div className="event-meta">{event.category} <span aria-hidden="true">·</span> {event.date}{event.ends_on && event.ends_on !== event.date ? " — "+event.ends_on : ""}</div>
      <h3><Link href={"/events/"+event.slug+"/"}>{event.title}</Link></h3>
      <p>{event.excerpt}</p>
      <Link className="text-link" href={"/events/"+event.slug+"/"}>Подробнее <span aria-hidden="true">↗</span></Link>
    </div>
  </article>;
}
