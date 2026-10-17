import {content} from "./content";
import {museumReference} from "./museum-reference";

/** Only a COMPLETE approved MoonShine visitor-contact card overrides the
 * official-site reference snapshot; no fake data and no CMS calls from UI. */
const approved=content.visitor_contacts;
export const visitorContacts={
  address:approved?.address ?? museumReference.address,
  metro:approved?.metro ?? museumReference.metro,
  phone:approved?.phone ?? museumReference.phone,
  phoneHref:approved?.phone_href ?? museumReference.phoneHref,
  email:approved?.email ?? museumReference.email,
  emailHref:"mailto:"+(approved?.email ?? museumReference.email),
  openingHours:approved?.opening_hours ?? museumReference.openingHours,
  admissionHours:approved?.admission_hours ?? museumReference.admissionHours,
  closedDay:approved?.closed_day ?? museumReference.closedDay,
  sanitaryDay:approved?.sanitary_day ?? museumReference.sanitaryDay,
} as const;
export const visitorAddressMapSearchUrl=
  "https://yandex.ru/maps/?text="+encodeURIComponent(visitorContacts.address);
