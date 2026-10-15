import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { content, findEntry, isMuseumSection, sections } from "@/data/content";
import RichText from "@/components/RichText";

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
    {entry.excerpt && <p className="lead">{entry.excerpt}</p>}
    <RichText html={entry.body} />
    <Link className="text-link" href={`/${section}/`}>← К списку материалов</Link>
  </article>;
}
