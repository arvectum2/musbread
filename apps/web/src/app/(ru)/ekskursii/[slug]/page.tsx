import {verifiedSourceRobots} from "@/data/seo-routes";
import type {Metadata} from "next";
import {notFound} from "next/navigation";
import Link from "@/components/MuseumLink";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import excursions from "@/data/official-excursion-programs.json";
import workshops from "@/data/official-workshop-pages.json";

/** Source-first: the old museum published one workshop under /ekskursii. */
const actual=[...excursions.programs,...workshops.programs]
  .filter(item=>new URL(item.source_url).pathname.startsWith("/ekskursii/"));
const originals=new Map(actual.map(item=>[new URL(item.source_url).pathname,item]));
type Props={params:Promise<{slug:string}>};
export function generateStaticParams(){
  return actual.map(item=>({slug:new URL(item.source_url).pathname.split("/")[2]}));
}
export async function generateMetadata({params}:Props):Promise<Metadata>{
  const {slug}=await params;
  const original=originals.get(`/ekskursii/${slug}`);
  if(!original)return {title:"Экскурсия не найдена",robots:{index:false}};
  return {title:original.title,description:original.intro?.trim()||undefined,
    alternates:{canonical:original.source_url},robots:verifiedSourceRobots(process.env.MUSBREAD_SITE_APPROVED,process.env.MUSBREAD_RELEASE_HOST)};
}
export default async function OldMuseumExcursion({params}:Props){
  const {slug}=await params;
  const item=originals.get(`/ekskursii/${slug}`);
  if(!item)notFound();
  return <article className="section inner-page museum-detail" data-original-museum-program={item.slug}>
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span>
      <Link href="/guide/excursions-guide/">Экскурсии</Link><span aria-hidden="true">/</span>
      <span aria-current="page">{item.title}</span>
    </nav>
    <h1>{item.title}</h1>
    <OfficialMuseumSourcePhotos photos={item.image_links} label={item.title} limit={25}/>
    <RichText html={item.html}/>
    <p>Сохранена редакция музея по исходному адресу. Доступность, цены и расписание
      посещения проверяются по актуальным сведениям музея.</p>
    <Link className="text-link" href="/guide/excursions-guide/">← Все программы</Link>
  </article>;
}
