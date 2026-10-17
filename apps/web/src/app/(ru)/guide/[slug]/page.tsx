import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { guideHref, legacyUrl, museumReference, museumAddressMapSearchUrl, REFERENCE_DATE } from "@/data/museum-reference";
import { findGuidePage, findMenuGroup, guidePages, menuGroups, navigationTree, usesCmsNavigation } from "@/data/navigation";
import { findPublicNavigationNode } from "@/data/navigation-tree";
import NavigationBranch from "@/components/NavigationBranch";
import OfficialMuseumDocuments from "@/components/OfficialMuseumDocuments";
import MuseumTeam from "@/components/MuseumTeam";
import MuseumMediaHub from "@/components/MuseumMediaHub";
import CurrentExhibitions from "@/components/CurrentExhibitions";
import {events} from "@/data/content";
import { officialMuseumGroupsForPage } from "@/data/museum-official-documents";
import { content, entriesInCmsSection, entryPublicHref } from "@/data/content";
import { siteSeoApproved } from "@/data/seo-routes";

type Props = { params: Promise<{ slug: string }> };
export function generateStaticParams() {
  return [...menuGroups.map(({ slug }) => ({ slug })), ...guidePages.map(({ slug }) => ({ slug }))];
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const title = findMenuGroup(slug)?.title ?? findGuidePage(slug)?.title;
  const section = content.sections?.find((item) => item.slug === slug);
  // Fallback/reference guide pages are unapproved prototypes. Only an
  // explicit site-approval gate permits indexing approved CMS section routes.
  const approved = siteSeoApproved(process.env.MUSBREAD_SITE_APPROVED) && !!section;
  return {
    title: section?.seo_title?.trim() || title || "Раздел не найден",
    description: section?.seo_description?.trim() || undefined,
    robots: { index: approved, follow: approved },
  };
}
export default async function GuidePage({ params }: Props) {
  const { slug } = await params;
  const group = findMenuGroup(slug);
  const page = findGuidePage(slug);
  if (!group && !page) notFound();
  const title = group?.title || page!.title;
  const publishedSection = content.sections?.find((item) => item.slug === slug);
  const parent = group || page!.group;
  const isVisit = ["museum-contacts", "plan-visit", "tickets-and-benefits"].includes(slug);
  const isContact = slug === "museum-contacts";
  const isPlanVisit = slug === "plan-visit";
  const isAccess = slug === "accessible-museum";
  const isCollection = slug === "science-collection";
  const isTeam = slug === "museum-team";
  const groupPages = group && !usesCmsNavigation ? group.children.map((child) => ({ ...child, href: guideHref(child.slug) })) : [];
  const directChildren = usesCmsNavigation ? findPublicNavigationNode(navigationTree, slug)?.children ?? [] : [];
  const sectionEntries = usesCmsNavigation ? entriesInCmsSection(slug) : [];
  const sourceUrl = page?.legacyPath ? legacyUrl(page.legacyPath) : undefined;

  return <article className="section inner-page guide-page">
    <nav aria-label="Хлебные крошки" className="breadcrumbs">
      <Link href="/">Главная</Link><span aria-hidden="true">/</span>
      {page ? page.ancestors.map((ancestor) =>
        <span className="crumb-node" key={ancestor.slug}>
          <Link href={"/guide/" + ancestor.slug + "/"}>{ancestor.title}</Link>
          <span aria-hidden="true">/</span>
        </span>) : null}
      <span aria-current="page">{title}</span>
    </nav>
    <span className="eyebrow">{page?.legacyPath
      ? "РАЗДЕЛ НА ДЕЙСТВУЮЩЕМ САЙТЕ"
      : page ? "НОВЫЙ РАЗДЕЛ ПО ТЗ — ЧЕРНОВИК" : "НАВИГАЦИЯ ПО ТЗ — ПРОЕКТ"} · {REFERENCE_DATE}</span>
    <h1>{publishedSection?.h1?.trim() || title}</h1>
    <p className="lead">{group
      ? "Раздел будущего сайта составлен по техническому заданию и действующей структуре музея. Наполнение уточним после интервью."
      : isTeam
        ? "Список должностных лиц и служебные телефоны перенесены с действующего сайта музея; публикация обновлённого списка требует подтверждения заказчика."
        : page?.legacyPath
          ? "Такой раздел уже есть на действующем сайте музея. Здесь пока справочный маршрут к первоисточнику, а не копия полного текста или подтверждение его актуальности."
          : "Этот раздел требуется ТЗ, но музей ещё не предоставил утверждённые сведения. Придумывать их не будем."}
    </p>
    {isVisit && <div className="reference-facts">
      <h2>Сведения с действующего сайта музея</h2>
      <p><strong>Адрес:</strong> {museumReference.address}</p>
      <p><strong>Метро:</strong> {museumReference.metro}</p>
      <p><strong>Рабочие часы:</strong> {museumReference.openingHours}. {museumReference.admissionHours}.</p>
      <p>{museumReference.closedDay}. {museumReference.sanitaryDay}.</p>
      <p><strong>Телефон:</strong> <a href={museumReference.phoneHref}>{museumReference.phone}</a></p>
      <p><strong>Почта:</strong> <a href={museumReference.emailHref}>{museumReference.email}</a></p>
      {(isContact || isPlanVisit) && <section aria-label="Как добраться">
        <h3>Как добраться</h3>
        <p>Ближайшая станция метро: {museumReference.metro}. Адрес для навигатора: {museumReference.address}.</p>
        <p><a href={museumAddressMapSearchUrl} target="_blank" rel="noopener noreferrer" className="text-link">Найти адрес на карте ↗</a> <small>(внешний поиск адреса, без передачи данных посещения этой страницей)</small></p>
        <p><Link href="/guide/accessible-museum/" className="text-link">Условия доступности музея</Link> · <a href={museumReference.accessibilityUrl} target="_blank" rel="noopener noreferrer" className="text-link">Официальная информация на действующем сайте ↗</a></p>
      </section>}
      {slug === "tickets-and-benefits" && <p><a href={museumReference.ticketUrl} target="_blank" rel="noopener noreferrer" className="primary-button">Купить билет на действующей площадке ↗</a></p>}
    </div>}
    {isAccess && <div className="reference-facts">
      <h2>Справка о доступности по действующему сайту</h2>
      <p>В музее имеются пандусы и подъёмник; на действующем сайте указана доступность экспозиций первого и второго этажей.</p>
      <p>Уточнение условий посещения: <a href={museumReference.phoneHref}>{museumReference.phone}</a>.</p>
      <p>Перед посещением уточните доступный вход, возможность сопровождения и временные ограничения по телефону музея. <a href={museumReference.accessibilityUrl} target="_blank" rel="noopener noreferrer" className="text-link">Актуальные сведения о доступности на официальном сайте ↗</a>.</p>
    </div>}
    {isTeam && <MuseumTeam />}
    {slug === "museum-media" && <MuseumMediaHub />}
    {slug === "exhibitions-current" && <CurrentExhibitions
      events={events} buildDay={new Date().toISOString().slice(0,10)} />}
    {(slug === "agenda" || slug === "agenda-events") && <p className="reference-source">
      <Link href="/events/" className="text-link">Открыть афишу и архив мероприятий →</Link>
      <span> · Пока там тестовые записи; программа публикуется на <a href={museumReference.newsUrl} target="_blank" rel="noopener noreferrer">действующем сайте музея ↗</a>.</span>
    </p>}
    <OfficialMuseumDocuments groups={officialMuseumGroupsForPage(slug)} />
    {isCollection && <p className="reference-facts"><a href={museumReference.goskatalogUrl} target="_blank" rel="noopener noreferrer">Музейная коллекция в Госкаталоге ↗</a></p>}
    {directChildren.length > 0 && <section aria-label={"Подразделы: " + title}>
      <h2>Подразделы</h2>
      <NavigationBranch nodes={directChildren}/>
    </section>}
    {sectionEntries.length > 0 && <section className="section-entries" aria-label={"Материалы раздела: " + title}>
      <h2>Материалы раздела</h2>
      <div className="museum-list">{sectionEntries.map((entry) =>
        <Link key={`${entry.type}:${entry.slug}`} className="museum-list-item" prefetch={false} href={entryPublicHref(entry)}>
          <h3>{entry.title}</h3>
          {entry.excerpt && <p>{entry.excerpt}</p>}
          <span className="text-link">Читать →</span>
        </Link>)}
      </div>
    </section>}
    {groupPages.length > 0 && <div className="museum-list" aria-label={"Подразделы: " + title}>
      {groupPages.map((child) => <Link className="museum-list-item" prefetch={false} key={child.slug} href={child.href}>
        <h2>{child.title}</h2><p>{child.legacyPath ? "Есть соответствующий раздел действующего сайта" : "Раздел предусмотрен новым ТЗ"}</p>
        <span className="text-link">Перейти →</span>
      </Link>)}
    </div>}
    {sourceUrl && <p className="reference-source">
      <a href={sourceUrl} target="_blank" rel="noopener noreferrer">Открыть исходную страницу на действующем сайте музея ↗</a>
    </p>}
    {page?.tenderOnly && <p className="reference-source">Страница включена по ТЗ новой закупки. Содержание будет согласовано с музеем; официальных данных пока нет.</p>}
    {page && <p><Link href={"/guide/" + (page.ancestors.at(-1)?.slug ?? parent.slug) + "/"} className="text-link">← Ко всем подразделам «{page.ancestors.at(-1)?.title ?? parent.title}»</Link></p>}
  </article>;
}
