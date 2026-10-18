import MuseumAnchor from "@/components/MuseumAnchor";
import Link from "@/components/MuseumLink";
import RichText from "@/components/RichText";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import { content, entryPublicHref } from "@/data/content";
import {
  officialExpositionCaptureDate,
  officialExpositionRooms,
  officialExpositionSource,
} from "@/data/official-exposition-rooms";

/**
 * Source-backed TZ-131 room catalogue including all genuine museum photos,
 * drawn directly from the original museum image URLs for the working copy.
 *
 * If the editor publishes a corresponding room page in the existing CMS, its
 * editorial text wins. Until then the official museum's current version is
 * visible as a labelled, independently verifiable reference, not fake copy.
 */
export default function OfficialExpositionRooms() {
  const revisions = new Map(
    content.entries.filter((entry) => entry.type === "page"
      && entry.section_slug === "museum-exposition").map((entry) => [entry.slug, entry]),
  );

  return <section className="exposition-catalog" aria-label="Залы постоянной экспозиции">
    <h2>Залы постоянной экспозиции</h2>
    <p className="exposition-catalog-intro">
      {officialExpositionRooms.length} залов по действующему
      <MuseumAnchor href={officialExpositionSource}> каталогу музея</MuseumAnchor>.
      Описания перенесены из официальных страниц, проверенных {officialExpositionCaptureDate}.
      Все фотографии экспозиции показаны по исходным опубликованным ссылкам музея.
    </p>
    <div className="exposition-cards">
      {officialExpositionRooms.map((room, index) => {
        const revision = revisions.get(room.slug);
        const title = revision?.title?.trim() || room.title;
        const description = revision?.body ?? room.html;
        return <article className="exposition-card" key={room.slug} id={room.slug}>
          <p className="exposition-card-index">Зал {String(index + 1).padStart(2, "0")} из {officialExpositionRooms.length}</p>
          <h3>{title}</h3>
          <p>{revision?.excerpt?.trim() || room.excerpt}</p>
          {room.image_sources.length>0 && <details className="exposition-photo-details">
            <summary>Фотографии зала ({room.image_sources.length})</summary>
            <OfficialMuseumSourcePhotos photos={room.image_sources.map(image=>({
              url:image.source_url,alt:image.alt,
            }))} label={title} limit={30}/>
          </details>}
          <details>
            <summary>Описание зала</summary>
            <div className="exposition-card-body">
              {description.trim()
                ? <RichText html={description} />
                : <p>Редактор музея пока не опубликовал описание этого зала.</p>}
            </div>
          </details>
          <p className="exposition-card-links">
            {revision && <Link className="text-link" href={entryPublicHref(revision)}>
              Открыть редакцию музея →
            </Link>}
            <MuseumAnchor className="text-link" href={room.source_url}
              target="_blank" rel="noopener noreferrer">
              Первоисточник ↗
            </MuseumAnchor>
          </p>
        </article>;
      })}
    </div>
  </section>;
}
