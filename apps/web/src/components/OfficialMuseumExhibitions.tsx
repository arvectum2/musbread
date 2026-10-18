import Link from "@/components/MuseumLink";
import MuseumAnchor from "@/components/MuseumAnchor";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import {content,entryPublicHref} from "@/data/content";
import {exhibitionSourceIndex,officialExhibitionDetails,officialExhibitionNewsLinked,officialExhibitionNodeLinked} from "@/data/official-exhibitions";

/** The old museum site is a dated source, not proof of future availability. */
export default function OfficialMuseumExhibitions({category}:{category:string}){
  const index=exhibitionSourceIndex(category);
  if(!index)return null;
  const source=new Map(officialExhibitionDetails
    .filter(x=>x.category_slug===category).map(x=>[x.source_url,x]));
  const published=new Map(content.entries
    .filter(x=>x.type==="exhibition" && x.section_slug===category)
    .map(x=>[x.slug,x]));
  const isCurrent=category==="exhibitions-current";
  const isTraveling=category==="exhibitions-traveling";
  return <section className="official-museum-programs official-exhibitions"
    aria-label={"Выставки из официального раздела: "+index.title}>
    <h2>{index.title} — опубликованные сведения</h2>
    <p>В действующем <MuseumAnchor href={index.source_url} target="_blank"
      rel="noopener noreferrer">музейном каталоге ↗</MuseumAnchor>
      {" "}зафиксировано <strong>{index.linked_exhibitions.length}</strong> выставок
      (снимок {index.captured_utc.slice(0,10)}). Даты и статусы отражают
      опубликованную на эту дату редакцию; для планирования визита уточните актуальность у музея.</p>
    {isTraveling && <p className="official-museum-program-warning">
      Выездные выставки — музейные проекты, а не подтверждённое расписание
      показов по конкретным адресам. Доступность и место показа необходимо уточнять.
    </p>}
    {isCurrent && <p className="official-museum-program-warning">
      Ниже — выставки, обозначенные музеем как текущие на дату снимка. Для каждого
      проекта указаны исходные музейные сроки; это не сведения о свободных местах.
    </p>}
    <div className="official-museum-program-grid">
      {index.linked_exhibitions.map((item,i)=>{
        const original=source.get(item.source_url);
        const editor=original && published.get(original.slug);
        return <article className="official-museum-program-card" key={item.source_url} id={original?.slug}>
          <p className="official-museum-program-number">
            {isCurrent?"Текущая на дату снимка":isTraveling?"Выездной проект":category==="exhibitions-past"?"Архивная выставка":"Виртуальная выставка"} {String(i+1).padStart(2,"0")}
          </p>
          <h3>{editor?.title?.trim() || original?.title || item.title}</h3>
          <OfficialMuseumSourcePhotos photos={index.image_links?.[i] ? [index.image_links[i]] : original?.image_links} label={item.title} limit={1}/>
          {item.date_text && <p><strong>Сроки по музею:</strong> {item.date_text}</p>}
          {original && <>
            {original.image_only && !editor
              ? <p>Исходная страница содержит изображение без текстового описания. Оригинал доступен на сайте музея.</p>
              : <p>{editor?.excerpt?.trim() || original.intro}</p>}
            {(editor?.body?.trim() || original.html) && <details>
              <summary>Полное описание выставки</summary>
              <div className="official-museum-program-body"><RichText html={editor?.body?.trim()||original.html}/></div>
            </details>}
          </>}
          <div className="official-museum-program-links">
            {editor && <Link href={entryPublicHref(editor)} className="text-link">
              Редакция музея на новом сайте →
            </Link>}
            <MuseumAnchor href={item.source_url} target="_blank" rel="noopener noreferrer"
              className="text-link">Оригинальная выставка ↗</MuseumAnchor>
          </div>
        </article>;
      })}
    </div>
    {category==="exhibitions-past" && officialExhibitionNewsLinked.length>0 && <section
      aria-label="Дополнительные музейные выставки, найденные в архиве новостей">
      <h3>Дополнительные архивные выставки из новостей музея</h3>
      <p>Подлинные музейные страницы ({officialExhibitionNewsLinked.length}) найдены по прямым ссылкам из старых музейных новостей;
        в обследованной подборке из 12 прошедших выставок их не было.
        Даты публикаций относятся к исходным материалам, не к предстоящим показам.</p>
      <div className="official-museum-program-grid">
        {officialExhibitionNewsLinked.map(original=>{
          const editor=published.get(original.slug);
          return <article className="official-museum-program-card" key={original.slug} id={original.slug}>
            <p className="official-museum-program-number">Архивная выставка из музейных новостей</p>
            <h3>{editor?.title?.trim() || original.title}</h3>
            <p>{editor?.excerpt?.trim() || original.intro}</p>
            <details>
              <summary>Полное описание выставки</summary>
              <div className="official-museum-program-body"><RichText html={editor?.body?.trim()||original.html}/></div>
            </details>
            <div className="official-museum-program-links">
              {editor && <Link href={entryPublicHref(editor)} className="text-link">Редакция музея →</Link>}
              <MuseumAnchor href={original.source_url} target="_blank" rel="noopener noreferrer"
                className="text-link">Исходная страница музея ↗</MuseumAnchor>
            </div>
          </article>;
        })}
      </div>
    </section>}
    {category==="exhibitions-past" && officialExhibitionNodeLinked.length>0 && <section
      aria-label="Подлинные выставки, восстановленные по ссылкам Drupal из старых новостей">
      <h3>Подробные описания выставок, найденные в старых новостях</h3>
      <p>Эти {officialExhibitionNodeLinked.length} подлинных музейных страниц
        обнаружены по старым ссылкам формата <code>/node/…</code> внутри
        публикаций 2019–2026 годов. Даты и сведения взяты из исходных публикаций;
        они не означают проведение выставки сегодня.</p>
      <div className="official-museum-program-grid">
        {officialExhibitionNodeLinked.map(original=>{
          const editor=published.get(original.slug);
          return <article className="official-museum-program-card" key={original.slug} id={original.slug}>
            <p className="official-museum-program-number">Подлинная архивная выставка</p>
            <h3>{editor?.title?.trim() || original.title}</h3>
            <OfficialMuseumSourcePhotos photos={original.image_links}
              label={original.title} limit={4}/>
            <p>{editor?.excerpt?.trim() || original.intro}</p>
            <details><summary>Полное музейное описание</summary>
              <div className="official-museum-program-body">
                <RichText html={editor?.body?.trim()||original.html}/>
              </div>
            </details>
            <div className="official-museum-program-links">
              {editor && <Link href={entryPublicHref(editor)} className="text-link">Редакция музея →</Link>}
              <MuseumAnchor href={original.source_url} target="_blank" rel="noopener noreferrer"
                className="text-link">Исходная публикация музея ↗</MuseumAnchor>
            </div>
          </article>;
        })}
      </div>
    </section>}
    <p className="official-museum-program-warning">
      Оригинальные фотографии и плакаты взяты с действующего сайта музея для рабочего прототипа.
      <span> </span><Link href="/guide/plan-visit/">Контакты и посещение музея →</Link>
    </p>
  </section>;
}
