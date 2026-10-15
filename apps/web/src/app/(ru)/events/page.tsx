import type { Metadata } from "next";
import Link from "next/link";
import EventCard from "@/components/EventCard";
import EventSearch from "@/components/EventSearch";
import { events } from "@/data/content";
export const metadata: Metadata = { title: "Афиша — тестовые события" };
export default function EventsPage() {
  return <section className="section inner-page">
    <nav className="breadcrumbs" aria-label="Хлебные крошки"><Link href="/">Главная</Link><span aria-hidden="true">/</span><span aria-current="page">Афиша</span></nav>
    <span className="eyebrow">СОБЫТИЯ МУЗЕЯ</span><h1>Афиша</h1>
    <p className="lead">Тестовые данные для проверки работы статической публикации. Это не официальное расписание музея.</p>
    <EventSearch events={events} />
    <div className="events-grid">{events.map((event,index)=><EventCard event={event} index={index} key={event.slug}/>)}</div>
  </section>;
}
