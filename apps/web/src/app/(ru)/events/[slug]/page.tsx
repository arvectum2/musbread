import Link from "@/components/MuseumLink";
import { notFound } from "next/navigation";
import { events, findEvent } from "@/data/content";
import type { Metadata } from "next";
export function generateStaticParams() { return events.map(event=>({slug:event.slug})); }
export async function generateMetadata({params}:{params:Promise<{slug:string}>}):Promise<Metadata> {
  const {slug}=await params; const event=findEvent(slug);
  return {
    title: event?.seo_title?.trim() || event?.title || "Событие не найдено",
    description: event?.seo_description?.trim() || event?.excerpt || undefined,
  };
}
export default async function EventPage({params}:{params:Promise<{slug:string}>}) {
  const {slug}=await params; const event=findEvent(slug); if(!event) notFound();
  return <article className="section inner-page event-detail">
    <nav className="breadcrumbs" aria-label="Хлебные крошки"><Link href="/">Главная</Link><span aria-hidden="true">/</span><Link href="/events/">Афиша</Link><span aria-hidden="true">/</span><span aria-current="page">{event.title}</span></nav>
    <span className="eyebrow">{event.category} · {event.date}{event.ends_on && event.ends_on !== event.date ? ` — ${event.ends_on}` : ""}</span><h1>{event.h1?.trim() || event.title}</h1>
    <p className="lead">{event.excerpt}</p><div className="article-content"><p>{event.body}</p></div>
    {event.related_entries && event.related_entries.length > 0 && <section className="museum-related" aria-label="Связанные материалы события">
      <h2>Связанные материалы</h2>
      <ul>{event.related_entries.map((related) => <li key={related.href}>
        <Link href={related.href} className="text-link">{related.title}</Link>
      </li>)}</ul>
    </section>}
    <Link href="/events/" className="text-link">← Вернуться к афише</Link>
  </article>;
}
