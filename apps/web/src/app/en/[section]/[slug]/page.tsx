import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import Image from "next/image";
import { content, findEntry, isMuseumSection } from "@/data/content";
import RichText from "@/components/RichText";

const names: Record<string, string> = {
  museum: "Museum", news: "News", excursions: "Excursions",
  exhibitions: "Exhibitions", documents: "Documents",
};
type Props = { params: Promise<{ section: string; slug: string }> };

export function generateStaticParams() {
  const pages = content.entries.filter((entry) => entry.translations?.en)
    .flatMap((entry) => Object.entries(names)
      .filter(([section]) => (section === "museum" ? "page" : section === "news" ? "news"
        : section === "excursions" ? "excursion" : section === "exhibitions" ? "exhibition" : "document") === entry.type)
      .map(([section]) => ({ section, slug: entry.slug })));
  // Next.js static export requires one route even with zero translations.
  // The sentinel is a 404 page, NEVER linked or indexed as a translation.
  return pages.length ? pages : [{ section: "museum", slug: "not-translated" }];
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { section, slug } = await params;
  if (!isMuseumSection(section)) return { title: "Page not found", robots: { index: false } };
  const entry = findEntry(section, slug);
  const english = entry?.translations?.en;
  if (!english) return { title: "Page not found", robots: { index: false } };
  return {
    title: english.seo_title || english.title,
    description: english.seo_description || english.excerpt || undefined,
    alternates: {
      canonical: "/en/" + section + "/" + slug + "/",
      languages: {
        "ru-RU": "/" + section + "/" + slug + "/",
        "en-US": "/en/" + section + "/" + slug + "/",
      },
    },
  };
}
export default async function EnglishEntryPage({ params }: Props) {
  const { section, slug } = await params;
  if (!isMuseumSection(section)) notFound();
  const entry = findEntry(section, slug);
  const en = entry?.translations?.en;
  if (!entry || !en) notFound();
  return <article lang="en" className="section inner-page museum-detail">
    <nav aria-label="Breadcrumbs" className="breadcrumbs">
      <Link href="/">Home</Link><span aria-hidden="true">/</span>
      <Link href={"/" + section + "/"}>{names[section]}</Link>
      <span aria-hidden="true">/</span><span aria-current="page">{en.title}</span>
    </nav>
    <h1>{en.title}</h1>
    {en.excerpt && <p className="lead">{en.excerpt}</p>}
    <RichText html={en.body}/>
    {entry.media && entry.media.length > 0 && <section className="museum-gallery" aria-label="Image gallery">
      <h2>Gallery</h2><div className="museum-gallery-grid">
        {entry.media.map((media) => <figure key={media.src}>
          <Image src={media.src} width={media.width} height={media.height}
            unoptimized alt={media.alt} loading="lazy"/>
          {media.caption && <figcaption>{media.caption}</figcaption>}
        </figure>)}
      </div>
    </section>}
    {entry.documents && entry.documents.length > 0 && <section className="museum-documents" aria-label="Downloads">
      <h2>Downloads</h2>
      <ul>{entry.documents.map((doc) => <li key={doc.href}>
        <a href={doc.href} download>{doc.label} ({doc.format.toUpperCase()})</a>
      </li>)}</ul>
    </section>}
    <p><Link className="text-link" href={"/" + section + "/" + slug + "/"} lang="ru">Русская версия →</Link></p>
  </article>;
}
