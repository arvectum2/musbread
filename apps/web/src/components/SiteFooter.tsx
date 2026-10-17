import MuseumAnchor from "@/components/MuseumAnchor";
import Link from "@/components/MuseumLink";
import { museumReference, REFERENCE_DATE } from "@/data/museum-reference";
import {visitorContacts} from "@/data/visitor-contacts";
import { menuGroups } from "@/data/navigation";
import MuseumIdentity from "@/components/MuseumIdentity";
import {content} from "@/data/content";

export default function SiteFooter() {
  return <footer id="contacts" className="site-footer">
    <div className="footer-info">
      <Link href="/" className="footer-identity" aria-label="Санкт-Петербургский музей Хлеба — главная">
        <MuseumIdentity />
      </Link>
      <strong>{museumReference.legalName}</strong>
      <p>{visitorContacts.address}<br />Метро: {visitorContacts.metro}</p>
      <p><MuseumAnchor href={visitorContacts.phoneHref}>{visitorContacts.phone}</MuseumAnchor><br />
        <MuseumAnchor href={visitorContacts.emailHref}>{visitorContacts.email}</MuseumAnchor></p>
      <p>{visitorContacts.openingHours}<br />{visitorContacts.admissionHours}<br />
        {visitorContacts.closedDay}<br />{visitorContacts.sanitaryDay}</p>
      <p className="footer-source">{content.visitor_contacts ? "Сведения опубликованы из CMS музея." : <>Действующие сведения с официального сайта музея на {REFERENCE_DATE}; сотрудники могут обновить их в CMS.</>}</p>
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
      <MuseumAnchor href={museumReference.privacyPolicyUrl} target="_blank" rel="noopener noreferrer">Политика конфиденциальности (действующий сайт) ↗</MuseumAnchor>
      <Link href="/guide/accessible-museum/">Доступная среда</Link>
      <MuseumAnchor href={museumReference.visitorPricesUrl} target="_blank" rel="noopener noreferrer">Цены и льготы</MuseumAnchor>
      <Link href="/guide/ticket-refunds/">Правила посещения и возврата — документы музея</Link>
      <MuseumAnchor href={museumReference.refundsUrl} target="_blank" rel="noopener noreferrer">Возврат билетов</MuseumAnchor>
      <MuseumAnchor href={museumReference.vkUrl} target="_blank" rel="noopener noreferrer">ВКонтакте ↗</MuseumAnchor>
      <MuseumAnchor href={museumReference.maxUrl} target="_blank" rel="noopener noreferrer">MAX ↗</MuseumAnchor>
      <MuseumAnchor href={museumReference.surveyUrl} target="_blank" rel="noopener noreferrer">Оценить работу музея — официальная анкета ↗</MuseumAnchor>
      <Link href="/guide/museum-cookie/">Информация об использовании cookie на действующем сайте</Link>
      <p className="footer-source">Анкета открывается на внешнем сервисе по ссылке действующего музея. Собственные формы обработки персональных данных и рассылка на прототипе не работают.</p>
    </div>
  </footer>;
}
