import Link from "@/components/MuseumLink";

/** English snapshot may have no approved translations. This is a real 404,
 * not a misleading stand-in for translated museum material. */
export default function EnglishNotFound() {
  return <section className="section inner-page" lang="en">
    <nav aria-label="Breadcrumbs" className="breadcrumbs">
      <Link href="/">Home (Russian)</Link><span aria-hidden="true">/</span>
      <span aria-current="page">Page not found</span>
    </nav>
    <h1>English page not available</h1>
    <p>Only verified and approved museum translations can be published here.</p>
    <Link className="text-link" href="/" lang="ru">Русская версия →</Link>
  </section>;
}
