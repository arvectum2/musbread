/**
 * Existing museum-owned documents, not generated legal policies.
 * Titles and file URLs were checked against https://muzei-xleb.ru on 17.10.2026.
 * Source versions are accepted as the current museum editions for migration;
 * any later correction or replacement is handled by museum editors.
 * UI patterns inspired by rusmuseum.ru and spbmuseum.ru; NO copied legal text.
 */
export type MuseumOfficialDocument = {
  label: string;
  url: string;
  format: "PDF" | "DOCX" | "Официальная страница";
};
export type MuseumOfficialDocumentGroup = {
  title: string;
  source: string;
  items: readonly MuseumOfficialDocument[];
};
const base = "https://muzei-xleb.ru";
const official = (file: string): string => `${base}${file}`;
const pages = {
  foundation: official("/oficialnye-dokumenty-muzeya"),
  privacy: official("/politika-konfidencialnosti-i-obrabotki-personalnyh-dannyh"),
  visits: official("/ceny-i-usloviya-predostavleniya-uslug"),
  accessible: official("/politika-obespecheniya-usloviy-dostupnosti-dlya-invalidov-i-drugih-mobilnyh-grazhdan"),
  accessVisitors: official("/informaciya-dlya-mgn"),
  finance: official("/finansovo-hozyaystvennaya-deyatelnost"),
  anticorruption: official("/protivodeystvie-korrupcii"),
} as const;
export const officialMuseumDocumentSources = pages;

const founding: MuseumOfficialDocumentGroup = {
  title: "Учредительные документы и сведения об учреждении",
  source: pages.foundation,
  items: [
    {label:"Устав музея",url:official("/sites/default/files/page/20260203114639-ustav_2011.docx"),format:"DOCX"},
    {label:"Изменения в Устав 2022",url:official("/sites/default/files/page/20260203114727-izmeneniya_v_ustav_2022.pdf"),format:"PDF"},
    {label:"Реквизиты учреждения",url:official("/sites/default/files/page/20260203114846-rekvizity_uchrezhdeniya.pdf"),format:"PDF"},
    {label:"Учредитель музея",url:official("/sites/default/files/page/20260203115202-uchreditel_muzeya.pdf"),format:"PDF"},
    {label:"Приказ о назначении директора музея",url:official("/sites/default/files/page/20260203115235-prikaz_o_naznachenii_direktora_muzeya.pdf"),format:"PDF"},
    {label:"Структура музея",url:official("/sites/default/files/page/20260203115739-struktura_muzeya.pdf"),format:"PDF"},
  ],
};
const privacy: MuseumOfficialDocumentGroup = {
  title: "Политики обработки персональных данных музея",
  source: pages.privacy,
  items: [
    {label:"Политика по обработке и защите персональных данных",url:official("/sites/default/files/page/20260203104919-1.pdf"),format:"PDF"},
    {label:"Политика обработки персональных данных пользователей сайта",url:official("/sites/default/files/page/20260203104920-1.pdf"),format:"PDF"},
  ],
};
const visiting: MuseumOfficialDocumentGroup = {
  title: "Правила посещения и билеты",
  source: pages.visits,
  items: [
    {label:"Сведения о видах предоставляемых услуг",url:official("/sites/default/files/page/20260203112119-svedeniya_o_vidah_predostavlyaemyh_uslug.pdf"),format:"PDF"},
    {label:"Положение о платных услугах",url:official("/sites/default/files/page/20260203112237-polozhenie_o_platnyh_uslugah.pdf"),format:"PDF"},
    {label:"Положение о порядке и условиях доступа граждан к музейным предметам и музейным коллекциям",url:official("/sites/default/files/page/20260203112347-poryadok_dostupa.pdf"),format:"PDF"},
    {label:"Положение о порядке приобретения и возврата кассовых чеков, билетов, экскурсионных путевок в СПб ГБУК «Санкт-Петербургский музей Хлеба»",url:official("/sites/default/files/page/20260203113223-1.pdf"),format:"PDF"},
    {label:"Приложение № 1 к Положению о порядке приобретения и возврата кассовых чеков, экскурсионных путевок, билетов",url:official("/sites/default/files/page/20260203113346-prilozhenie_1_k_polozheniyu_o_vozvrate.docx"),format:"DOCX"},
    {label:"Приказ о применении сервиса Цифрового ID",url:official("/sites/default/files/page/20260203113458-prikaz_o_primenenii_servisa_cifrovogo_id.pdf"),format:"PDF"},
    {label:"Приказ о создании информационного канала Учреждения в национальном мессенджере МАХ",url:official("/sites/default/files/page/20251127220642.pdf"),format:"PDF"},
  ],
};
const accessibility: MuseumOfficialDocumentGroup = {
  title: "Документы и сведения о доступности",
  source: pages.accessible,
  items: [
    {label:"Политика обеспечения условий доступности музея",url:pages.accessible,format:"Официальная страница"},
    {label:"Информация для маломобильных посетителей",url:pages.accessVisitors,format:"Официальная страница"},
  ],
};
const activity: MuseumOfficialDocumentGroup = {
  title: "Финансовая и организационная информация",
  source: pages.foundation,
  items: [
    {label:"Финансово-хозяйственная деятельность",url:pages.finance,format:"Официальная страница"},
    {label:"Противодействие коррупции",url:pages.anticorruption,format:"Официальная страница"},
  ],
};

/** The list is curated from the SOURCE museum pages, never from legal inferences. */
export const officialMuseumDocumentGroups: readonly MuseumOfficialDocumentGroup[] = [
  founding,privacy,visiting,accessibility,activity,
];

export const officialMuseumGroupsForPage = (slug:string): readonly MuseumOfficialDocumentGroup[] => {
  switch(slug){
    case "museum-documents": return officialMuseumDocumentGroups;
    case "museum-privacy": return [privacy];
    case "ticket-refunds":
    case "tickets-and-benefits": return [visiting];
    case "museum-accessibility-policy":
    case "accessible-museum": return [accessibility];
    case "museum-finance":
    case "museum-anti-corruption": return [activity];
    default: return [];
  }
};
