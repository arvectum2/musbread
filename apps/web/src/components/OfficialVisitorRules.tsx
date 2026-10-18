import Link from "@/components/MuseumLink";
import MuseumAnchor from "@/components/MuseumAnchor";
import { officialExcursionGuidance, officialOpeningHours } from "@/data/official-visitor-guidance";
import { visitorContacts } from "@/data/visitor-contacts";

/**
 * Source-backed practical visitor rules for the EXISTING museum site.
 * Never passes rules for research/collections or pandemic-era notices off
 * as an approved code of conduct for all visitors.
 */
export default function OfficialVisitorRules(){
  const organized = officialExcursionGuidance.document_links.find(x=>
    x.url.includes("prikaz_pravila_poseshcheniya_organizovannymi_gruppami_ekskursiy.pdf")
  );
  return <section className="visit-practical-rules" aria-labelledby="visit-practical-title">
    <h2 id="visit-practical-title">Перед посещением: условия экскурсий</h2>
    <p>Эти условия опубликованы на <MuseumAnchor href={officialExcursionGuidance.source_url} target="_blank" rel="noopener noreferrer">странице экскурсий музея ↗</MuseumAnchor> и относятся к экскурсионному посещению, а не заменяют официальный полный регламент поведения посетителей.</p>
    <dl className="visit-practical-list">
      <div><dt>Запись</dt><dd>Экскурсии и занятия проводятся только по предварительной записи. Телефон: <MuseumAnchor href={visitorContacts.phoneHref}>{visitorContacts.phone}</MuseumAnchor>.</dd></div>
      <div><dt>Размер группы</dt><dd>На странице музея указано до 20 детей и двух сопровождающих взрослых в детской группе. Одновременно — до 40 посетителей в двух группах.</dd></div>
      <div><dt>Продолжительность</dt><dd>Экскурсии и занятия: 50–60 минут по информации музея.</dd></div>
      <div><dt>Фотосъёмка</dt><dd>Любительские фото- и видеосъёмка бесплатны, съёмка разрешена только без вспышки.</dd></div>
    </dl>
    {organized && <p className="visit-practical-doc">
      <MuseumAnchor href={organized.url} target="_blank" rel="noopener noreferrer">
        Официальный приказ о посещении экскурсий организованными группами (PDF, скан) ↗
      </MuseumAnchor>
      <span> Этот документ относится к организованным группам и не является общими правилами поведения посетителей.</span>
    </p>}
    <p className="visit-practical-source">
      Режим работы также подтверждён <MuseumAnchor href={officialOpeningHours.source_url} target="_blank" rel="noopener noreferrer">отдельной страницей музея</MuseumAnchor>.
      {" "}Другие сведения: <Link href="/guide/faq/">частые вопросы →</Link>
    </p>
  </section>;
}
