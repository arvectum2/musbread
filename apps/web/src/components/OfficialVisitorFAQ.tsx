import MuseumAnchor from "@/components/MuseumAnchor";
import { officialVisitorFAQ } from "@/data/official-visitor-guidance";

/**
 * Questions are an editorial navigation aid, not a claim that the old museum
 * hosted these exact questions or that they are legally binding regulations.
 * Published CMS page body (when present) takes precedence over this fallback.
 */
export default function OfficialVisitorFAQ(){
  return <section className="visitor-faq" aria-label="Частые вопросы о посещении музея">
    <h2>Ответы по действующим материалам музея</h2>
    <p>Вопросы подготовлены для нового сайта. Ответы основаны на опубликованных страницах музея. Последние условия и расписание следует сверять по указанным официальным источникам.</p>
    <div className="visitor-faq-list">
      {officialVisitorFAQ.map((item,i)=><details key={item.id} className="visitor-faq-item">
        <summary><span className="visitor-faq-number" aria-hidden="true">{String(i+1).padStart(2,"0")}</span>{item.question}</summary>
        <div className="visitor-faq-answer">
          <p>{item.answer}</p>
          <p><MuseumAnchor href={item.source_url} target="_blank" rel="noopener noreferrer">Подтвердить на сайте музея ↗</MuseumAnchor></p>
        </div>
      </details>)}
    </div>
  </section>;
}
