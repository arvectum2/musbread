import Link from "next/link";
import { museumReference, REFERENCE_DATE } from "@/data/museum-reference";
import { menuGroups } from "@/data/navigation";
import MuseumIdentity from "@/components/MuseumIdentity";

export default function SiteFooter() {
  return <footer id="contacts" className="site-footer">
    <div className="footer-info">
      <Link href="/" className="footer-identity" aria-label="Санкт-Петербургский музей Хлеба — главная">
        <MuseumIdentity />
      </Link>
      <strong>{museumReference.legalName}</strong>
      <p>{museumReference.address}<br />Метро: {museumReference.metro}</p>
      <p><a href={museumReference.phoneHref}>{museumReference.phone}</a><br />
        <a href={museumReference.emailHref}>{museumReference.email}</a></p>
      <p>{museumReference.openingHours}<br />{museumReference.admissionHours}<br />
        {museumReference.closedDay}<br />{museumReference.sanitaryDay}</p>
      <p className="footer-source">Предварительная справка с действующего сайта на {REFERENCE_DATE}. Перед запуском уточнить у музея.</p>
    </div>
    <div className="footer-navigation">
      <h2>Разделы</h2>
      {menuGroups.map((g) => <Link key={g.slug} prefetch={false} href={"/guide/" + g.slug + "/"}>{g.title}</Link>)}
      <Link href="/news/">Новости</Link>
      <Link href="/guide/plan-visit/">Спланировать визит</Link>
      <Link href="/guide/museum-contacts/">Контакты</Link>
    </div>
    <div className="footer-legal">
      <h2>Ссылки и документы</h2>
      <Link href="/guide/museum-documents/">Документы музея — каталог</Link>
      <a href={museumReference.privacyPolicyUrl} target="_blank" rel="noopener noreferrer">Политика конфиденциальности (действующий сайт) ↗</a>
      <Link href="/guide/accessible-museum/">Доступная среда</Link>
      <a href={museumReference.visitorPricesUrl} target="_blank" rel="noopener noreferrer">Цены и льготы</a>
      <Link href="/guide/ticket-refunds/">Правила посещения и возврата — документы музея</Link>
      <a href={museumReference.refundsUrl} target="_blank" rel="noopener noreferrer">Возврат билетов</a>
      <a href={museumReference.vkUrl} target="_blank" rel="noopener noreferrer">ВКонтакте ↗</a>
      <a href={museumReference.maxUrl} target="_blank" rel="noopener noreferrer">MAX ↗</a>
      <p className="footer-source">Опрос оценки музея и рассылка ожидают утверждения заказчика. Формы сбора данных здесь не работают.</p>
    </div>
  </footer>;
}
