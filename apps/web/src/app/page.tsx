import Link from "next/link";
import EventCard from "@/components/EventCard";
import { content, events } from "@/data/content";
export default function Home() {
  return <>
    <section className="hero">
      <div className="hero-text">
        <div className="eyebrow">САНКТ-ПЕТЕРБУРГ · КУЛЬТУРА И ИСТОРИЯ</div>
        <h1>Хлеб — больше,<br/>чем <em>еда.</em></h1>
        <p className="lead">Демонстрационный интерфейс будущего музея. Здесь мы проверяем архитектуру, доступность и публикацию без доступа к CMS.</p>
        <div className="hero-actions"><Link href="/events/" className="primary-button">Смотреть афишу <span aria-hidden="true">↗</span></Link><a className="secondary-button" href="#museum">Узнать о проекте</a></div>
      </div>
      <div className="hero-art" aria-hidden="true"><div className="hero-orbit orbit-1"/><div className="hero-orbit orbit-2"/><div className="hero-symbol">✳</div><span className="art-caption">ХЛЕБ · КУЛЬТУРА · ГОРОД</span></div>
    </section>
    <section className="section introduction" id="museum">
      <div className="section-heading"><span className="eyebrow">01 / О ПРОЕКТЕ</span><h2>В центре истории —<br/>человек и хлеб.</h2></div>
      <p>{content.site.description} Тексты, фотографии, айдентика, мероприятия и цвета здесь временные: официальные материалы появятся после интервью с заказчиком.</p>
    </section>
    <section className="section events-section">
      <div className="section-title-row"><div><span className="eyebrow">02 / СОБЫТИЯ</span><h2>Афиша музея</h2></div><Link className="text-link" href="/events/">Вся афиша <span aria-hidden="true">↗</span></Link></div>
      <div className="events-grid">{events.map((event,index)=><EventCard event={event} index={index} key={event.slug}/>)}</div>
    </section>
    <section className="closing-banner"><div><span className="eyebrow">ТЕХНИЧЕСКАЯ ДЕМОНСТРАЦИЯ</span><h2>Сайт, доступный каждому.</h2><p>Адаптивный интерфейс, клавиатурная навигация и страницы, собираемые исключительно из проверенных данных.</p></div><span className="closing-icon" aria-hidden="true">✳</span></section>
  </>;
}
