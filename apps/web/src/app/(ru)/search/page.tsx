import type { Metadata } from "next";
import Link from "@/components/MuseumLink";
import GlobalSearch from "@/components/GlobalSearch";
import VisitorTaskLinks from "@/components/VisitorTaskLinks";
import {fixedPageH1,fixedPageMetadata} from "@/data/fixed-page-seo";
export function generateMetadata():Metadata{return fixedPageMetadata("/search/", "Поиск по сайту");}
export default function SearchPage() {
  return <section className="section inner-page">
    <nav className="breadcrumbs" aria-label="Хлебные крошки">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span><span aria-current="page">Поиск</span>
    </nav>
    <h1>{fixedPageH1("/search/","Поиск по сайту")}</h1>
    <p className="lead">Поиск по предварительной структуре музея и опубликованным тестовым материалам. Полный музейный архив будет подключён после согласования.</p>
    <GlobalSearch fullPage />
    <VisitorTaskLinks compact />
  </section>;
}
