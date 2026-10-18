import type {Metadata} from "next";
import {notFound} from "next/navigation";
import Link from "@/components/MuseumLink";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import workshops from "@/data/official-workshop-pages.json";

const originals=new Map(workshops.programs
  .filter(item=>new URL(item.source_url).pathname.startsWith("/master-klassy/"))
  .map(item=>[new URL(item.source_url).pathname,item]));
type Props={params:Promise<{slug:string}>};
export function generateStaticParams(){
  return [...originals.keys()].map(path=>({slug:path.split("/")[2]}));
}
export async function generateMetadata({params}:Props):Promise<Metadata>{
  const {slug}=await params;
  const item=originals.get(`/master-klassy/${slug}`);
  if(!item)return {title:"Мастер-класс не найден",robots:{index:false}};
  return {title:item.title,description:item.intro.trim()||undefined,
    alternates:{canonical:item.source_url}};
}
export default async function OldMuseumWorkshop({params}:Props){
  const {slug}=await params;
  const item=originals.get(`/master-klassy/${slug}`);
  if(!item)notFound();
  return <article className="section inner-page museum-detail" data-original-museum-program={item.slug}>
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span>
      <Link href="/guide/children-workshops/">Мастер-классы</Link><span aria-hidden="true">/</span>
      <span aria-current="page">{item.title}</span>
    </nav>
    <h1>{item.title}</h1>
    <OfficialMuseumSourcePhotos photos={item.image_links} label={item.title} limit={25}/>
    <RichText html={item.html}/>
    <p>Сохранена исходная публикация музея. Расписание и возможность записи
      уточняются по действующим сведениям музея.</p>
    <Link className="text-link" href="/guide/children-workshops/">← Все мастер-классы</Link>
  </article>;
}
