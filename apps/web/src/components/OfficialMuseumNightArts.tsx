"use client";

import {useEffect,useState} from "react";
import MuseumAnchor from "@/components/MuseumAnchor";
import RichText from "@/components/RichText";
import {officialMuseumNews} from "@/data/official-museum-news";
import {localCalendarDay} from "@/data/event-archive";
import type {MuseumEvent} from "@/data/types";

/**
 * One REAL upcoming event in museum's news, not to be confused with article's
 * earlier publication date. Works after Nov 3 as archived source, and never
 * duplicates an editor-published MuseumEvent record.
 */
const SOURCE_NEWS_SLUG="museum-news-2026-10-16-noch-iskusstv-v-muzee-hleba";
const CMS_EVENT_SLUG="museum-night-of-arts-2026";
const EVENT_DAY="2026-11-03";
export default function OfficialMuseumNightArts({
  events, buildDay, archiveOnly=false,
}:{events:MuseumEvent[];buildDay:string;archiveOnly?:boolean}){
  const original=officialMuseumNews.find(item=>item.slug===SOURCE_NEWS_SLUG);
  const [today,setToday]=useState(buildDay);
  useEffect(()=>{
    const refresh=()=>setToday(localCalendarDay(new Date()));
    refresh();
    const handleVisibility=()=>{if(!document.hidden)refresh();};
    document.addEventListener("visibilitychange",handleVisibility);
    const tick=window.setInterval(refresh,60_000);
    return ()=>{
      document.removeEventListener("visibilitychange",handleVisibility);
      window.clearInterval(tick);
    };
  },[]);
  if(!original || events.some(event=>event.slug===CMS_EVENT_SLUG))return null;
  const isArchive=EVENT_DAY<today;
  if(archiveOnly && !isArchive)return null;
  return <section className="official-museum-programs official-source-event"
    aria-label="Официальный анонс Ночи искусств">
    <h2>{isArchive?"Архив официальных анонсов":"Подтверждённое событие по действующему сайту музея"}</h2>
    <article className="official-museum-program-card">
      <p className="official-museum-program-number">
        {isArchive?"Мероприятие завершилось":"Предстоящая программа по официальному источнику"}
      </p>
      <h3>{original.title}</h3>
      <p><strong>Программа «Петербург гостеприимный»</strong></p>
      <p><strong>3 ноября 2026 г., 18:00–20:00.</strong> Дата и часы — из текста
        действующего музея. Новость опубликована отдельно {original.published_on.split("-").reverse().join(".")}.</p>
      <details>
        <summary>Полное описание музейной программы</summary>
        <div className="official-museum-program-body"><RichText html={original.html}/></div>
      </details>
      <p><MuseumAnchor href={original.source_url} className="text-link"
        target="_blank" rel="noopener noreferrer">
        Официальный анонс музея ↗
      </MuseumAnchor></p>
      <p className="official-museum-program-warning">Перед посещением уточните
        запись, наличие мест и возможные изменения у музея.
        Эта карточка не осуществляет продажи билетов.</p>
    </article>
  </section>;
}
