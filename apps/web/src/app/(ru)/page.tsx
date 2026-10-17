import Link from "next/link";
import EventAgenda from "@/components/EventAgenda";
import { content, events } from "@/data/content";
import { museumReference } from "@/data/museum-reference";
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
      {process.env.MUSBREAD_SITE_APPROVED !== "true" && <p className="event-demo-notice">
        Афиша в этом прототипе содержит демонстрационные события, а не официальное расписание музея.
        Актуальные анонсы можно проверить в{" "}
        <a href={museumReference.newsUrl} target="_blank" rel="noopener noreferrer"
           className="text-link">новостях действующего сайта музея ↗</a>.
      </p>}
      <EventAgenda events={events} buildDay={new Date().toISOString().slice(0, 10)} variant="featured" />
    </section>
    <section className="section visit-info">
      <div className="section-title-row"><div><span className="eyebrow">ПОСЕЩЕНИЕ МУЗЕЯ</span><h2>Спланировать визит</h2></div></div>
      <p><strong>Адрес:</strong> Санкт-Петербург, ул. Михайлова, д. 2, лит. А · метро «Площадь Ленина».</p>
      <p><strong>Режим:</strong> среда — понедельник 10:00–18:00, вход и касса до 17:00; вторник — выходной. Последний четверг месяца — санитарный день.</p>
      <p>Предварительные данные с действующего сайта музея; актуальность необходимо подтвердить перед публикацией.</p>
      <div className="hero-actions"><Link className="primary-button" href="/guide/plan-visit/">Как посетить музей →</Link><Link className="secondary-button" href="/guide/tickets-and-benefits/">Билеты и льготы</Link></div>
    </section>
    <section className="closing-banner"><div><span className="eyebrow">ТЕХНИЧЕСКАЯ ДЕМОНСТРАЦИЯ</span><h2>Сайт, доступный каждому.</h2><p>Адаптивный интерфейс, клавиатурная навигация и страницы, собираемые исключительно из проверенных данных.</p></div><span className="closing-icon" aria-hidden="true">✳</span></section>
  </>;
}
