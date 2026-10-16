/**
 * Short factual metadata and URLs from muzei-xleb.ru, checked 2026-10-15.
 * NOT an approved identity, content license, or guarantee of ongoing accuracy.
 */
export const REFERENCE_DATE = "15.10.2026";
export const LEGACY_BASE = "https://muzei-xleb.ru";
export const museumReference = {
  legalName: "СПб ГБУК «Санкт-Петербургский музей Хлеба»",
  shortName: "Санкт-Петербургский музей Хлеба",
  address: "195009, Санкт-Петербург, ул. Михайлова, д. 2, лит. А",
  metro: "Площадь Ленина, выход к Финляндскому вокзалу",
  phone: "+7 (812) 294-50-82",
  phoneHref: "tel:+78122945082",
  email: "musbread@cult.gugov.spb.ru",
  emailHref: "mailto:musbread@cult.gugov.spb.ru",
  openingHours: "Среда — понедельник, 10:00–18:00",
  admissionHours: "Касса и вход — до 17:00",
  closedDay: "Вторник — выходной",
  sanitaryDay: "Последний четверг месяца — санитарный день",
  ticketUrl: "https://vmuzey.com/museum/sankt-peterburgskiy-muzey-hleba",
  goskatalogUrl: "https://goskatalog.ru/portal/#/collections?museumIds=1200",
  vkUrl: "https://vk.com/club37126776",
  maxUrl: "https://max.ru/id7808018523_gos",
  privacyPolicyUrl: "https://muzei-xleb.ru/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh",
  accessibilityUrl: "https://muzei-xleb.ru/informaciya-dlya-mgn",
  visitorPricesUrl: "https://muzei-xleb.ru/stoimost",
  refundsUrl: "https://muzei-xleb.ru/ceny-i-usloviya-predostavleniya-uslug",
} as const;

/** External address lookup rather than unverified geo-coordinates or a third-party embed. */
export const museumAddressMapSearchUrl = "https://yandex.ru/maps/?text=" + encodeURIComponent(museumReference.address);

export type SitePage = { slug: string; title: string; legacyPath?: string; tenderOnly?: boolean };
export type MenuGroup = { slug: string; title: string; children: readonly SitePage[] };
const legacy = (slug: string, title: string, legacyPath: string): SitePage =>
  ({ slug, title, legacyPath });
const requested = (slug: string, title: string): SitePage =>
  ({ slug, title, tenderOnly: true });

/** Tender's seven groups + selected extra sections preserved from live website. */
export const menuGroups: readonly MenuGroup[] = [
  { slug: "museum", title: "Музей", children: [
    legacy("museum-history", "История музея", "/o-muzee"),
    legacy("building-history", "История здания", "/istoriya-zdaniya"),
    legacy("museum-exposition", "Экспозиция", "/ekspozicii"),
    legacy("museum-team", "Команда и администрация", "/administraciya"),
    requested("friends", "Друзья музея"),
    legacy("museum-documents", "Официальные документы", "/oficialnye-dokumenty-muzeya"),
    legacy("museum-finance", "Финансово-хозяйственная деятельность", "/finansovo-hozyaystvennaya-deyatelnost"),
    legacy("museum-science-administration", "Научно-организационная деятельность", "/nauchno-organizacionnaya-deyatelnost"),
    legacy("museum-scientific-council", "Научно-методический совет", "/nauchno-metodicheskiy-sovet"),
    legacy("museum-accounting-policy", "Учётная политика", "/uchetnaya-politika"),
    legacy("museum-anti-corruption", "Противодействие коррупции", "/protivodeystvie-korrupcii"),
    legacy("museum-anti-terror", "Противодействие терроризму", "/protivodeystvie-terrorizmu"),
    legacy("museum-antimonopoly", "Антимонопольный комплаенс", "/antimonopolnyy-komplaens"),
    legacy("museum-accessibility-policy", "Политика обеспечения доступности", "/politika-obespecheniya-usloviy-dostupnosti-dlya-invalidov-i-drugih-mobilnyh-grazhdan"),
    legacy("museum-privacy", "Политика конфиденциальности и обработки ПДн", "/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh"),
    legacy("museum-media", "Медиа", "/video"),
    legacy("museum-vacancies", "Вакансии", "/vakansii"),
    legacy("museum-contacts", "Контакты", "/kontakty"),
  ] },
  { slug: "visitors", title: "Посетителям", children: [
    legacy("plan-visit", "Спланировать визит", "/posetitelyam"),
    legacy("tickets-and-benefits", "Билеты и льготы", "/stoimost"),
    requested("pushkin-card", "Пушкинская карта"),
    legacy("accessible-museum", "Доступная среда", "/informaciya-dlya-mgn"),
    requested("museum-shop", "Магазин (без продажи)"),
    requested("faq", "Частые вопросы"),
    legacy("museum-donors", "Информация для дарителей", "/informaciya-dlya-dariteley"),
    legacy("museum-feedback", "Гостевая книга (действующий сайт)", "/gostevaya-kniga"),
    legacy("ticket-refunds", "Правила возврата билетов", "/ceny-i-usloviya-predostavleniya-uslug"),
  ] },
  { slug: "agenda", title: "Афиша", children: [
    requested("agenda-events", "Все события"),
    requested("agenda-excursions", "Экскурсии"),
    requested("agenda-children", "Детям"),
    requested("agenda-exhibitions", "Выставки"),
    requested("agenda-meetings", "Встречи"),
    requested("agenda-festivals", "Фестивали"),
    requested("agenda-workshops", "Мастер-классы"),
    requested("agenda-archive", "Архив"),
  ] },
  { slug: "excursions-guide", title: "Экскурсии", children: [
    legacy("excursion-overview", "Обзорная экскурсия", "/obzornaya-ekskursiya"),
    legacy("excursion-interactive", "Интерактивные экскурсии", "/interaktivnye-zanyatiya"),
    legacy("excursion-thematic", "Тематические экскурсии", "/tematicheskie-ekskursii"),
    requested("excursion-workshops-adults", "Мастер-классы для взрослых"),
    legacy("excursion-theatrical", "Театрализованные экскурсии", "/teatralizovannye-ekskursii"),
  ] },
  { slug: "children", title: "Детям", children: [
    requested("children-interactive", "Интерактивные экскурсии"),
    requested("children-thematic", "Тематические экскурсии"),
    requested("children-workshops", "Мастер-классы для детей"),
    requested("children-pushkin-card", "Пушкинская карта"),
  ] },
  { slug: "exhibitions-guide", title: "Выставки", children: [
    legacy("exhibitions-current", "Текущие выставки", "/vistavky/tekushchie-vystavki"),
    requested("exhibitions-future", "Будущие выставки"),
    legacy("exhibitions-traveling", "Передвижные и выездные выставки", "/vistavky/vyezdnye-vystavki"),
    legacy("exhibitions-past", "Прошедшие выставки", "/vistavky/proshedshie-vystavki"),
    legacy("exhibitions-virtual", "Виртуальные выставки", "/vistavky/virtualnye-vystavki"),
    requested("exhibitions-pushkin-card", "Пушкинская карта"),
  ] },
  { slug: "science", title: "Наука", children: [
    requested("science-conferences", "Семинары и конференции"),
    requested("science-publications", "Публикации"),
    requested("science-collection", "Коллекция"),
    requested("science-researchers", "Исследователям"),
    requested("science-materials", "Материалы по теме"),
  ] },
] as const;

export type GuidePage = SitePage & { group: MenuGroup; href: string };
export const guidePages: readonly GuidePage[] = menuGroups.flatMap((group) =>
  group.children.map((page) => ({ ...page, group, href: "/guide/" + page.slug + "/" }))
);
export const findGuidePage = (slug: string) => guidePages.find((page) => page.slug === slug);
export const findMenuGroup = (slug: string) => menuGroups.find((group) => group.slug === slug);
export const legacyUrl = (path: string) => new URL(path, LEGACY_BASE).href;
