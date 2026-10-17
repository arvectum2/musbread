import {museumAdministration, museumAdministrationCheckedAt, museumAdministrationSource} from "@/data/museum-team";

/** Public facts from existing museum website; customer must approve names before release. */
export default function MuseumTeam() {
 return <section className="museum-team" aria-label="Руководство и администрация музея">
  <h2>Руководство и администрация</h2>
  <p className="museum-team-note">Сведения сверены с действующим сайтом музея {museumAdministrationCheckedAt}.
   <strong> Перед публикацией новой версии заказчик подтверждает актуальность должностей, ФИО и контактов.</strong></p>
  <ul className="museum-team-list">{museumAdministration.map(p=><li key={p.role}>
   <h3>{p.role}</h3><p>{p.name}</p><a href={p.phoneHref}>Телефон: {p.phone}</a>
  </li>)}</ul>
  <p className="museum-team-source"><a href={museumAdministrationSource} target="_blank" rel="noopener noreferrer">
   Первоисточник: администрация на действующем сайте музея ↗</a></p>
 </section>;
}
