import Link from "next/link";
import { notFound } from "next/navigation";
import { events, findEvent } from "@/data/content";
import type { Metadata } from "next";
export function generateStaticParams() { return events.map(event=>({slug:event.slug})); }
export async function generateMetadata({params}:{params:Promise<{slug:string}>}):Promise<Metadata> {
  const {slug}=await params; const event=findEvent(slug);
  return {title:event?.title ?? "Событие не найдено", description:event?.excerpt};
}
export default async function EventPage({params}:{params:Promise<{slug:string}>}) {
  const {slug}=await params; const event=findEvent(slug); if(!event) notFound();
  return <article className="section inner-page event-detail">
    <nav className="breadcrumbs" aria-label="Хлебные крошки"><Link href="/">Главная</Link><span aria-hidden="true">/</span><Link href="/events/">Афиша</Link><span aria-hidden="true">/</span><span aria-current="page">{event.title}</span></nav>
    <span className="eyebrow">{event.category} · {event.date}</span><h1>{event.title}</h1>
    <p className="lead">{event.excerpt}</p><div className="article-content"><p>{event.body}</p></div>
    <Link href="/events/" className="text-link">← Вернуться к афише</Link>
  </article>;
}
