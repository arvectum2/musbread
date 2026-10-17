import MuseumAnchor from "@/components/MuseumAnchor";
import Link from "@/components/MuseumLink";
import EventAgenda from "@/components/EventAgenda";
import VisitorTaskLinks from "@/components/VisitorTaskLinks";
import { content, events } from "@/data/content";
import { museumReference } from "@/data/museum-reference";
import {fixedPageSeo,fixedPageMetadata} from "@/data/fixed-page-seo";
import {visitorContacts} from "@/data/visitor-contacts";
export function generateMetadata(){return fixedPageMetadata("/", "Музей Хлеба — предконтрактный прототип");}
export default function Home() {
  return <>
    <section className="hero">
      <div className="hero-text">
        <div className="eyebrow">САНКТ-ПЕТЕРБУРГ · КУЛЬТУРА И ИСТОРИЯ</div>
        {fixedPageSeo("/")?.h1?.trim() ? <h1>{fixedPageSeo("/")!.h1}</h1> : <h1>Хлеб — больше,<br/>чем <em>еда.</em></h1>}
        <p className="lead">Демонстрационный интерфейс будущего музея. Здесь мы проверяем архитектуру, доступность и публикацию без доступа к CMS.</p>
        <div className="hero-actions"><Link href="/events/" className="primary-button">Смотреть афишу <span aria-hidden="true">↗</span></Link><MuseumAnchor className="secondary-button" href="#museum">Узнать о проекте</MuseumAnchor></div>
      </div>
      <div className="hero-art" aria-hidden="true"><div className="hero-orbit orbit-1"/><div className="hero-orbit orbit-2"/><div className="hero-symbol">✳</div><span className="art-caption">ХЛЕБ · КУЛЬТУРА · ГОРОД</span></div>
    </section>
    <div className="section"><VisitorTaskLinks /></div>
    <section className="section introduction" id="museum">
      <div className="section-heading"><span className="eyebrow">01 / О ПРОЕКТЕ</span><h2>В центре истории —<br/>человек и хлеб.</h2></div>
      <p>{content.site.description} Тексты, фотографии, айдентика, мероприятия и цвета здесь временные: официальные материалы появятся после интервью с заказчиком.</p>
    </section>
    <section className="section events-section">
      <div className="section-title-row"><div><span className="eyebrow">02 / СОБЫТИЯ</span><h2>Афиша музея</h2></div><Link className="text-link" href="/events/">Вся афиша <span aria-hidden="true">↗</span></Link></div>
      {process.env.MUSBREAD_SITE_APPROVED !== "true" && <p className="event-demo-notice">
        Афиша в этом прототипе содержит демонстрационные события, а не официальное расписание музея.
        Актуальные анонсы можно проверить в{" "}
        <MuseumAnchor href={museumReference.newsUrl} target="_blank" rel="noopener noreferrer"
           className="text-link">новостях действующего сайта музея ↗</MuseumAnchor>.
      </p>}
      <EventAgenda events={events} buildDay={new Date().toISOString().slice(0, 10)} variant="featured" />
    </section>
    <section className="section visit-info">
      <div className="section-title-row"><div><span className="eyebrow">ПОСЕЩЕНИЕ МУЗЕЯ</span><h2>Спланировать визит</h2></div></div>
      <p><strong>Адрес:</strong> {visitorContacts.address} · метро «{visitorContacts.metro}».</p>
      <p><strong>Режим:</strong> {visitorContacts.openingHours}; {visitorContacts.admissionHours}; {visitorContacts.closedDay}; {visitorContacts.sanitaryDay}.</p>
      <p>{content.visitor_contacts ? "Сведения из утверждённой карточки CMS музея." : "Предварительные данные с действующего сайта музея; актуальность необходимо подтвердить перед публикацией."}</p>
      <div className="hero-actions"><Link className="primary-button" href="/guide/plan-visit/">Как посетить музей →</Link><Link className="secondary-button" href="/guide/tickets-and-benefits/">Билеты и льготы</Link></div>
    </section>
    <section className="closing-banner"><div><span className="eyebrow">ТЕХНИЧЕСКАЯ ДЕМОНСТРАЦИЯ</span><h2>Сайт, доступный каждому.</h2><p>Адаптивный интерфейс, клавиатурная навигация и страницы, собираемые исключительно из проверенных данных.</p></div><span className="closing-icon" aria-hidden="true">✳</span></section>
  </>;
}
