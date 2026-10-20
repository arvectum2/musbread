'use client';
import {useState,useSyncExternalStore, type FormEvent} from 'react';
import MuseumAnchor from '@/components/MuseumAnchor';
import Link from '@/components/MuseumLink';
import {museumReference} from '@/data/museum-reference';
import {museumInquiryEmailDraft,type MuseumInquiryKind} from '@/data/visitor-inquiry-email';

/** Unlike an effect-triggered state update, this hydration indicator is
 * guaranteed FALSE on the static/server snapshot (including JS-disabled
 * visitors), and TRUE only after React hydrates in the browser. It never
 * causes a POST of visitor data to a static or CMS endpoint.
 */
const subscribeHydration=()=>()=>{};
const getClientHydration=()=>true;
const getServerHydration=()=>false;

/** Does not POST PII to Next static output or the restricted CMS. */
export default function MuseumVisitorInquiryForm({kind}:{kind:MuseumInquiryKind}) {
 const hydrated=useSyncExternalStore(subscribeHydration,getClientHydration,getServerHydration);
 const [name,setName]=useState('');
 const [message,setMessage]=useState('');
 const [date,setDate]=useState('');
 const [groupSize,setGroupSize]=useState('1');
 const [draft,setDraft]=useState<string|null>(null);
 const [error,setError]=useState('');
 const clear=()=>{setDraft(null);setError('');};
 const submit=(event:FormEvent<HTMLFormElement>)=>{
  event.preventDefault();
  try {
   const href=museumInquiryEmailDraft(kind,{name,message,
     ...(kind==='excursion'?{preferredDate:date,groupSize:Number(groupSize)}:{})});
   setDraft(href);setError('');
  } catch(ex) {setDraft(null);setError(ex instanceof Error?ex.message:'Проверьте данные');}
 };
 const excursion=kind==='excursion';
 return <section aria-label={excursion?'Запрос на экскурсию':'Форма обратной связи'}>
   <h2>{excursion?'Запросить экскурсию':'Написать в музей'}</h2>
   <p>Временный способ связи — письмо на официальный адрес музея. На сайте данные не сохраняются и
    в закрытую CMS не передаются. Для отправки нужна настроенная почтовая программа.</p>
   <noscript><p>Для составления письма используйте электронную почту музея, указанную ниже.</p></noscript>
   <form onSubmit={submit} method="post" className="museum-visitor-inquiry-form">
    <fieldset disabled={!hydrated} aria-label="Данные обращения">
     <p><label htmlFor={`inquiry-${kind}-name`}>Ваше имя</label>{' '}
       <input id={`inquiry-${kind}-name`} autoComplete="name" name="visitor-name"
         value={name} onChange={event=>{setName(event.target.value);clear();}}
         required maxLength={100}/></p>
     {excursion && <>
       <p><label htmlFor="inquiry-excursion-date">Предпочтительная дата экскурсии</label>{' '}
         <input id="inquiry-excursion-date" type="date" name="preferred-date"
           value={date} onChange={event=>{setDate(event.target.value);clear();}}
           required/></p>
       <p><label htmlFor="inquiry-excursion-group">Количество посетителей</label>{' '}
         <input id="inquiry-excursion-group" type="number" min={1} max={100} step={1}
           name="group-size" value={groupSize} onChange={event=>{setGroupSize(event.target.value);clear();}} required/></p>
     </>}
     <p><label htmlFor={`inquiry-${kind}-message`}>{excursion?'Дополнительная информация':'Ваш вопрос'}</label>{' '}
       <textarea id={`inquiry-${kind}-message`} name="message" rows={5} maxLength={1200}
         value={message} onChange={event=>{setMessage(event.target.value);clear();}}
         required/></p>
     <button type="submit">Сформировать письмо</button>
    </fieldset>
   </form>
   {error && <p role="alert">{error}</p>}
   <div role="status" aria-live="polite">
     {draft && <p>Черновик готов. <MuseumAnchor href={draft} className="text-link">
       Открыть письмо в почтовой программе ↗</MuseumAnchor>. Проверьте письмо и отправьте его самостоятельно.
       {excursion?' Дата и время экскурсии ещё не подтверждены музеем.':''}</p>}
   </div>
   <p>Можно также обратиться напрямую: <MuseumAnchor href={museumReference.emailHref}>
     {museumReference.email}</MuseumAnchor> или позвонить по номеру <MuseumAnchor href={museumReference.phoneHref}>
     {museumReference.phone}</MuseumAnchor>.</p>
   <p>Официальный документ: <Link href="/guide/museum-privacy/">Политика обработки персональных данных музея</Link>.</p>
 </section>;
}
