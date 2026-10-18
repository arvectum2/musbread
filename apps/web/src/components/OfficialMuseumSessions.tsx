"use client";

import {useEffect,useMemo,useState} from "react";
import MuseumAnchor from "@/components/MuseumAnchor";
import Link from "@/components/MuseumLink";
import {localCalendarDay} from "@/data/event-archive";
import {officialMuseumSessions,officialSessionSourceStats,sourceAgendaMatches} from "@/data/official-agenda-sessions";
import type {SourceAgendaSection} from "@/data/official-agenda-sessions";
import type {MuseumEvent} from "@/data/types";

/** Source-backed event schedule from literal dates in six official weekly bulletins.
 * Every session has a real source URL; no session lengths, tickets, prices or photos inferred.
 */
export default function OfficialMuseumSessions({section,events,buildDay}:{
  section:SourceAgendaSection;
  events:MuseumEvent[];
  buildDay:string;
}){
  const [today,setToday]=useState(buildDay);
  const [showArchive,setShowArchive]=useState(section==="agenda-archive");
  const [expanded,setExpanded]=useState(false);
  useEffect(()=>{
    const refresh=()=>setToday(localCalendarDay(new Date()));
    refresh();
    const onVisible=()=>{if(!document.hidden)refresh();};
    document.addEventListener("visibilitychange",onVisible);
    const timer=window.setInterval(refresh,60_000);
    return ()=>{
      document.removeEventListener("visibilitychange",onVisible);
      window.clearInterval(timer);
    };
  },[]);
  const approvedSlugs=useMemo(()=>new Set(events.map(e=>e.slug)),[events]);
  const all=useMemo(()=>officialMuseumSessions
    .filter(x=>sourceAgendaMatches(x,section)&&!approvedSlugs.has(x.slug)),[section,approvedSlugs]);
  const upcoming=all.filter(e=>e.date>=today);
  const archived=all.filter(e=>e.date<today);
  const candidate=showArchive?archived:upcoming;
  const order=[...candidate].sort((a,b)=>showArchive
    ? b.date.localeCompare(a.date)||a.time.localeCompare(b.time)||a.title.localeCompare(b.title,"ru")
    : a.date.localeCompare(b.date)||a.time.localeCompare(b.time)||a.title.localeCompare(b.title,"ru"));
  const visible=expanded?order:order.slice(0,15);
  const groups=new Map<string,typeof visible>();
  for(const entry of visible){
    const siblings=groups.get(entry.date)||[];
    siblings.push(entry);
    groups.set(entry.date,siblings);
  }
  return <section className="official-museum-programs official-agenda-sessions"
    aria-label="Проверенные сеансы из официальных недельных афиш музея">
    <h2>Подтверждённые даты и время из музейных афиш</h2>
    <p>Из <strong>{officialSessionSourceStats.bulletins} опубликованных музейных выпусков</strong>
      {" "}извлечено {officialSessionSourceStats.raw} строк; после удаления
      повторов получилось <strong>{officialSessionSourceStats.unique} отдельных сеанса</strong>
      за сентябрь–октябрь 2026 года. Указаны только исходные
      даты начала, время начала, названия и возрастные ограничения.
      Места, стоимость, продолжительность и доступность записи не подтверждены.</p>
    {section==="agenda-children" && <p>
      Здесь показаны программы с опубликованной минимальной возрастной маркировкой
      от 5+ до 10+. Это отбор по возрасту, а не утверждение, что программы
      предназначены исключительно для детей.</p>}
    {section==="agenda-meetings" && <p>Источник содержит литературные гостиные,
      но не содержит отдельно подтверждённых встреч, лекций и презентаций.</p>}
    {section==="agenda-festivals" && <p>В этих недельных выпусках нет
      подтверждённых отдельных фестивальных сеансов.</p>}
    {section==="agenda-exhibitions" && <p>Выставки имеют отдельные
      <Link className="text-link" href="/guide/exhibitions-current/">официальные каталоги →</Link>,
      а не выдуманные сеансы с началом в указанное время.</p>}
    {section!=="agenda-archive"&&<div className="event-periods" role="group"
      aria-label="Официальные сеансы: период">
      <button type="button" aria-pressed={!showArchive}
        onClick={()=>{setShowArchive(false);setExpanded(false);}}>По расписанию <span>({upcoming.length})</span></button>
      <button type="button" aria-pressed={showArchive}
        onClick={()=>{setShowArchive(true);setExpanded(false);}}>Архив <span>({archived.length})</span></button>
    </div>}
    {visible.length>0
      ? <div className="official-museum-sessions-list">
          {Array.from(groups).map(([day,entries])=><section key={day} className="official-session-day"
            aria-label={"Дата программы: "+day}>
            <h3>{day.split("-").reverse().join(".")}</h3>
            <div className="official-museum-program-grid">
              {entries.map(entry=><article className="official-museum-program-card" key={entry.slug}>
                <p className="official-museum-program-number">{entry.category} · {entry.time} · {entry.age_min}+</p>
                <h4>{entry.title}</h4>
                <p className="official-museum-program-links"><MuseumAnchor href={entry.source_urls[0]}
                  rel="noopener noreferrer" target="_blank" className="text-link">
                  Музейный первоисточник ↗
                </MuseumAnchor></p>
              </article>)}
            </div>
          </section>)}
        </div>
      : <p role="status">В отобранных официальных выпусках {showArchive
        ? "нет подтверждённых прошедших сеансов этой категории."
        : "нет подтверждённых будущих сеансов этой категории."}
        {" "}Это не означает, что музей не проводит такие программы.</p>}
    {!expanded&&order.length>visible.length&&<button type="button"
      className="text-link" onClick={()=>setExpanded(true)}>
      Показать все {order.length} подтверждённых записей ({order.length-visible.length} ещё)
    </button>}
    {expanded&&order.length>15&&<button type="button" className="text-link"
      onClick={()=>setExpanded(false)}>Свернуть список</button>}
    <p className="official-museum-program-warning">
      Данные — историческая редакция недельной афиши, не живое бронирование.
      Для актуальных дат и доступности билетов сверяйтесь с
      {" "}<MuseumAnchor href="https://muzei-xleb.ru/novosty" target="_blank"
        rel="noopener noreferrer">действующими объявлениями музея ↗</MuseumAnchor>.
      При публикации изменённой записи редактором MoonShine справочная карточка
      того же сеанса скрывается автоматически.</p>
  </section>;
}
