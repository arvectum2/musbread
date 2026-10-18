import MuseumAnchor from "@/components/MuseumAnchor";
import Link from "@/components/MuseumLink";
import { accessVisitFacts, accessibilityRouteCaution, museumAccessibilitySource } from "@/data/official-accessibility-visit";
import { visitorContacts } from "@/data/visitor-contacts";

type Props = { condensed?: boolean };

/** TZ-140: real visit-plan accessibility, grounded in official museum content. */
export default function VisitAccessibilityGuide({ condensed = false }: Props) {
  if (!museumAccessibilitySource) return null;
  return (
    <section className="visit-accessibility" aria-labelledby="visit-accessibility-heading">
      <h2 id="visit-accessibility-heading">Доступная среда при планировании визита</h2>
      <p>
        По сведениям{" "}
        <MuseumAnchor href={museumAccessibilitySource.source_url} target="_blank" rel="noopener noreferrer">
          действующего сайта музея
        </MuseumAnchor>
        {" "}от {museumAccessibilitySource.captured_utc.slice(0, 10)}. Это исходная
        редакция музея, не подтверждение отсутствия барьеров на каждом участке маршрута.
      </p>
      <div className="visit-accessibility-grid">
        {accessVisitFacts.slice(0, condensed ? 3 : undefined).map((fact) => (
          <section key={fact.id} className="visit-accessibility-fact" aria-label={fact.title}>
            <h3>{fact.title}</h3>
            <p>{fact.summary}</p>
          </section>
        ))}
      </div>
      {!condensed && <p className="visit-accessibility-warning">
        <strong>Особенность маршрута:</strong> {accessibilityRouteCaution.text}
      </p>}
      <p className="visit-accessibility-contact">
        Музей просит заранее позвонить перед посещением, чтобы уточнить помощь и условия доступа:{" "}
        <MuseumAnchor href={visitorContacts.phoneHref}>{visitorContacts.phone}</MuseumAnchor>.
      </p>
      <p>
        {condensed
          ? <Link href="/guide/plan-visit/" className="text-link">
              Адрес, часы работы и план визита →
            </Link>
          : <Link href="/guide/accessible-museum/" className="text-link">
              Полные условия доступности и маршрут к музею →
            </Link>}
      </p>
    </section>
  );
}
