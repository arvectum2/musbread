"use client";
import {useState} from "react";
import MuseumAnchor from "@/components/MuseumAnchor";
import type {MuseumPublishedVideo} from "@/data/types";

/** No external request until a visitor explicitly activates this verified
 * publisher-approved embed. No copied files, third-party autoplay or scripts. */
export default function MuseumInlineVideo({video}:{video:MuseumPublishedVideo}){
  const [playing,setPlaying]=useState(false);
  const [transcript,setTranscript]=useState(false);
  return <section className="museum-inline-video" aria-label={"Видеозапись: "+video.title}>
    <h3>{video.title}</h3>
    <p className="official-museum-program-warning">
      VK Видео загрузится только после нажатия; внешний сервис может обрабатывать
      технические данные и использовать cookie. До нажатия запросы к VK не выполняются.
    </p>
    <button type="button" className="visitor-map-button"
      aria-expanded={playing} onClick={()=>setPlaying(current=>!current)}>
      {playing?"Закрыть видеоплеер":"Посмотреть видеозапись"}
    </button>
    {playing&&<div className="official-video-frame">
      <iframe title={"Музейный видеоматериал: "+video.title}
        src={video.embed_url} loading="lazy" referrerPolicy="no-referrer"
        sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
        allow="encrypted-media; fullscreen; picture-in-picture" allowFullScreen/>
    </div>}
    <button type="button" className="visitor-map-button"
      aria-expanded={transcript} onClick={()=>setTranscript(current=>!current)}>
      {transcript?"Скрыть текстовую альтернативу":"Читать текстовую альтернативу"}
    </button>
    {transcript&&<div className="museum-video-transcript" role="region"
      aria-label={"Текстовая альтернатива: "+video.title}>
      <p>{video.transcript}</p>
    </div>}
    <p><MuseumAnchor href={video.source_url} target="_blank"
      rel="noopener noreferrer" className="text-link">
      Официальный источник видеоматериала ↗
    </MuseumAnchor></p>
  </section>;
}
