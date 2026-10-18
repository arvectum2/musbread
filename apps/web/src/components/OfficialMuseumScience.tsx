import Link from "@/components/MuseumLink";
import MuseumAnchor from "@/components/MuseumAnchor";
import RichText from "@/components/RichText";
import EventAgenda from "@/components/EventAgenda";
import {content,entriesInCmsSection,entryPublicHref} from "@/data/content";
import {officialScienceInstitutionalRecords,museumCollectionsAccessDocument} from "@/data/official-science";
import {museumReference} from "@/data/museum-reference";

type ScienceSection="science-conferences"|"science-publications"|"science-collection"|"science-researchers"|"science-materials";
export function isScienceSection(section:string):section is ScienceSection{
  return ["science-conferences","science-publications","science-collection",
    "science-researchers","science-materials"].includes(section);
}
const permittedConferenceCategories=new Set([
  "Научный семинар","Семинар","Научная конференция","Конференция",
]);
const heading:Record<ScienceSection,string>={
  "science-conferences":"Семинары и научные конференции",
  "science-publications":"Научные публикации музея",
  "science-collection":"Музейная коллекция",
  "science-researchers":"Информация для исследователей",
  "science-materials":"Научные и научно-организационные материалы",
};

/**
 * Source-backed science gateway. Never turns fund administration PDFs into
 * academic publications or claims to have found individual collection objects.
 */
export default function OfficialMuseumScience({section}:{section:ScienceSection}){
  const approved=entriesInCmsSection(section).filter(e=>
    !(e.type==="page" && e.slug===section));
  const sourceEntries=approved.filter(e=>e.type==="page" || e.type==="news");
  const newsEvents=content.events.filter(e=>permittedConferenceCategories.has(e.category.trim()));
  return <section className="museum-science-portal" aria-label={heading[section]}>
    <h2>{heading[section]}</h2>

    {section==="science-conferences" && <>
      <p>Ниже показываются только научные мероприятия, отдельно опубликованные в редакторской
        афише музея с категорией «Семинар», «Научный семинар», «Конференция» или
        «Научная конференция». Административные документы не считаются проведёнными конференциями.</p>
      <EventAgenda events={newsEvents} buildDay={new Date().toISOString().slice(0,10)}/>
      {!newsEvents.length && <p role="status">На действующем сайте музея не обнаружено
        подтверждённого календаря научных конференций для переноса.
        Раздел подготовлен для публикации музеем.</p>}
    </>}

    {section==="science-publications" && <>
      <p>Страница библиографии предусмотрена ТЗ. Публикации появятся после
        размещения редактором проверенных авторов, названий, выходных данных
        и сведений о правах. Положения об организации музея не являются
        научными публикациями.</p>
      {!sourceEntries.length && <p role="status">Подтверждённая библиография
        научных работ музея пока не предоставлена.</p>}
    </>}

    {section==="science-collection" && <>
      <p>В официальном источнике музея опубликована ссылка на его коллекцию
        в Государственном каталоге Музейного фонда Российской Федерации.
        Самостоятельный каталог отдельных предметов с проверенными
        инвентарными данными и разрешёнными фотографиями пока не предоставлен.</p>
      <p><MuseumAnchor className="text-link" href={museumReference.goskatalogUrl}
        rel="noopener noreferrer" target="_blank">
        Открыть музейную коллекцию в Госкаталоге ↗
      </MuseumAnchor></p>
      <p className="museum-science-note">Госкаталог — внешняя система;
        доступность конкретной страницы зависит от её работы.
        Ссылку взяли непосредственно с действующего сайта музея.</p>
      {!sourceEntries.length && <p role="status">Описание отдельных предметов
        и право на публикацию музейных фотографий требуют материалов заказчика.</p>}
    </>}

    {section==="science-researchers" && <>
      <p>Музей опубликовал официальный документ об условиях доступа граждан
        к музейным предметам и коллекциям. Он является исходным документом
        для ознакомления, но не заменяет специальный порядок записи
        внешних исследователей и не гарантирует доступ в фонды.</p>
      {museumCollectionsAccessDocument && <p><MuseumAnchor
        className="text-link" href={museumCollectionsAccessDocument.url}
        target="_blank" rel="noopener noreferrer">
        {museumCollectionsAccessDocument.label} (PDF, официальный источник) ↗
      </MuseumAnchor></p>}
      <p>Для уточнения условий работы с коллекцией обратитесь
        к сотрудникам музея через <Link href="/guide/museum-contacts/" className="text-link">
          официальные контакты</Link>.
        Подачи заявки и сбора данных исследователей на этой странице нет.</p>
      {!sourceEntries.length && <p role="status">Регламент исследовательских
        обращений, заявки и условия работы с фондовыми материалами
        отдельно пока не предоставлены.</p>}
    </>}

    {section==="science-materials" && <>
      <p>Следующие документы действительно размещены музеем
        в разделах научно-организационной деятельности и научно-методического совета.
        Это <strong>организационные документы</strong>, а не библиография
        научных статей или доказательство проведения конференций.</p>
      <div className="official-museum-program-grid">
        {officialScienceInstitutionalRecords.map(item=>{
          const published=approved.find(e=>e.slug===item.slug);
          return <article key={item.slug} className="official-museum-program-card">
            <h3>{published?.title?.trim() || item.title}</h3>
            <p className="meta">Официальная редакция музея,
              снимок {item.captured_utc.slice(0,10)}</p>
            <div className="museum-science-article">
              <RichText html={published?.body?.trim() || item.html}/>
            </div>
            <div className="official-museum-program-links">
              {published && <Link className="text-link" href={entryPublicHref(published)}>
                Редакция музея на новом сайте →</Link>}
              <MuseumAnchor className="text-link" href={item.source_url}
                target="_blank" rel="noopener noreferrer">Исходная страница музея ↗</MuseumAnchor>
            </div>
          </article>;
        })}
      </div>
    </>}

    {sourceEntries.filter(e=>section!=="science-materials" ||
      !officialScienceInstitutionalRecords.some(src=>src.slug===e.slug)).length>0 && <>
      <h3>Материалы, опубликованные редактором</h3>
      <div className="museum-list">
        {sourceEntries.filter(e=>section!=="science-materials" ||
          !officialScienceInstitutionalRecords.some(src=>src.slug===e.slug)).map(e=>
          <Link key={e.slug} className="museum-list-item" href={entryPublicHref(e)}>
            <h3>{e.title}</h3>{e.excerpt && <p>{e.excerpt}</p>}
            <span className="text-link">Читать →</span>
          </Link>)}
      </div>
    </>}
    <p className="museum-science-note">
      В раздел не добавляются вымышленные публикации, семинары,
      инвентарные номера, условия доступа или изображения музейных предметов.
    </p>
  </section>;
}
