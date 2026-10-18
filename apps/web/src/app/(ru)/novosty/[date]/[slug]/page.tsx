import type {Metadata} from "next";
import {notFound} from "next/navigation";
import OfficialMuseumNewsDetail from "@/components/OfficialMuseumNewsDetail";
import {officialMuseumNews,officialMuseumArchiveNews, type OfficialMuseumNewsItem} from "@/data/official-museum-news";

/** SEO-safe copy of the ORIGINAL museum news URLs, not browser redirects. */
const publishedMuseumNews=[...officialMuseumNews,...officialMuseumArchiveNews];
const originals=new Map<string,OfficialMuseumNewsItem>(
  publishedMuseumNews.map(article=>[new URL(article.source_url).pathname,article]),
);
type Props={params:Promise<{date:string;slug:string}>};

export function generateStaticParams(){
  return publishedMuseumNews.map(article=>{
    const segments=new URL(article.source_url).pathname.split("/");
    return {date:segments[2],slug:segments[3]};
  });
}
export async function generateMetadata({params}:Props):Promise<Metadata>{
  const {date,slug}=await params;
  const original=originals.get(`/novosty/${date}/${slug}`);
  if(!original)return {title:"Страница не найдена",robots:{index:false}};
  return {
    title:original.title,
    description:original.intro.trim()||undefined,
    alternates:{canonical:original.source_url},
    // In the unapproved prototype inherited layout robots remain noindex.
    // Only source-URL release gates can subsequently make this indexable.
  };
}
export default async function OriginalMuseumNewsPage({params}:Props){
  const {date,slug}=await params;
  const original=originals.get(`/novosty/${date}/${slug}`);
  if(!original)notFound();
  return <OfficialMuseumNewsDetail article={original} originalPath/>;
}
