import MuseumAnchor from "@/components/MuseumAnchor";
import type { Metadata } from "next";
import Link from "@/components/MuseumLink";
import { notFound } from "next/navigation";
import { guideHref, legacyUrl, museumReference, REFERENCE_DATE } from "@/data/museum-reference";
import {visitorContacts} from "@/data/visitor-contacts";
import { findGuidePage, findMenuGroup, guidePages, menuGroups, navigationTree, usesCmsNavigation } from "@/data/navigation";
import { findPublicNavigationNode } from "@/data/navigation-tree";
import NavigationBranch from "@/components/NavigationBranch";
import OfficialMuseumDocuments from "@/components/OfficialMuseumDocuments";
import MuseumTeam from "@/components/MuseumTeam";
import MuseumRichBody from "@/components/MuseumRichBody";
import OfficialMuseumSourcePhotos from "@/components/OfficialMuseumSourcePhotos";
import OfficialExpositionRooms from "@/components/OfficialExpositionRooms";
import VisitAccessibilityGuide from "@/components/VisitAccessibilityGuide";
import OfficialVisitorRules from "@/components/OfficialVisitorRules";
import OfficialVisitorFAQ from "@/components/OfficialVisitorFAQ";
import {officialExpositionSlugs} from "@/data/official-exposition-rooms";
import {officialSnapshotByPath} from "@/data/official-page-snapshots";
import {officialExcursionBySlug} from "@/data/official-excursion-pages";
import OfficialMuseumExcursionPrograms from "@/components/OfficialMuseumExcursionPrograms";
import MuseumShopShowcase from "@/components/MuseumShopShowcase";
import OfficialMuseumWorkshops from "@/components/OfficialMuseumWorkshops";
import OfficialMuseumExhibitions from "@/components/OfficialMuseumExhibitions";
import OfficialMuseumScience, {isScienceSection} from "@/components/OfficialMuseumScience";
import OfficialMuseumNightArts from "@/components/OfficialMuseumNightArts";
import OfficialMuseumSessions from "@/components/OfficialMuseumSessions";
import OfficialMuseumMap from "@/components/OfficialMuseumMap";
import OfficialMuseumSocialLinks from "@/components/OfficialMuseumSocialLinks";
import {exhibitionSourceIndex,officialExhibitionSourceSlugs} from "@/data/official-exhibitions";
import {officialWorkshopSlugs} from "@/data/official-workshops";
import {isProgramCategory,originalMuseumProgramSlugs} from "@/data/official-excursion-programs";
import MuseumMediaHub from "@/components/MuseumMediaHub";
import CurrentExhibitions from "@/components/CurrentExhibitions";
import FutureExhibitions from "@/components/FutureExhibitions";
import EventAgenda from "@/components/EventAgenda";
import {isAgendaSection,publishedEventsForAgendaSection} from "@/data/agenda-sections";
import {events} from "@/data/content";
import { officialMuseumGroupsForPage } from "@/data/museum-official-documents";
import { content, entriesInCmsSection, entryPublicHref } from "@/data/content";
import { siteSeoApproved } from "@/data/seo-routes";
import {fixedPageSeo, fixedPageH1} from "@/data/fixed-page-seo";

type Props = { params: Promise<{ slug: string }> };
export function generateStaticParams() {
  return [...menuGroups.map(({ slug }) => ({ slug })), ...guidePages.map(({ slug }) => ({ slug }))];
}
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const title = findMenuGroup(slug)?.title ?? findGuidePage(slug)?.title;
  const section = content.sections?.find((item) => item.slug === slug);
  const guide = findGuidePage(slug);
  const sourceTitle = officialSnapshotByPath(guide?.legacyPath)?.title
    || officialExcursionBySlug(slug)?.title;
  const cmsPage = content.entries.find((entry) => entry.type === "page" && entry.slug === slug);
  const fallback = fixedPageSeo("/guide/" + slug + "/");
  // Fallback/reference guide pages are unapproved prototypes. Only an
  // explicit site-approval gate permits indexing approved CMS section routes.
  const approved = siteSeoApproved(process.env.MUSBREAD_SITE_APPROVED) && !!section;
  return {
    title: cmsPage?.seo_title?.trim() || section?.seo_title?.trim() || fallback?.seo_title?.trim() || sourceTitle || title || "Раздел не найден",
    description: cmsPage?.seo_description?.trim() || section?.seo_description?.trim() || fallback?.seo_description?.trim() || undefined,
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
  const childExcursionCategory = slug === "children-interactive" ? "excursion-interactive"
    : slug === "children-thematic" ? "excursion-thematic" : null;
  const isTeam = slug === "museum-team";
  const groupPages = group && !usesCmsNavigation ? group.children.map((child) => ({ ...child, href: guideHref(child.slug) })) : [];
  const directChildren = usesCmsNavigation ? findPublicNavigationNode(navigationTree, slug)?.children ?? [] : [];
  // A page published for this exact guide slug is the body of the
  // current route, not a second entry in its own "Материалы раздела" list.
  const sectionEntries = usesCmsNavigation
    ? entriesInCmsSection(slug).filter((entry) =>
      !(entry.type === "page" && entry.slug === slug)
      // Room catalogue already displays source-backed CMS room revisions.
      && !(slug === "museum-exposition" && officialExpositionSlugs.has(entry.slug))
      // Genuine source programs (including approved CMS revisions) are
      // presented once in the detailed category cards, not duplicated below.
      && !(isProgramCategory(slug) && originalMuseumProgramSlugs.has(entry.slug))
      && !(slug === "children-workshops" && officialWorkshopSlugs.has(entry.slug))
      && !(exhibitionSourceIndex(slug) && officialExhibitionSourceSlugs.has(entry.slug))
      && !(slug === "science-materials" && ["science-organization","science-methodical-council"].includes(entry.slug)))
    : [];
  const sourceUrl = page?.legacyPath ? legacyUrl(page.legacyPath) : undefined;
  const officialSnapshot = officialSnapshotByPath(page?.legacyPath)
    || officialExcursionBySlug(slug);
  // Museum-owned CMS content takes precedence; an operator can replace the
  // official-site reference by publishing a page with this exact guide slug.
  const cmsPage = content.entries.find((entry) => entry.type === "page" && entry.slug === slug);
  const referenceBody = cmsPage?.body?.trim() || officialSnapshot?.html;
  // The source-backed catalogue replaces the old 11-link index; still
  // show a museum-authored CMS introduction after its own publication.
  const showReferenceBody = !!referenceBody
    && !["museum-contacts", "museum-team", "museum-cookie"].includes(slug)
    && (slug !== "museum-exposition" || !!cmsPage)
    && (!isProgramCategory(slug) || !!cmsPage)
    && (!exhibitionSourceIndex(slug) || !!cmsPage);
  const sourceDate = officialSnapshot?.captured_utc.slice(0, 10);

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
    <span className="eyebrow">{cmsPage
      ? "ОПУБЛИКОВАНО РЕДАКТОРОМ МУЗЕЯ"
      : page?.legacyPath
      ? "РАЗДЕЛ НА ДЕЙСТВУЮЩЕМ САЙТЕ"
      : page ? "НОВЫЙ РАЗДЕЛ ПО ТЗ — ЧЕРНОВИК" : "НАВИГАЦИЯ ПО ТЗ — ПРОЕКТ"} · {REFERENCE_DATE}</span>
    <h1>{cmsPage?.h1?.trim() || cmsPage?.title?.trim() || publishedSection?.h1?.trim() || fixedPageH1("/guide/" + slug + "/",title)}</h1>
    <p className="lead">{group
      ? "Раздел будущего сайта составлен по техническому заданию и действующей структуре музея. Наполнение уточним после интервью."
      : isTeam
        ? "Список должностных лиц и служебные телефоны перенесены с действующего сайта музея; публикация обновлённого списка требует подтверждения заказчика."
        : page?.legacyPath
          ? (slug === "museum-exposition"
              ? "Все 11 залов постоянной экспозиции перенесены с действующего сайта музея. Их описания можно раскрыть ниже и впоследствии изменить через CMS."
              : isVisit && content.visitor_contacts
              ? "Сведения о посещении перенесены с официального сайта и могут обновляться из CMS."
              : showReferenceBody
                ? "Содержание перенесено с действующего официального сайта музея как исходная редакция. Заказчик сможет изменить его в CMS."
                : "Этот раздел существует на официальном сайте музея; пока сохранена ссылка на первоисточник.")
          : cmsPage
            ? "Этот раздел опубликован редактором музея; сведения можно изменять через CMS."
            : slug === "faq"
            ? "Ответы собраны по действующим официальным материалам музея. Вопросы подготовлены для нового сайта и могут уточняться редактором."
            : isScienceSection(slug)
            ? "Научный раздел использует только официально подтверждённые документы музея, публикации редактора и музейный Госкаталог. Неустановленные сведения не выдумываются."
            : slug === "exhibitions-future"
            ? "Раздел будущих выставок готов: отображаются только утверждённые события с будущими датами начала. Действительных анонсов пока нет."
            : exhibitionSourceIndex(slug)
            ? "Реальный каталог выставок перенесён с действующего сайта музея, даты и статусы соответствуют исходной редакции на дату снимка."
            : ["children-workshops","excursion-workshops-adults"].includes(slug)
            ? "Реальные музейные мастер-классы перенесены с действующего сайта. Возраст, даты и условия участия уточняйте по официальному первоисточнику."
            : slug === "museum-shop"
            ? "Витрина магазина по ТЗ: без онлайн-продажи, а ассортимент заполняется только проверенными материалами музея."
            : childExcursionCategory
            ? "Представлены реальные экскурсионные программы с описаниями и возрастными ограничениями действующего музея. Редактируемые карточки программы находятся в CMS."
            : "Этот раздел требуется ТЗ, но сведения на действующем сайте не найдены."}
    </p>
    <div className={directChildren.length > 0 ? "guide-content-layout" : "guide-content-layout guide-content-single"}>
      <div className="guide-primary">
    {isVisit && <div className="reference-facts">
      <h2>{content.visitor_contacts ? "Сведения, утверждённые музеем" : "Сведения с действующего сайта музея"}</h2>
      <p><strong>Адрес:</strong> {visitorContacts.address}</p>
      <p><strong>Метро:</strong> {visitorContacts.metro}</p>
      <p><strong>Рабочие часы:</strong> {visitorContacts.openingHours}. {visitorContacts.admissionHours}.</p>
      <p>{visitorContacts.closedDay}. {visitorContacts.sanitaryDay}.</p>
      <p><strong>Телефон:</strong> <MuseumAnchor href={visitorContacts.phoneHref}>{visitorContacts.phone}</MuseumAnchor></p>
      <p><strong>Почта:</strong> <MuseumAnchor href={visitorContacts.emailHref}>{visitorContacts.email}</MuseumAnchor></p>
      {(isContact || isPlanVisit) && <section aria-label="Как добраться">
        <h3>Как добраться</h3>
        <p>Ближайшая станция метро: {visitorContacts.metro}. Адрес для навигатора: {visitorContacts.address}.</p>
        <OfficialMuseumMap/>
        <p><Link href="/guide/accessible-museum/" className="text-link">Условия доступности музея</Link> · <MuseumAnchor href={museumReference.accessibilityUrl} target="_blank" rel="noopener noreferrer" className="text-link">Официальная информация на действующем сайте ↗</MuseumAnchor></p>
      </section>}
      {slug === "tickets-and-benefits" && <p><MuseumAnchor href={museumReference.ticketUrl} target="_blank" rel="noopener noreferrer" className="primary-button">Купить билет на действующей площадке ↗</MuseumAnchor></p>}
    </div>}
    {isAccess && <div className="reference-facts">
      <h2>Справка о доступности по действующему сайту</h2>
      <p>В музее имеются пандусы и подъёмник; на действующем сайте указана доступность экспозиций первого и второго этажей.</p>
      <p>Уточнение условий посещения: <MuseumAnchor href={visitorContacts.phoneHref}>{visitorContacts.phone}</MuseumAnchor>.</p>
      <p>Перед посещением уточните доступный вход, возможность сопровождения и временные ограничения по телефону музея. <MuseumAnchor href={museumReference.accessibilityUrl} target="_blank" rel="noopener noreferrer" className="text-link">Актуальные сведения о доступности на официальном сайте ↗</MuseumAnchor>.</p>
    </div>}
    {isPlanVisit && !cmsPage && officialSnapshotByPath("/adres") && <section
      className="reference-facts official-source-content"
      aria-label="Как добраться: официальная инструкция музея">
      <h2>Подробный маршрут к музею</h2>
      <p className="meta">Текст действующей страницы музея:
        <MuseumAnchor href="https://muzei-xleb.ru/adres" target="_blank"
          rel="noopener noreferrer">оригинальная инструкция «Адрес» ↗</MuseumAnchor>.
      </p>
      <MuseumRichBody html={officialSnapshotByPath("/adres")!.html}/>
    </section>}
    {(isContact || isPlanVisit) && <OfficialMuseumSocialLinks />}
    {isPlanVisit && <VisitAccessibilityGuide />}
    {isPlanVisit && <OfficialVisitorRules />}
    {slug === "museum-shop" && <MuseumShopShowcase />}
    {isScienceSection(slug) && <OfficialMuseumScience section={slug} />}
    {exhibitionSourceIndex(slug) && <OfficialMuseumExhibitions category={slug} />}
    {slug === "children-workshops" && <OfficialMuseumWorkshops audience="children" />}
    {slug === "excursion-workshops-adults" && <OfficialMuseumWorkshops audience="adults" />}
    {slug === "faq" && !cmsPage && <OfficialVisitorFAQ />}
    {isAccess && <VisitAccessibilityGuide condensed />}
    {slug === "museum-exposition" && <OfficialExpositionRooms />}
    {isProgramCategory(slug) && <OfficialMuseumExcursionPrograms category={slug} />}
    {childExcursionCategory && <OfficialMuseumExcursionPrograms category={childExcursionCategory} childrenSection />}
    {isTeam && <MuseumTeam />}
    {slug === "museum-media" && <MuseumMediaHub />}
    {slug === "exhibitions-current" && <CurrentExhibitions
      events={events} buildDay={new Date().toISOString().slice(0,10)} />}
    {slug === "exhibitions-future" && <FutureExhibitions
      events={events} buildDay={new Date().toISOString().slice(0,10)} />}
    {(slug === "agenda" || slug === "agenda-events") && <p className="reference-source">
      <Link href="/events/" className="text-link">Открыть афишу и архив мероприятий →</Link>
      <span> · Пока там тестовые записи; программа публикуется на <MuseumAnchor href={museumReference.newsUrl} target="_blank" rel="noopener noreferrer">действующем сайте музея ↗</MuseumAnchor>.</span>
    </p>}
    {(slug==="agenda-archive" || slug==="agenda-events") &&
      <OfficialMuseumNightArts events={events} buildDay={new Date().toISOString().slice(0,10)}
        archiveOnly={slug==="agenda-archive"} />}
    {(["agenda-excursions","agenda-children","agenda-meetings",
      "agenda-workshops","agenda-festivals","agenda-exhibitions",
      "agenda-archive"] as const).some(x=>x===slug) && <OfficialMuseumSessions
      section={slug as "agenda-excursions"|"agenda-children"|"agenda-meetings"|"agenda-workshops"|"agenda-festivals"|"agenda-exhibitions"|"agenda-archive"}
      events={events} buildDay={new Date().toISOString().slice(0,10)}/>}
    {isAgendaSection(slug) && <section className="guide-agenda-category" aria-label={"Мероприятия раздела: " + title}>
      <h2>{slug === "agenda-archive" ? "Прошедшие мероприятия" : "События и программа"}</h2>
      <p>Ниже показаны только записи, опубликованные редактором CMS. Демонстрационные записи не являются официальным расписанием музея.</p>
      <EventAgenda
        events={publishedEventsForAgendaSection(events,slug)}
        buildDay={new Date().toISOString().slice(0,10)}
        initialPeriod={slug === "agenda-archive" ? "archive" : "upcoming"}
      />
      <p className="reference-source">Проверенная афиша музея доступна на <MuseumAnchor href={museumReference.newsUrl} target="_blank" rel="noopener noreferrer">официальном действующем сайте ↗</MuseumAnchor>.</p>
    </section>}
    {showReferenceBody && <section aria-label="Содержание действующего сайта музея" className="reference-facts official-source-content">
      <h2>{cmsPage ? "Содержание, опубликованное редактором музея" : "Содержание с официального сайта музея"}</h2>
      {officialSnapshot && !cmsPage && <p className="meta">Источник: {officialSnapshot.source_url} · проверено {sourceDate}.
        Текст перенесён без самостоятельной юридической редакции; заказчик может обновить страницу в CMS.</p>}
      <MuseumRichBody html={referenceBody!} videos={cmsPage?.videos} />
      {!cmsPage && officialSnapshot?.image_links?.length
        && ["https://muzei-xleb.ru/istoriya-zdaniya",
            "https://muzei-xleb.ru/obzornaya-ekskursiya",
            "https://muzei-xleb.ru/informaciya-dlya-mgn"].includes(officialSnapshot.source_url)
        ? <div className="official-museum-original-gallery">
            <h3>Оригинальные фотографии музея ({officialSnapshot.image_links.length})</h3>
            <OfficialMuseumSourcePhotos photos={officialSnapshot.image_links}
              label={officialSnapshot.title} limit={30}/>
          </div> : null}
    </section>}
    {slug === "museum-cookie" && <p className="reference-facts">
      Документ описывает использование cookie на прежнем сайте музея. Мы сохраняем ссылку на действующую редакцию,
      но не переносим утверждения о целях и согласиях на новую техническую платформу без проверки используемых сервисов.
      На этом прототипе собственные формы получения согласия и аналитические cookie не добавлялись.
    </p>}
    {cmsPage?.documents && cmsPage.documents.length > 0 && <section className="official-documents" aria-label="Документы опубликованной редакции CMS">
      <h2>Документы музея для скачивания</h2>
      <p className="official-documents-notice">Оригинальные файлы опубликованы из редакционной системы музея.
        Если документ ещё не прошёл проверку доступности, используйте описание на странице или обратитесь в музей.</p>
      <ul className="official-documents-list">{cmsPage.documents.map((document) => <li key={document.href}>
        <MuseumAnchor href={document.href} download className="text-link">
          {document.label} ({document.format.toUpperCase()}, {Math.ceil(document.size_bytes / 1024)} КБ)
        </MuseumAnchor>
        {document.accessibility_reviewed && document.accessibility_note
          ? <p className="museum-document-accessibility">{document.accessibility_note}</p>
          : <p className="museum-document-accessibility">Доступность документа ещё не проверена редактором.</p>}
      </li>)}</ul>
    </section>}
    {!cmsPage && <OfficialMuseumDocuments groups={officialMuseumGroupsForPage(slug)} />}
    {["children", "children-pushkin-card", "exhibitions-guide", "exhibitions-pushkin-card"].includes(slug) && <section className="reference-facts" aria-label="Переход к Пушкинской карте">
      <h2>«Пушкинская карта»</h2>
      <p>Условия участия и актуальная информация размещены на действующем официальном сайте музея. Участие конкретного мероприятия в программе необходимо уточнять перед посещением.</p>
      <MuseumAnchor href={legacyUrl("/pushkinskaya-karta")} target="_blank" rel="noopener noreferrer" className="primary-button">Открыть «Пушкинскую карту» на сайте музея ↗</MuseumAnchor>
    </section>}
    {directChildren.length > 0 && <p className="guide-subnav-hint">
      Подразделы этого раздела доступны в боковой навигации; на мобильном экране — ниже основного текста.
    </p>}
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
      <MuseumAnchor href={sourceUrl} target="_blank" rel="noopener noreferrer">Открыть исходную страницу на действующем сайте музея ↗</MuseumAnchor>
    </p>}
    {page?.tenderOnly && !cmsPage && slug !== "faq" && slug !== "museum-shop" && !isScienceSection(slug) && slug !== "exhibitions-future" && !exhibitionSourceIndex(slug) && slug !== "children-workshops" && slug !== "excursion-workshops-adults" && !childExcursionCategory && <p className="reference-source">Страница включена по ТЗ новой закупки. Содержание будет согласовано с музеем; официальных данных пока нет.</p>}
    {page && (page.ancestors.length > 0 || findMenuGroup(parent.slug)
      ? <p><Link href={"/guide/" + (page.ancestors.at(-1)?.slug ?? parent.slug) + "/"} className="text-link">← Ко всем подразделам «{page.ancestors.at(-1)?.title ?? parent.title}»</Link></p>
      : <p><Link href="/" className="text-link">← На главную</Link></p>)}
      </div>
      {directChildren.length > 0 && <aside className="guide-sidebar" aria-label={"Навигация по подразделам: "+title}>
        <h2>Подразделы</h2>
        <NavigationBranch nodes={directChildren}/>
      </aside>}
    </div>
  </article>;
}
