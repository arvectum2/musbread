/**
 * TZ-080/081/203/204 — interim official-email path, not a payment API, a
 * ticket reservation, a server form or an acceptance of personal data by us.
 * Only explicitly user-initiated OS mail-client draft. Never GET to the site,
 * never store names, messages, contacts, IPs or consent in our CMS.
 */
import {museumReference} from './museum-reference.ts';
export type MuseumInquiryKind='feedback'|'excursion';
export interface MuseumInquiryInput {
  name:string;
  message:string;
  preferredDate?:string;
  groupSize?:number;
}
function cleaned(value:string, maxLength:number):string {
 return value.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g,'')
  .replace(/\r\n?/g,'\n').trim().slice(0,maxLength);
}
export function museumInquiryEmailDraft(kind:MuseumInquiryKind,input:MuseumInquiryInput):string {
 const name=cleaned(input.name,100);
 const message=cleaned(input.message,1200);
 if(!name || !message)throw new Error('Имя и текст обращения обязательны');
 const subject=kind==='feedback'?'Обратная связь — сайт Музея Хлеба':'Заявка на экскурсию — сайт Музея Хлеба';
 const body=[`Имя: ${name}`];
 if(kind==='excursion'){
  const date=input.preferredDate||'';
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(date+'T00:00:00Z'))
      || new Date(date+'T00:00:00Z').toISOString().slice(0,10)!==date){
   throw new Error('Нужно указать корректную дату экскурсии');
  }
  if(!Number.isInteger(input.groupSize)||input.groupSize!<1||input.groupSize!>100){
   throw new Error('Размер группы: от 1 до 100');
  }
  body.push(`Предпочтительная дата: ${date}`,`Количество посетителей: ${input.groupSize}`);
 }
 body.push('',`Сообщение:\n${message}`,'',
  'Пожалуйста, подтвердите получение обращения. Отправка письма не является подтверждением записи на экскурсию.');
 // Source address hard-coded in existing official museum reference; never a
 // visitor-controlled recipient, header or third-party mail collector.
 return museumReference.emailHref+'?subject='+encodeURIComponent(subject)
  +'&body='+encodeURIComponent(body.join('\n'));
}
