import Link from "@/components/MuseumLink";
import Image from "next/image";
import { content, entryPublicHref } from "@/data/content";
import OfficialMuseumVideoLibrary from "@/components/OfficialMuseumVideoLibrary";

/**
 * TZ-136: public gallery index of already approved CMS media.
 * Files in draft/hidden sections cannot occur in exported content.
 * Real original museum video embeds are consent gated separately below.
 */
export default function MuseumMediaHub() {
  const galleries = content.entries.filter(entry => (entry.media?.length ?? 0) > 0);
  return <section aria-label="Фото и медиаматериалы" className="museum-media-hub">
    <h2>Опубликованные фотоматериалы</h2>
    {galleries.length
      ? <div className="museum-gallery-index">
          {galleries.map(entry => {
            const first = entry.media![0];
            return <article className="museum-gallery-preview" key={entry.type + ":" + entry.slug}>
              <Link href={entryPublicHref(entry)}>
                <Image src={first.src} width={first.width} height={first.height}
                  alt={first.alt} unoptimized loading="lazy"/>
                <h3>{entry.title}</h3>
              </Link>
              <p>{entry.media!.length} {entry.media!.length === 1 ? "изображение" : "изображений"} в материале.</p>
            </article>;
          })}
        </div>
      : <p>Утверждённые фотоматериалы пока не опубликованы в новой системе.
          Файлы из закрытой редакторской медиатеки не показываются без публикации материала.</p>}
    <OfficialMuseumVideoLibrary />
    <p className="reference-source">Четвёртая рубрика исходного музейного видеоархива —
      <Link className="text-link" href="/guide/science-conferences/">«Семинары»</Link>:
      ещё семь настоящих научных встреч и 16 видеозаписей
      размещены в научном разделе, чтобы не смешивать с обычными сюжетами.
    </p>
    <p className="reference-source">Оригинальные музейные видеоплееры подключаются
      только после явного действия посетителя. Новые видео не загружаются в CMS
      без подтверждения прав, подписей и требований доступности.</p>
  </section>;
}
