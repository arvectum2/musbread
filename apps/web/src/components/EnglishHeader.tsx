import Link from "next/link";
import VisionMode from "@/components/VisionMode";
import { content, sections } from "@/data/content";
import { museumReference } from "@/data/museum-reference";

const englishPages = content.entries.filter((entry) => entry.translations?.en).map((entry) => {
  const section = Object.entries(sections).find(([, item]) => item.type === entry.type)?.[0];
  return { title: entry.translations!.en.title, url: "/en/" + section + "/" + entry.slug + "/" };
});

export default function EnglishHeader() {
  return <header className="site-header" lang="en">
    <a href="#main" className="skip-link">Skip to content</a>
    <div className="header-inner">
      <Link href="/" className="wordmark" aria-label="Museum of Bread — Russian home page">
        <span className="brand-mark" aria-hidden="true">✳</span>
        <span>MUSEUM OF BREAD</span>
      </Link>
      <nav className="main-nav" aria-label="English navigation">
        {englishPages.map((entry) => <Link key={entry.url} href={entry.url}>{entry.title}</Link>)}
        <Link href="/" lang="ru">Русская версия / Russian site</Link>
      </nav>
      <div className="header-controls">
        <VisionMode locale="en"/>
        <a href={museumReference.ticketUrl} className="header-action" target="_blank"
           rel="noopener noreferrer" aria-label="Tickets on external Russian-language booking site, opens a new tab">
          Tickets (Russian) ↗
        </a>
      </div>
      <details className="mobile-nav">
        <summary aria-label="Open menu">Menu ☰</summary>
        <nav aria-label="English mobile navigation">
          {englishPages.map((entry) => <Link key={entry.url} href={entry.url}>{entry.title}</Link>)}
          <Link href="/" lang="ru">Русская версия / Russian site</Link>
        </nav>
      </details>
    </div>
  </header>;
}
