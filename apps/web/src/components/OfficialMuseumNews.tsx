import Link from "@/components/MuseumLink";
import MuseumAnchor from "@/components/MuseumAnchor";
import RichText from "@/components/RichText";
import {content, entryPublicHref} from "@/data/content";
import {officialMuseumNews, officialMuseumArchiveNews, museumNewsSourceIndex, museumNewsSourceSnapshot} from "@/data/official-museum-news";

/** Official recent news articles, not imaginary current-event dates or availability. */
export default function OfficialMuseumNews(){
  const published=new Map(content.entries.filter(e=>e.type==="news")
    .map(e=>[e.slug,e]));
  return <>
  <section className="official-museum-programs museum-news-source"
    aria-label="Последние новости действующего сайта музея">
    <h2>Последние новости Санкт-Петербургского музея Хлеба</h2>
    <p>Перенесены <strong>{officialMuseumNews.length} действительных новостей</strong>
      {" "}с <MuseumAnchor href={museumNewsSourceIndex} target="_blank" rel="noopener noreferrer">
      официального сайта музея ↗</MuseumAnchor> (снимок {museumNewsSourceSnapshot.slice(0,10)}).
      Дата публикации новости не означает дату проведения события.
      Сведения о доступности программы и билетах уточняйте на исходной странице.</p>
    <div className="official-museum-program-grid">
      {officialMuseumNews.map(item=>{
        const editor=published.get(item.slug);
        return <article className="official-museum-program-card" key={item.slug}>
          <p className="official-museum-program-number">Новость от {item.published_on.split("-").reverse().join(".")}</p>
          <h3>{editor?.title?.trim() || item.title}</h3>
          <p>{editor?.excerpt?.trim() || item.intro}</p>
          <details>
            <summary>Прочитать сообщение музея</summary>
            <div className="official-museum-program-body"><RichText html={editor?.body?.trim() || item.html}/></div>
          </details>
          <div className="official-museum-program-links">
            {editor && <Link href={entryPublicHref(editor)} className="text-link">
              Редакция на новом сайте →</Link>}
            <MuseumAnchor className="text-link" href={item.source_url}
              target="_blank" rel="noopener noreferrer">Оригинальная новость ↗</MuseumAnchor>
          </div>
        </article>;
      })}
    </div>
    <p className="official-museum-program-warning">
      Это последние десять публикаций с первой страницы официального списка.
      Исторический архив приведён отдельно ниже. Фотографии не выводятся до подтверждения прав.
    </p>
  </section>
  <section className="official-museum-programs museum-news-archive"
    aria-label="Исторический архив новостей музея">
    <h2>Архив новостей музея</h2>
    <p>Дополнительно перенесены {officialMuseumArchiveNews.length} подлинных архивных новостей
      с официальных страниц музея. Это прошлые публикации, а не действующее расписание.
      Права на изображения требуют отдельного подтверждения.</p>
    <details>
      <summary>Показать {officialMuseumArchiveNews.length} архивных публикаций</summary>
      <div className="official-museum-program-grid">
        {officialMuseumArchiveNews.map(item=>{
          const editor=published.get(item.slug);
          return <article className="official-museum-program-card" key={item.slug}>
            <p className="official-museum-program-number">Архивная публикация от {item.published_on.split("-").reverse().join(".")}</p>
            <h3>{editor?.title?.trim() || item.title}</h3>
            <p>{editor?.excerpt?.trim() || item.intro}</p>
            <details>
              <summary>Прочитать архивное сообщение</summary>
              <div className="official-museum-program-body"><RichText html={editor?.body?.trim() || item.html}/></div>
            </details>
            <div className="official-museum-program-links">
              {editor && <Link href={entryPublicHref(editor)} className="text-link">Редакция на новом сайте →</Link>}
              <MuseumAnchor className="text-link" href={item.source_url} target="_blank"
                rel="noopener noreferrer">Оригинальная архивная новость ↗</MuseumAnchor>
            </div>
          </article>;
        })}
      </div>
    </details>
    <p className="official-museum-program-warning">Архив на этой странице не претендует на полноту
      всех лет существования музея. Новые источники добавляются по мере достоверной сверки.</p>
  </section>
  </>;
}
