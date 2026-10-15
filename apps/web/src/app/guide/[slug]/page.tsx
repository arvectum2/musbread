import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { findGuidePage, findMenuGroup, guidePages, legacyUrl, menuGroups, museumReference, REFERENCE_DATE } from "@/data/museum-reference";

type Props = { params: Promise<{ slug: string }> };
export function generateStaticParams() {
  return [...menuGroups.map(({ slug }) => ({ slug })), ...guidePages.map(({ slug }) => ({ slug }))];
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const title = findMenuGroup(slug)?.title ?? findGuidePage(slug)?.title;
  return { title: title || "Раздел не найден", robots: { index: false, follow: false } };
}
export default async function GuidePage({ params }: Props) {
  const { slug } = await params;
  const group = findMenuGroup(slug);
  const page = findGuidePage(slug);
  if (!group && !page) notFound();
  const title = group?.title || page!.title;
  const parent = group || page!.group;
  const isVisit = ["museum-contacts", "plan-visit", "tickets-and-benefits"].includes(slug);
  const isAccess = slug === "accessible-museum";
  const isCollection = slug === "science-collection";
  const groupPages = group ? group.children.map((child) => ({ ...child, href: "/guide/" + child.slug + "/" })) : [];
  const sourceUrl = page?.legacyPath ? legacyUrl(page.legacyPath) : undefined;

  return <article className="section inner-page guide-page">
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span>
      {page ? <><Link href={"/guide/" + parent.slug + "/"}>{parent.title}</Link><span aria-hidden="true">/</span></> : null}
      <span aria-current="page">{title}</span>
    </nav>
    <span className="eyebrow">ПРЕДВАРИТЕЛЬНАЯ СТРУКТУРА · {REFERENCE_DATE}</span>
    <h1>{title}</h1>
    <p className="lead">{group
      ? "Раздел будущего сайта составлен по техническому заданию и действующей структуре музея. Наполнение уточним после интервью."
      : "Эта страница пока является навигационным каркасом. Фотографии и полные музейные тексты не перенесены без согласования прав."}
    </p>
    {isVisit && <div className="reference-facts">
      <h2>Сведения с действующего сайта музея</h2>
      <p><strong>Адрес:</strong> {museumReference.address}</p>
      <p><strong>Метро:</strong> {museumReference.metro}</p>
      <p><strong>Рабочие часы:</strong> {museumReference.openingHours}. {museumReference.admissionHours}.</p>
      <p>{museumReference.closedDay}. {museumReference.sanitaryDay}.</p>
      <p><strong>Телефон:</strong> <a href={museumReference.phoneHref}>{museumReference.phone}</a></p>
      <p><strong>Почта:</strong> <a href={museumReference.emailHref}>{museumReference.email}</a></p>
      {slug === "tickets-and-benefits" && <p><a href={museumReference.ticketUrl} target="_blank" rel="noopener noreferrer" className="primary-button">Купить билет на действующей площадке ↗</a></p>}
    </div>}
    {isAccess && <div className="reference-facts">
      <h2>Справка о доступности по действующему сайту</h2>
      <p>В музее имеются пандусы и подъёмник; на действующем сайте указана доступность экспозиций первого и второго этажей.</p>
      <p>Уточнение условий посещения: <a href={museumReference.phoneHref}>{museumReference.phone}</a>.</p>
    </div>}
    {isCollection && <p className="reference-facts"><a href={museumReference.goskatalogUrl} target="_blank" rel="noopener noreferrer">Музейная коллекция в Госкаталоге ↗</a></p>}
    {groupPages.length > 0 && <div className="museum-list" aria-label={"Подразделы: " + title}>
      {groupPages.map((child) => <Link className="museum-list-item" prefetch={false} key={child.slug} href={child.href}>
        <h2>{child.title}</h2><p>{child.legacyPath ? "Есть соответствующий раздел действующего сайта" : "Раздел предусмотрен новым ТЗ"}</p>
        <span className="text-link">Перейти →</span>
      </Link>)}
    </div>}
    {sourceUrl && <p className="reference-source">
      <a href={sourceUrl} target="_blank" rel="noopener noreferrer">Посмотреть актуальные сведения на действующем сайте музея ↗</a>
    </p>}
    {page?.tenderOnly && <p className="reference-source">Страница включена по ТЗ новой закупки. Содержание будет согласовано с музеем; официальных данных пока нет.</p>}
    {page && <p><Link href={"/guide/" + parent.slug + "/"} className="text-link">← Ко всем подразделам «{parent.title}»</Link></p>}
  </article>;
}
