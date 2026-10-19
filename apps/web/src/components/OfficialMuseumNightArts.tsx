import type { MuseumEvent } from "@/data/types";
import { officialMuseumNews } from "@/data/official-museum-news";
import RichText from "@/components/RichText";
import OfficialMuseumNightArtsDisplay from "@/components/OfficialMuseumNightArtsDisplay";

/** Museum source HTML is verified and sanitized on the SERVER.
 * Do not ship all historical news, sanitize-html and image manifests
 * as browser JS just to show one dated programme card.
 */
const SOURCE_NEWS_SLUG = "museum-news-2026-10-16-noch-iskusstv-v-muzee-hleba";
const CMS_EVENT_SLUG = "museum-night-of-arts-2026";

export default function OfficialMuseumNightArts({
  events, buildDay, archiveOnly = false,
}: {events: MuseumEvent[]; buildDay: string; archiveOnly?: boolean}) {
  const original = officialMuseumNews.find(item => item.slug === SOURCE_NEWS_SLUG);
  if (!original || events.some(event => event.slug === CMS_EVENT_SLUG)) return null;
  return <OfficialMuseumNightArtsDisplay
    buildDay={buildDay}
    archiveOnly={archiveOnly}
    original={{
      title: original.title,
      published_on: original.published_on,
      source_url: original.source_url,
    }}>
    <RichText html={original.html} />
  </OfficialMuseumNightArtsDisplay>;
}
