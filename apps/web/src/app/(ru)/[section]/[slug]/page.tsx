import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { content, findEntry, isMuseumSection, sections } from "@/data/content";
import RichText from "@/components/RichText";
import Image from "next/image";

type Props = { params: Promise<{ section: string; slug: string }> };

export function generateStaticParams() {
  return content.entries.flatMap((entry) =>
    Object.entries(sections)
      .filter(([, section]) => section.type === entry.type)
      .map(([section]) => ({ section, slug: entry.slug })),
  );
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { section, slug } = await params;
  if (!isMuseumSection(section)) return { title: "Материал не найден" };
  const entry = findEntry(section, slug);
  return {
    title: entry?.seo_title || entry?.title || "Материал не найден",
    description: entry?.seo_description || entry?.excerpt || undefined,
    ...(entry?.translations?.en ? { alternates: {
      canonical: "/" + section + "/" + slug + "/",
      languages: { "ru-RU": "/" + section + "/" + slug + "/",
        "en-US": "/en/" + section + "/" + slug + "/" },
    } } : {}),
  };
}

export default async function MuseumEntryPage({ params }: Props) {
  const { section, slug } = await params;
  if (!isMuseumSection(section)) notFound();
  const entry = findEntry(section, slug);
  if (!entry) notFound();
  return <article className="section inner-page museum-detail">
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span>
      <Link href={`/${section}/`}>{sections[section].title}</Link>
      <span aria-hidden="true">/</span><span aria-current="page">{entry.title}</span>
    </nav>
    <span className="eyebrow">{sections[section].title} · ТЕСТОВЫЙ МАТЕРИАЛ</span>
    <h1>{entry.h1 || entry.title}</h1>
    {entry.translations?.en && <p><Link href={"/en/" + section + "/" + slug + "/"} lang="en"
      className="text-link">Read in English →</Link></p>}
    {entry.excerpt && <p className="lead">{entry.excerpt}</p>}
    <RichText html={entry.body} />
    {entry.media && entry.media.length > 0 && <section className="museum-gallery" aria-label="Галерея изображений">
      <h2>Галерея</h2>
      <div className="museum-gallery-grid">
        {entry.media.map((media, index) => <figure key={media.src + "-" + index}>
          <Image src={media.src} width={media.width} height={media.height}
            unoptimized alt={media.alt} loading="lazy" />
          {media.caption && <figcaption>{media.caption}</figcaption>}
        </figure>)}
      </div>
    </section>}
    {entry.documents && entry.documents.length > 0 && <section aria-label="Документы для скачивания" className="museum-documents">
      <h2>Документы</h2>
      <ul>
        {entry.documents.map((document) => <li key={document.href}>
          <a href={document.href} download className="text-link">
            {document.label} ({document.format.toUpperCase()}, {Math.ceil(document.size_bytes / 1024)} КБ)
          </a>
          {document.accessibility_reviewed && document.accessibility_note
            ? <p className="museum-document-accessibility">{document.accessibility_note}</p>
            : <p className="museum-document-accessibility">Доступность документа ещё проверяется редактором;
              основную информацию можно прочесть в тексте этой страницы.</p>}
        </li>)}
      </ul>
      <p>Файлы скачиваются на устройство. Для доступного просмотра используйте описание на этой странице.</p>
    </section>}
    {entry.related_entries && entry.related_entries.length > 0 && <section className="museum-related" aria-label="Связанные материалы">
      <h2>Связанные материалы</h2>
      <ul>{entry.related_entries.map((related) => <li key={related.href}>
        <Link href={related.href} className="text-link">{related.title}</Link>
      </li>)}</ul>
    </section>}
    {entry.related_events && entry.related_events.length > 0 && <section className="museum-related" aria-label="Связанные события">
      <h2>Связанные события</h2>
      <ul>{entry.related_events.map((event) => <li key={event.href}>
        <Link href={event.href} className="text-link">{event.title}</Link>
      </li>)}</ul>
    </section>}
    <Link className="text-link" href={`/${section}/`}>← К списку материалов</Link>
  </article>;
}
