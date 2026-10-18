import {verifiedSourceRobots} from "@/data/seo-routes";
import type {Metadata} from "next";
import {notFound} from "next/navigation";
import Link from "@/components/MuseumLink";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import source from "@/data/official-original-legacy-sections.json";

/** Museum's actual four preserved exhibition-catalog URLs. */
const oldIndexes=source.sections.filter(item=>/^\/vistavky\/[a-z0-9-]+$/.test(item.path));
const byPath=new Map(oldIndexes.map(item=>[item.path,item]));
type Props={params:Promise<{slug:string}>};
export function generateStaticParams(){return oldIndexes.map(item=>({slug:item.path.split('/')[2]}));}
export async function generateMetadata({params}:Props):Promise<Metadata>{
  const {slug}=await params;
  const item=byPath.get('/vistavky/'+slug);
  if(!item)return {title:"Каталог музея не найден",robots:{index:false}};
  return {title:item.title,alternates:{canonical:item.source_url},robots:verifiedSourceRobots(process.env.MUSBREAD_SITE_APPROVED,process.env.MUSBREAD_RELEASE_HOST)};
}
export default async function OriginalMuseumExhibitionIndex({params}:Props){
  const {slug}=await params;
  const item=byPath.get('/vistavky/'+slug);
  if(!item)notFound();
  return <article className="section inner-page museum-detail" data-original-museum-section={item.path}>
    <nav aria-label="Хлебные крошки" className="breadcrumbs"><Link href="/">Главная</Link>
      <span aria-hidden="true">/</span><Link href="/guide/exhibitions-guide/">Выставки</Link>
      <span aria-hidden="true">/</span><span aria-current="page">{item.title}</span></nav>
    <h1>{item.title}</h1>
    <OfficialMuseumSourcePhotos photos={item.image_links} label={item.title} limit={25}/>
    <RichText html={item.html}/>
    <p>Сохранены оригинальные материалы каталога музея на исходном адресе.</p>
  </article>;
}
