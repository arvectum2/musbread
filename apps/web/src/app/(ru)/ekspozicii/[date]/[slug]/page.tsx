import type {Metadata} from "next";
import {notFound} from "next/navigation";
import Link from "@/components/MuseumLink";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import rooms from "@/data/official-exposition-rooms.json";

const originals=new Map(rooms.rooms.map(item=>[new URL(item.source_url).pathname,item]));
type Props={params:Promise<{date:string;slug:string}>};
export function generateStaticParams(){
  return rooms.rooms.map(item=>{
    const parts=new URL(item.source_url).pathname.split("/");
    return {date:parts[2],slug:parts[3]};
  });
}
export async function generateMetadata({params}:Props):Promise<Metadata>{
  const {date,slug}=await params;
  const item=originals.get(`/ekspozicii/${date}/${slug}`);
  if(!item)return {title:"Зал экспозиции не найден",robots:{index:false}};
  return {title:item.title,description:item.excerpt.trim()||undefined,
    alternates:{canonical:item.source_url}};
}
export default async function OldMuseumRoom({params}:Props){
  const {date,slug}=await params;
  const item=originals.get(`/ekspozicii/${date}/${slug}`);
  if(!item)notFound();
  return <article className="section inner-page museum-detail" data-original-museum-room={item.slug}>
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span>
      <Link href="/guide/museum-exposition/">Экспозиция</Link><span aria-hidden="true">/</span>
      <span aria-current="page">{item.title}</span>
    </nav>
    <h1>{item.title}</h1>
    <OfficialMuseumSourcePhotos photos={item.image_sources.map(source=>({url:source.source_url,alt:source.alt}))}
      label={item.title} limit={50}/>
    <RichText html={item.html}/>
    <p>Это первоначальное описание зала на историческом адресе музея.</p>
    <Link className="text-link" href="/guide/museum-exposition/">← Залы музея</Link>
  </article>;
}
