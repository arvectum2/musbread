import MuseumAnchor from "@/components/MuseumAnchor";
import type { Metadata } from "next";
import Link from "@/components/MuseumLink";
import { notFound } from "next/navigation";
import { entriesInSection, isMuseumSection, sections } from "@/data/content";
import { museumReference } from "@/data/museum-reference";
import {fixedPageH1,fixedPageMetadata} from "@/data/fixed-page-seo";

type Props = { params: Promise<{ section: string }> };

export function generateStaticParams() {
  return Object.keys(sections).map((section) => ({ section }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { section } = await params;
  if (!isMuseumSection(section)) return { title: "Раздел не найден" };
  return fixedPageMetadata("/"+section+"/",sections[section].title);
}

export default async function MuseumSectionPage({ params }: Props) {
  const { section } = await params;
  if (!isMuseumSection(section)) notFound();
  const entries = entriesInSection(section);
  const heading = sections[section].title;

  return <section className="section inner-page">
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span><span aria-current="page">{heading}</span>
    </nav>
    <span className="eyebrow">ДЕМОНСТРАЦИОННЫЙ РАЗДЕЛ</span>
    <h1>{fixedPageH1("/"+section+"/",heading)}</h1>
    <p className="lead">Тестовые материалы для проверки редакторской системы. Неофициальная информация музея.</p>
    {section === "news" && <p className="reference-source">
      Новости уже опубликованы на действующем сайте музея.{" "}
      <MuseumAnchor href={museumReference.newsUrl} target="_blank" rel="noopener noreferrer">Читать новости музея ↗</MuseumAnchor>
      <span> · Актуальность отдельных публикаций перед переносом подтвердит заказчик.</span>
    </p>}
    {entries.length ? <div className="museum-list">{entries.map((item) =>
      <Link className="museum-list-item" key={item.slug} href={`/${section}/${item.slug}/`}>
        <h2>{item.title}</h2><p>{item.excerpt}</p><span className="text-link">Читать ↗</span>
      </Link>)}</div> : <p>Материалы этого раздела пока не опубликованы.</p>}
  </section>;
}
