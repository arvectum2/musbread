"use client";

import {useState} from "react";
import MuseumAnchor from "@/components/MuseumAnchor";
import Link from "@/components/MuseumLink";
import {content,entryPublicHref} from "@/data/content";
import {officialMuseumSeminars,officialSeminarCount,officialSeminarVideoCount,officialSeminarIndex} from "@/data/official-museum-seminars";

/** Seven real past seminars and genuine original recordings.
 * All VK embeds are opt-in, one at a time, no autoplay, no assumed license.
 */
export default function OfficialMuseumSeminars(){
  const [playing,setPlaying]=useState<string|null>(null);
  const revisions=new Map(content.entries
    .filter(e=>e.section_slug==="science-conferences" && e.slug.startsWith("science-seminar-"))
    .map(e=>[e.slug,e]));
  return <section className="official-science-seminars" aria-label="Реальные научные семинары музея">
    <h3>Архив семинаров с официального сайта</h3>
    <p>На <MuseumAnchor href={officialSeminarIndex} target="_blank"
      rel="noopener noreferrer" className="text-link">действующей странице семинаров музея ↗</MuseumAnchor>
      {" "}подтверждены <strong>{officialSeminarCount} научных мероприятий 2020–2026 годов</strong>
      {" "}и <strong>{officialSeminarVideoCount} видеозаписей</strong>.
      Указаны исходные названия и даты, без выдуманных выступающих, тезисов
      или будущего расписания.</p>
    <p className="official-museum-program-warning">При нажатии «Просмотреть запись»
      VK Видео получает технические данные посетителя и может использовать
      собственные cookie. До нажатия внешний плеер не загружается.
      Субтитры и права на отдельные записи требуют подтверждения.</p>
    <div className="official-museum-program-grid">
      {officialMuseumSeminars.map(seminar=>{
        const revision=revisions.get(seminar.id);
        return <article className="official-museum-program-card" key={seminar.id}>
          <p className="official-museum-program-number">
            {seminar.date_start.split("-").reverse().join(".")}
            {seminar.date_end?" — "+seminar.date_end.split("-").reverse().join("."):""}
          </p>
          <h4>{revision?.title?.trim() || seminar.title}</h4>
          {revision?.excerpt && <p>{revision.excerpt}</p>}
          {seminar.original_body_text && <p>Материалы исходной записи: {seminar.original_body_text}</p>}
          <p>Видеозаписей в первоисточнике: {seminar.video_count}.</p>
          {seminar.videos.map((vid,i)=>{
            const key=seminar.id+"-"+i;
            return <div className="official-seminar-video" key={key}>
              {playing===key&&<div className="official-video-frame">
                <iframe title={"Запись семинара: "+seminar.title+"; часть "+(i+1)}
                  src={vid.embed_url} loading="lazy" referrerPolicy="no-referrer"
                  allow="encrypted-media; fullscreen; picture-in-picture"
                  sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
                  allowFullScreen/>
              </div>}
              <button type="button" className="visitor-map-button"
                aria-expanded={playing===key}
                onClick={()=>setPlaying(current=>current===key?null:key)}>
                {playing===key?"Закрыть запись":"Просмотреть запись"} — {vid.part_label || "часть "+(i+1)}
              </button>
            </div>;
          })}
          {revision && <Link href={entryPublicHref(revision)}
            className="text-link">Редакция музейного материала →</Link>}
          <p><MuseumAnchor href={seminar.source_url} target="_blank"
              rel="noopener noreferrer" className="text-link">
            Оригинальная страница научного семинара ↗</MuseumAnchor></p>
        </article>;
      })}
    </div>
  </section>;
}
