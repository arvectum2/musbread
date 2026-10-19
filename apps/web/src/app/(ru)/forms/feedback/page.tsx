import Link from '@/components/MuseumLink';
import MuseumVisitorInquiryForm from '@/components/MuseumVisitorInquiryForm';
import type {Metadata} from 'next';
export const metadata:Metadata={title:'Обратная связь — Музей Хлеба',robots:{index:false,follow:false}};
export default function Page(){return <article className="section inner-page guide-page">
 <nav aria-label="Хлебные крошки" className="breadcrumbs"><Link href="/">Главная</Link><span aria-hidden="true">/</span><span aria-current="page">Обратная связь</span></nav>
 <h1>Обратная связь</h1>
 <MuseumVisitorInquiryForm kind="feedback"/>
 </article>;}
