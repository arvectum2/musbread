import MuseumAnchor from "@/components/MuseumAnchor";
import {museumAdministration, museumAdministrationCheckedAt, museumAdministrationSource} from "@/data/museum-team";

/** Public facts from existing museum website; customer must approve names before release. */
export default function MuseumTeam() {
 return <section className="museum-team" aria-label="Руководство и администрация музея">
  <h2>Руководство и администрация</h2>
  <p className="museum-team-note">Сведения сверены с действующим сайтом музея {museumAdministrationCheckedAt}.
   <strong> Используется опубликованная редакция музея; изменения сотрудники могут внести при обновлении данных.</strong></p>
  <ul className="museum-team-list">{museumAdministration.map(p=><li key={p.role}>
   <h3>{p.role}</h3><p>{p.name}</p><MuseumAnchor href={p.phoneHref}>Телефон: {p.phone}</MuseumAnchor>
  </li>)}</ul>
  <p className="museum-team-source"><MuseumAnchor href={museumAdministrationSource} target="_blank" rel="noopener noreferrer">
   Первоисточник: администрация на действующем сайте музея ↗</MuseumAnchor></p>
 </section>;
}
