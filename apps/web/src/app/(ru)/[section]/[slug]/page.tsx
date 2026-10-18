import RichText from "@/components/RichText";
import MuseumAnchor from "@/components/MuseumAnchor";
import type { Metadata } from "next";
import Link from "@/components/MuseumLink";
import { notFound } from "next/navigation";
import { content, findEntry, isMuseumSection, sections } from "@/data/content";
import MuseumRichBody from "@/components/MuseumRichBody";
import Image from "next/image";
import OfficialMuseumNewsDetail from "@/components/OfficialMuseumNewsDetail";
import {officialMuseumNews,officialMuseumArchiveNews} from "@/data/official-museum-news";

type Props = { params: Promise<{ section: string; slug: string }> };

const originalNews = new Map([...officialMuseumNews,...officialMuseumArchiveNews]
  .map(article=>[article.slug,article]));

export function generateStaticParams() {
  const cms=content.entries.flatMap((entry) =>
    Object.entries(sections)
      .filter(([, section]) => section.type === entry.type)
      .map(([section]) => ({section,slug:entry.slug})),
  );
  const owned=new Set(cms.map(item=>item.section+"/"+item.slug));
  const verified=[...originalNews.keys()].filter(slug=>!owned.has("news/"+slug))
    .map(slug=>({section:"news",slug}));
  return [...cms,...verified];
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { section, slug } = await params;
  if (!isMuseumSection(section)) return { title: "Материал не найден" };
  const entry = findEntry(section, slug);
  const original=section==="news"?originalNews.get(slug):undefined;
  return {
    title: entry?.seo_title || entry?.title || original?.title || "Материал не найден",
    description: entry?.seo_description || entry?.excerpt || original?.intro || undefined,
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
  const original=section==="news"?originalNews.get(slug):undefined;
  if(!entry && original)return <OfficialMuseumNewsDetail article={original}/>;
  if (!entry) notFound();
  return <article className="section inner-page museum-detail">
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span>
      <Link href={`/${section}/`}>{sections[section].title}</Link>
      <span aria-hidden="true">/</span><span aria-current="page">{entry.title}</span>
    </nav>
    {entry.section_slug && content.sections?.some((s) => s.slug === entry.section_slug) &&
      <p className="cms-entry-section">Раздел каталога: <Link className="text-link" href={`/guide/${entry.section_slug}/`}>
        {content.sections.find((s) => s.slug === entry.section_slug)?.title}
      </Link></p>}
    <span className="eyebrow">{sections[section].title} · ТЕСТОВЫЙ МАТЕРИАЛ</span>
    <h1>{entry.h1 || entry.title}</h1>
    {entry.translations?.en && <p><Link href={"/en/" + section + "/" + slug + "/"} lang="en"
      className="text-link">Read in English →</Link></p>}
    {entry.excerpt && <p className="lead">{entry.excerpt}</p>}
    <MuseumRichBody html={entry.body} videos={entry.videos} />
    {entry.media && entry.media.length > 0 && <section className="museum-gallery" aria-label="Галерея изображений">
      <h2>Галерея</h2>
      <div className="museum-gallery-grid">
        {entry.media.map((media, index) => <figure key={media.src + "-" + index}>
          <Image src={media.src} width={media.width} height={media.height}
            unoptimized alt={media.alt} loading="lazy" />
          {media.caption && <figcaption>{media.caption}</figcaption>}
          {media.long_description && <p className="museum-media-long-description" >
            <strong>Подробное описание:</strong> {media.long_description}
          </p>}
        </figure>)}
      </div>
    </section>}
    {entry.documents && entry.documents.length > 0 && <section aria-label="Документы для скачивания" className="museum-documents">
      <h2>Документы</h2>
      <ul>
        {entry.documents.map((document) => <li key={document.href}>
          <MuseumAnchor href={document.href} download className="text-link">
            {document.label} ({document.format.toUpperCase()}, {Math.ceil(document.size_bytes / 1024)} КБ)
          </MuseumAnchor>
          {document.accessible_html
            ? <details id={"html-edition-"+document.href.split("/").pop()?.split(".")[0]}
                className="museum-document-html-edition">
                <summary>Читать проверенную HTML-версию этого документа</summary>
                <p>HTML-редакция подготовлена и сверена с исходным документом редактором музея.
                Оригинальный файл доступен по ссылке выше.</p>
                <RichText html={document.accessible_html}/>
              </details>
            : null}
          {document.accessibility_reviewed && document.accessibility_note
            ? <p className="museum-document-accessibility">{document.accessibility_note}</p>
            : <p className="museum-document-accessibility">Полнотекстовая HTML-версия пока не утверждена; доступность исходного файла
              для экранного диктора может быть ограничена.</p>}
        </li>)}
      </ul>
      <p>Файлы скачиваются на устройство. Полная HTML-версия появляется отдельно
        только после подтверждения эквивалентности редактором музея.</p>
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
