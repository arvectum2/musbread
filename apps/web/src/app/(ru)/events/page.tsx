import type { Metadata } from "next";
import Link from "next/link";
import EventAgenda from "@/components/EventAgenda";
import EventSearch from "@/components/EventSearch";
import { events } from "@/data/content";
import { museumReference } from "@/data/museum-reference";
import {fixedPageH1,fixedPageMetadata} from "@/data/fixed-page-seo";
export function generateMetadata():Metadata{return fixedPageMetadata("/events/", "Афиша — тестовые события");}
export default function EventsPage() {
  return <section className="section inner-page">
    <nav className="breadcrumbs" aria-label="Хлебные крошки"><Link href="/">Главная</Link><span aria-hidden="true">/</span><span aria-current="page">Афиша</span></nav>
    <span className="eyebrow">СОБЫТИЯ МУЗЕЯ</span><h1>{fixedPageH1("/events/","Афиша")}</h1>
    <p className="lead">Тестовые данные для проверки работы статической публикации. Это не официальное расписание музея.</p>
    <p className="reference-source">Программы мероприятий опубликованы на{" "}
      <a href={museumReference.newsUrl} target="_blank" rel="noopener noreferrer">действующем сайте Музея хлеба ↗</a>.
    </p>
    <EventSearch events={events} />
    <EventAgenda events={events} buildDay={new Date().toISOString().slice(0, 10)} />
  </section>;
}
