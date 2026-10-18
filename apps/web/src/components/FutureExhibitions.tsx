"use client";

import {useEffect,useState} from "react";
import Link from "@/components/MuseumLink";
import EventCard from "@/components/EventCard";
import {futureExhibitions} from "@/data/current-exhibitions";
import {localCalendarDay} from "@/data/event-archive";
import type {MuseumEvent} from "@/data/types";

/** TZ-164: only future CMS events, no fabricated museum dates or "coming soon" cards. */
export default function FutureExhibitions({events,buildDay}:{events:MuseumEvent[];buildDay:string}){
  const [today,setToday]=useState(buildDay);
  useEffect(()=>{
    const update=()=>setToday(localCalendarDay(new Date()));
    update();
    const onVisibility=()=>{if(!document.hidden)update();};
    document.addEventListener("visibilitychange",onVisibility);
    const interval=window.setInterval(update,60_000);
    return ()=>{
      document.removeEventListener("visibilitychange",onVisibility);
      window.clearInterval(interval);
    };
  },[]);
  // Ignore the EXACT precontract "exhibition" fixture, which carries a
  // 2026-11-19 dummy date in published.json. Do not suppress real published
  // CMS events, even if their user-visible category is also "Выставка".
  const verifiedEvents=events.filter(e=>
    !(e.slug==="exhibition" &&
      e.body.includes("Сведения для испытания шаблонов")));
  const upcoming=futureExhibitions(verifiedEvents,today);
  return <section className="current-exhibitions" aria-label="Будущие выставки из CMS">
    <h2>Запланированные выставки</h2>
    <p>Показываются только выставки с датой открытия позднее сегодняшней даты,
      опубликованные редактором музея. Проверяйте актуальность расписания перед посещением.</p>
    {upcoming.length>0
      ? <div className="events-grid">{upcoming.map((event,i)=>
          <EventCard key={event.slug} event={event} index={i}/>)}</div>
      : <p role="status">Будущие выставки пока не подтверждены в новой музейной афише.
          Раздел готов к публикации реальных анонсов через MoonShine.</p>}
    <p><Link href="/guide/exhibitions-current/" className="text-link">
      Текущие выставки на действующем сайте →
    </Link></p>
  </section>;
}
