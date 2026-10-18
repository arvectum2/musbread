import Link from "@/components/MuseumLink";
import MuseumAnchor from "@/components/MuseumAnchor";
import RichText from "@/components/RichText";
import {content,entryPublicHref} from "@/data/content";
import {officialWorkshopIndex,officialWorkshops} from "@/data/official-workshops";

/** Real current museum workshops, without inventing an adult-only program. */
export default function OfficialMuseumWorkshops({audience}:{audience:"children"|"adults"}){
  const published = new Map(content.entries
    .filter(p=>p.type==="page" && p.section_slug==="children-workshops"
      && p.slug.startsWith("museum-workshop-")).map(p=>[p.slug,p]));
  return <section className="official-museum-programs" aria-label="Мастер-классы по действующему каталогу музея">
    <h2>{audience==="children"?"Мастер-классы для детей и семей":"Мастер-классы: программы музея"}</h2>
    <p>На действующем сайте музея размещены <strong>{officialWorkshops.length} мастер-классов</strong>.
      Все названия и описания взяты из <MuseumAnchor href={officialWorkshopIndex.source_url}
        target="_blank" rel="noopener noreferrer">официального каталога ↗</MuseumAnchor>.
      В карточках сохранены исходные ограничения минимального возраста.</p>
    {audience==="adults"
      ? <p className="official-museum-program-warning">Отдельного утверждённого музеем каталога
          мастер-классов именно для взрослых не опубликовано. Ниже представлены реальные
          музейные программы; возможность участия взрослых нужно уточнить при записи.
          Возраст «6+» или «10+» не означает подтверждённую взрослую группу.</p>
      : <p className="official-museum-program-warning">Ознакомьтесь с возрастным ограничением
          в полном описании. Уточните даты и наличие мест у музея: наличие описания не означает
          запись на конкретную дату.</p>}
    <div className="official-museum-program-grid">
      {officialWorkshops.map((p,index)=>{
        const editor=published.get(p.slug);
        return <article className="official-museum-program-card" key={p.slug}>
          <p className="official-museum-program-number">Мастер-класс {String(index+1).padStart(2,"0")}</p>
          <h3>{editor?.title?.trim() || p.title}</h3>
          <p>{editor?.excerpt?.trim() || p.intro}</p>
          <details>
            <summary>Полное описание и возраст</summary>
            <div className="official-museum-program-body">
              <RichText html={editor?.body?.trim() || p.html}/>
            </div>
          </details>
          <div className="official-museum-program-links">
            {editor && <Link href={entryPublicHref(editor)} className="text-link">
              Редакция на новом сайте →
            </Link>}
            <MuseumAnchor href={p.source_url} target="_blank"
              rel="noopener noreferrer" className="text-link">Официальное описание ↗</MuseumAnchor>
          </div>
        </article>;
      })}
    </div>
    <div className="museum-workshop-footer">
      <p>Запись и билеты — на <MuseumAnchor href={officialWorkshopIndex.source_url}
        target="_blank" rel="noopener noreferrer">официальной странице мастер-классов музея ↗</MuseumAnchor>.
        Уточнение условий посещения: <Link href="/guide/plan-visit/">план визита →</Link>.</p>
      <p>Изображения мастер-классов не скопированы на новый сайт до подтверждения прав музея.</p>
    </div>
  </section>;
}
