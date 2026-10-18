import {verifiedSourceRobots} from "@/data/seo-routes";
import type {Metadata} from "next";
import Link from "@/components/MuseumLink";
import RichText from "@/components/RichText";
import {notFound} from "next/navigation";
import sources from "@/data/official-museum-crosslink-pages.json";

/** Standalone original video-section URLs; source HTML is museum-authored. */
const sections=sources.pages.filter(page=>/^\/video\/[a-z0-9-]+$/.test(page.path));
const byPath=new Map(sections.map(item=>[item.path,item]));
type Props={params:Promise<{slug:string}>};
export function generateStaticParams(){return sections.map(s=>({slug:s.path.split('/')[2]}));}
export async function generateMetadata({params}:Props):Promise<Metadata>{
  const {slug}=await params;
  const item=byPath.get(`/video/${slug}`);
  if(!item)return {title:"Видеоматериал не найден",robots:{index:false}};
  return {title:item.title,alternates:{canonical:item.source_url},robots:verifiedSourceRobots(process.env.MUSBREAD_SITE_APPROVED,process.env.MUSBREAD_RELEASE_HOST)};
}
export default async function OriginalMuseumVideoSection({params}:Props){
  const {slug}=await params;
  const item=byPath.get(`/video/${slug}`);
  if(!item)notFound();
  return <article className="section inner-page museum-detail" data-original-museum-section={item.path}>
    <nav aria-label="Хлебные крошки" className="breadcrumbs"><Link href="/">Главная</Link>
      <span aria-hidden="true">/</span><Link href="/video/">Видео</Link>
      <span aria-hidden="true">/</span><span aria-current="page">{item.title}</span></nav>
    <h1>{item.title}</h1>
    <RichText html={item.html}/>
    <p>Подлинный текст музейной страницы. Видеовстраивания требуют отдельной проверки доступности.</p>
  </article>;
}
