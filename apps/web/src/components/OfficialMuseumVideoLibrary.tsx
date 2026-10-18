"use client";

import {useState} from "react";
import MuseumAnchor from "@/components/MuseumAnchor";
import {originalMuseumVideos,originalMuseumVideosCount} from "@/data/official-museum-videos";

/**
 * Real museum /video hierarchy. Only one third-party VK iframe exists AFTER
 * explicit interaction; changing category/closing player removes that iframe.
 * Direct broadcaster .mp4 is linked, never treated as iframe/video autoplay.
 */
export default function OfficialMuseumVideoLibrary(){
  const [category,setCategory]=useState("museum");
  const [playing,setPlaying]=useState<string|null>(null);
  const active=originalMuseumVideos.find(group=>group.slug===category)??originalMuseumVideos[0];
  if(!active)return null;
  return <section className="official-video-library" aria-label="Официальные видео музея">
    <h2>Видеоматериалы с действующего сайта музея</h2>
    <p>Перенесены <strong>{originalMuseumVideosCount} настоящих видеоматериала</strong>
      {" "}из трёх тематических подразделов. Заголовки и видеоссылки сохранены
      по <MuseumAnchor href="https://muzei-xleb.ru/video" target="_blank"
        rel="noopener noreferrer">официальному видеоархиву музея ↗</MuseumAnchor>.
      Файлы и обложки не копировались.</p>
    <div className="official-video-categories" role="group" aria-label="Темы музейного видео">
      {originalMuseumVideos.map(group=><button key={group.slug} type="button"
        aria-pressed={category===group.slug}
        onClick={()=>{setCategory(group.slug);setPlaying(null);}}>
        {group.title} <span>({group.count})</span>
      </button>)}
    </div>
    <p className="official-museum-program-warning">
      Видео из ВКонтакте загружается исключительно по вашему нажатию на конкретный ролик.
      После нажатия сторонний видеосервис может обрабатывать технические данные
      и использовать собственные cookie. До этого плееры не подключаются.
      Доступность субтитров зависит от первоначального видеосервиса.
    </p>
    <div className="official-video-grid">
      {active.videos.map(video=><article key={video.id} className="official-video-card">
        <h3>{video.title}</h3>
        {video.kind==="vk"&&video.embed_url
          ? <>
            {playing===video.id
              ? <div className="official-video-frame">
                  <iframe
                    title={"Видео музея: "+video.title}
                    src={video.embed_url}
                    loading="lazy"
                    referrerPolicy="no-referrer"
                    sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
                    allow="encrypted-media; fullscreen; picture-in-picture"
                    allowFullScreen/>
                </div>
              : <p>Проигрыватель VK Видео ещё не загружен.</p>}
            <button type="button" className="visitor-map-button"
              aria-expanded={playing===video.id}
              onClick={()=>setPlaying(previous=>previous===video.id?null:video.id)}>
              {playing===video.id?"Закрыть видео":"Посмотреть видео"}
            </button>
          </>
          : <p><MuseumAnchor href={video.direct_file_url} target="_blank"
              rel="noopener noreferrer" className="text-link">
              Открыть оригинальное видео телеканала ↗
            </MuseumAnchor> (MP4 на внешнем сайте; локальный проигрыватель не создаётся).</p>}
        <p className="official-video-source">
          <MuseumAnchor href={video.source_page} className="text-link"
            target="_blank" rel="noopener noreferrer">
            Страница ролика на сайте музея ↗
          </MuseumAnchor>
          {video.kind==="vk"&&!video.hosted_in_museum_vk_group
            ? " · Ролик размещён на стороннем VK-канале, но показан на сайте музея."
            : ""}
        </p>
      </article>)}
    </div>
    <p className="official-museum-program-warning">
      Это публикации действующего музея, а не перенос исключительных прав на видеозаписи.
      Перед контрактной публикацией необходимо проверить разрешения на материалы
      сторонних правообладателей и доступность субтитров/текстовых альтернатив.
    </p>
  </section>;
}
