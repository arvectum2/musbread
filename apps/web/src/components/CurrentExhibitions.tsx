"use client";

import {useEffect, useState} from "react";
import Link from "next/link";
import EventCard from "@/components/EventCard";
import {currentlyRunningExhibitions, futureExhibitions} from "@/data/current-exhibitions";
import {localCalendarDay} from "@/data/event-archive";
import type {MuseumEvent} from "@/data/types";

/** Reuses the existing event cards. Never implies that a future opening is
 * already running. The inclusive end date comes directly from MoonShine. */
export default function CurrentExhibitions({events,buildDay}:{
  events:MuseumEvent[]; buildDay:string;
}){
  const [today,setToday]=useState(buildDay);
  useEffect(()=>{
    const update=()=>setToday(localCalendarDay(new Date()));
    update();
    const onVisibility=()=>{if(!document.hidden) update();};
    document.addEventListener("visibilitychange",onVisibility);
    const interval=window.setInterval(update,60_000);
    return ()=>{window.clearInterval(interval);document.removeEventListener("visibilitychange",onVisibility);};
  },[]);
  const current=currentlyRunningExhibitions(events,today);
  const future=futureExhibitions(events,today);
  return <section className="current-exhibitions" aria-label="Актуальные выставки из опубликованной афиши">
    <h2>Идут сейчас</h2>
    {current.length>0
      ? <div className="events-grid">{current.map((event,i)=><EventCard key={event.slug} event={event} index={i}/>)}</div>
      : <p role="status">На сегодня в новой афише нет подтверждённых действующих выставок. Это не означает, что в музее их нет.</p>}
    <h2>Скоро откроются</h2>
    {future.length>0
      ? <div className="events-grid">{future.map((event,i)=><EventCard key={event.slug} event={event} index={i}/>)}</div>
      : <p>Будущие выставки пока не опубликованы.</p>}
    <p><Link href="/events/" className="text-link">Все опубликованные события и архив →</Link></p>
  </section>;
}
