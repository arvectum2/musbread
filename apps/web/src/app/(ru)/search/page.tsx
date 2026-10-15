import type { Metadata } from "next";
import Link from "next/link";
import GlobalSearch from "@/components/GlobalSearch";
export const metadata: Metadata = { title: "Поиск по сайту" };
export default function SearchPage() {
  return <section className="section inner-page">
    <nav className="breadcrumbs" aria-label="Хлебные крошки">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span><span aria-current="page">Поиск</span>
    </nav>
    <h1>Поиск по сайту</h1>
    <p className="lead">Поиск по предварительной структуре музея и опубликованным тестовым материалам. Полный музейный архив будет подключён после согласования.</p>
    <GlobalSearch />
  </section>;
}
