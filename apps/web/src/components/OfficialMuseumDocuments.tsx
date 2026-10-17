import MuseumAnchor from "@/components/MuseumAnchor";
import type {MuseumOfficialDocumentGroup} from "@/data/museum-official-documents";

/** Catalogue of original museum-owned files; no new legal wording. */
export default function OfficialMuseumDocuments({groups}:{groups:readonly MuseumOfficialDocumentGroup[]}) {
  if(!groups.length)return null;
  return <section className="official-documents" aria-label="Официальные документы музея">
    <h2>Официальные документы музея</h2>
    <p className="official-documents-notice">Ниже ссылки на документы и страницы <strong>действующего сайта Музея хлеба</strong>.
      Это справочная копия структуры: перед запуском нового сайта музей должен подтвердить актуальность редакций.
      Мы не изменяем содержание утверждённых документов.</p>
    {groups.map(group=><section key={group.title} className="official-documents-group" aria-label={group.title}>
      <h3>{group.title}</h3>
      <ul className="official-documents-list">{group.items.map(doc=><li key={doc.url}>
        <MuseumAnchor href={doc.url} target="_blank" rel="noopener noreferrer">{doc.label} <span aria-label="Открыть на действующем сайте музея">↗</span></MuseumAnchor>
        <span className="official-document-format">{doc.format}</span>
      </li>)}</ul>
      <p className="official-documents-source">Все документы раздела на <MuseumAnchor href={group.source} target="_blank" rel="noopener noreferrer">действующем сайте музея ↗</MuseumAnchor></p>
    </section>)}
  </section>;
}
