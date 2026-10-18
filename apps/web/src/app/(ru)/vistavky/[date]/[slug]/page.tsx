import {verifiedSourceRobots} from "@/data/seo-routes";
import type {Metadata} from "next";
import Link from "@/components/MuseumLink";
import {notFound} from "next/navigation";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import {officialExhibitionDetails,type MuseumExhibitionSource} from "@/data/official-exhibitions";
import deeperOriginals from "@/data/official-deep-museum-pages.json";

/** Historical museum exhibitions retained at the original public /vistavky/YYYY… URL. */
// An extra museum exhibition discovered in old /novosti links: preserve its
// original source URL and true H1; do not invent an intro or visit schedule.
const deeperExhibitions=deeperOriginals.pages
  .filter(item=>/^\/vistavky\/\d{4}-\d{2}-\d{2}\/[a-z0-9-]+$/.test(item.path))
  .map(item=>({...item,slug:item.path.split("/")[3],category_slug:"exhibitions-past",
    intro:"",photos_rights_confirmed:false as const,captured_utc:item.source_page_captured_at}));
const realShows=[...officialExhibitionDetails,...deeperExhibitions] as MuseumExhibitionSource[];
const byOriginal=new Map<string,MuseumExhibitionSource>(realShows.map(x=>[new URL(x.source_url).pathname,x]));
type Props={params:Promise<{date:string;slug:string}>};
export function generateStaticParams(){
  return realShows.map(x=>{
    const parts=new URL(x.source_url).pathname.split("/");
    return {date:parts[2],slug:parts[3]};
  });
}
export async function generateMetadata({params}:Props):Promise<Metadata>{
  const {date,slug}=await params;
  const item=byOriginal.get(`/vistavky/${date}/${slug}`);
  if(!item)return {title:"Выставка не найдена",robots:{index:false}};
  return {
    title:item.title,
    description:item.intro.trim()||undefined,
    alternates:{canonical:item.source_url},
    robots:verifiedSourceRobots(process.env.MUSBREAD_SITE_APPROVED,process.env.MUSBREAD_RELEASE_HOST),
  };
}
export default async function OriginalMuseumExhibitionPage({params}:Props){
  const {date,slug}=await params;
  const item=byOriginal.get(`/vistavky/${date}/${slug}`);
  if(!item)notFound();
  return <article className="section inner-page museum-detail" data-original-museum-exhibition={item.slug}>
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span>
      <Link href={`/guide/${item.category_slug}/`}>Выставки</Link><span aria-hidden="true">/</span>
      <span aria-current="page">{item.title}</span>
    </nav>
    <span className="eyebrow">ОПУБЛИКОВАННЫЙ МУЗЕЕМ МАТЕРИАЛ · ИСХОДНЫЙ АДРЕС</span>
    <h1>{item.title}</h1>
    {item.category_slug==="exhibitions-past" && <p>Это архивное описание выставки.
      Даты и сведения взяты из музейного первоисточника и не означают, что выставка проходит сегодня.</p>}
    {item.category_slug==="exhibitions-traveling" && <p>Это описание музейного выездного проекта,
      не расписание показов. Доступность уточняйте у музея.</p>}
    <OfficialMuseumSourcePhotos photos={item.image_links} label={item.title} limit={12}/>
    {item.image_only
      ? <p>Источник содержит только изображение. Оно сохранено без добавленного текста.</p>
      : <RichText html={item.html}/>}
    <p>Исходный адрес выставки сохранён без перенаправления, чтобы не терять исторические ссылки.</p>
    <Link href={`/guide/${item.category_slug}/`} className="text-link">← Все выставки этого раздела</Link>
  </article>;
}
