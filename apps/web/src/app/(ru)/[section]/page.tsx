import MuseumAnchor from "@/components/MuseumAnchor";
import type { Metadata } from "next";
import Link from "@/components/MuseumLink";
import { notFound } from "next/navigation";
import { entriesInSection, isMuseumSection, sections } from "@/data/content";
import { museumReference } from "@/data/museum-reference";
import OfficialMuseumNews from "@/components/OfficialMuseumNews";
import {officialMuseumNewsSlugs} from "@/data/official-museum-news";
import {fixedPageH1,fixedPageMetadata} from "@/data/fixed-page-seo";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import originalSections from "@/data/official-original-legacy-sections.json";
import extraOriginalPages from "@/data/official-museum-crosslink-pages.json";


const verifiedOldRoots=[...originalSections.sections,...extraOriginalPages.pages]
  .filter(item=>/^\/[a-z0-9-]+$/.test(item.path));
const oldRootByPath=new Map(verifiedOldRoots.map(item=>[item.path,item]));

type Props = { params: Promise<{ section: string }> };

export function generateStaticParams() {
  return [...Object.keys(sections).map((section) => ({ section })),
    ...verifiedOldRoots.map(item=>({section:item.path.slice(1)}))];
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { section } = await params;
  const original=oldRootByPath.get('/'+section);
  if(original)return {title:original.title,alternates:{canonical:original.source_url}};
  if (!isMuseumSection(section)) return { title: "Раздел не найден" };
  return fixedPageMetadata("/"+section+"/",sections[section].title);
}

export default async function MuseumSectionPage({ params }: Props) {
  const { section } = await params;
  const original=oldRootByPath.get('/'+section);
  if(original)return <article className="section inner-page museum-detail" data-original-museum-section={original.path}>
    <nav className="breadcrumbs" aria-label="Хлебные крошки"><Link href="/">Главная</Link>
      <span aria-hidden="true">/</span><span aria-current="page">{original.title}</span></nav>
    <h1>{original.title}</h1>
    <OfficialMuseumSourcePhotos photos={original.image_links} label={original.title} limit={40}/>
    <RichText html={original.html}/>
    {original.path==='/gostevaya-kniga' && <p>Сохранён доступный на исходной странице отзыв. Отправка новых отзывов
      в доконтрактном прототипе не подключена и требует согласованной реализации.</p>}
    <p>Материал воспроизведён по исходному адресу музея; сведения могут уточняться редакцией музея.</p>
    <Link href="/" className="text-link">← На главную музея</Link>
  </article>;
  if (!isMuseumSection(section)) notFound();
  const entries = entriesInSection(section)
    .filter(e=>section!=="news" || !officialMuseumNewsSlugs.has(e.slug));
  const heading = sections[section].title;

  return <section className="section inner-page">
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span><span aria-current="page">{heading}</span>
    </nav>
    <span className="eyebrow">{section==="news"
      ? "НОВОСТИ ИЗ ОФИЦИАЛЬНОГО МУЗЕЙНОГО ИСТОЧНИКА"
      : "ДЕМОНСТРАЦИОННЫЙ РАЗДЕЛ"}</span>
    <h1>{fixedPageH1("/"+section+"/",heading)}</h1>
    <p className="lead">{section==="news"
      ? "Публикации текущей редакции действующего сайта музея и материалы, которые впоследствии сможет обновлять редактор."
      : "Тестовые материалы для проверки редакторской системы. Неофициальная информация музея."}</p>
    {section === "news" && <p className="reference-source">
      Новости уже опубликованы на действующем сайте музея.{" "}
      <MuseumAnchor href={museumReference.newsUrl} target="_blank" rel="noopener noreferrer">Читать новости музея ↗</MuseumAnchor>
      <span> · Актуальность отдельных публикаций перед переносом подтвердит заказчик.</span>
    </p>}
    {section==="news" && <OfficialMuseumNews />}
    {entries.length ? <>
      <h2>{section==="news" ? "Другие публикации из CMS" : "Материалы"}</h2>
      <div className="museum-list">{entries.map((item) =>
      <Link className="museum-list-item" key={item.slug} href={`/${section}/${item.slug}/`}>
        <h2>{item.title}</h2><p>{item.excerpt}</p><span className="text-link">Читать ↗</span>
      </Link>)}</div></> : section!=="news" ? <p>Материалы этого раздела пока не опубликованы.</p> : null}
  </section>;
}
