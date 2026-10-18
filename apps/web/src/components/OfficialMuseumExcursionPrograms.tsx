import MuseumAnchor from "@/components/MuseumAnchor";
import Link from "@/components/MuseumLink";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import {content,entryPublicHref} from "@/data/content";
import {officialExcursionBySlug} from "@/data/official-excursion-pages";
import {sourceProgramsForCategory} from "@/data/official-excursion-programs";

/** Genuine detailed descriptions, not fabricated demo event schedules. */
export default function OfficialMuseumExcursionPrograms({
  category, childrenSection = false,
}:{category:string;childrenSection?:boolean}){
  const source=officialExcursionBySlug(category);
  const items=sourceProgramsForCategory(category);
  if(!source || !items.length)return null;
  const approved=new Map(content.entries
    .filter(e=>e.type==="excursion" && e.section_slug===category)
    .map(e=>[e.slug,e]));
  return <section className="official-museum-programs" aria-label="Программы по действующему каталогу музея">
    <h2>{childrenSection
      ? "Экскурсионные программы для детей и подростков"
      : "Программы по действующему каталогу музея"}</h2>
    <p>В каталоге <strong>{items.length}</strong> {items.length===2?"программы":"программ"} с настоящими описаниями.
      Источник: <MuseumAnchor href={source.source_url} target="_blank" rel="noopener noreferrer">
        официальный раздел музея ↗
      </MuseumAnchor>. Перечень взят с музейного сайта {source.captured_utc.slice(0,10)};
      наличие программы в архиве не подтверждает свободные места или дату проведения.
      {childrenSection && " Возрастные ограничения, возможность участия взрослых и условия записи уточняйте в каждом оригинальном описании; часть программ рассчитана на подростков."}
    </p>
    <div className="official-museum-program-grid">
      {items.map((item,index)=>{
        const published=approved.get(item.slug);
        return <article className="official-museum-program-card" key={item.slug} id={item.slug}>
          <p className="official-museum-program-number">Программа {String(index+1).padStart(2,"0")}</p>
          <h3>{published?.title?.trim() || item.title}</h3>
          <OfficialMuseumSourcePhotos photos={item.image_links} label={item.title}/>
          <p>{published?.excerpt?.trim() || item.intro}</p>
          <details>
            <summary>Полное описание программы</summary>
            <div className="official-museum-program-body">
              <RichText html={published?.body?.trim() || item.html}/>
            </div>
          </details>
          <div className="official-museum-program-links">
            {published && <Link href={entryPublicHref(published)} className="text-link">
              Редакция музея на новом сайте →
            </Link>}
            <MuseumAnchor href={item.source_url} className="text-link"
              target="_blank" rel="noopener noreferrer">Официальный первоисточник ↗</MuseumAnchor>
          </div>
        </article>;
      })}
    </div>
    <p className="official-museum-program-warning">Показаны подлинные фотографии действующего музея. Для записи и уточнения условий
      обратитесь в музей по контактам на странице <Link href="/guide/plan-visit/">«Спланировать визит»</Link>.
    </p>
  </section>;
}
