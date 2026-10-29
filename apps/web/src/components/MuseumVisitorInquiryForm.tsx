'use client';
import {useState,useRef,useSyncExternalStore,type FormEvent} from 'react';
import MuseumAnchor from '@/components/MuseumAnchor';
import Link from '@/components/MuseumLink';
import {museumReference} from '@/data/museum-reference';
import {museumInquiryEmailDraft,type MuseumInquiryKind} from '@/data/visitor-inquiry-email';

const subscribe=()=>()=>{};
const isClient=()=>true;
const isServer=()=>false;
// The build must explicitly opt in AFTER the museum approves its privacy terms.
// No secrets, CMS URLs, or database connections are part of this static client.
const endpoint=process.env.NEXT_PUBLIC_MUSEUM_REQUESTS_ENDPOINT ?? '';
const consentVersion=process.env.NEXT_PUBLIC_MUSEUM_REQUESTS_CONSENT_VERSION ?? '';
const validEndpoint=(()=>{
 try{
  const url=new URL(endpoint);
  return url.protocol==='https:' && url.username==='' && url.password===''
   && url.hostname!=='localhost' && !url.hostname.endsWith('.local')
   && url.pathname==='/v1/requests' && url.search==='' && url.hash==='';
 }catch{return false;}
})();
const enabled=process.env.NEXT_PUBLIC_MUSEUM_REQUESTS_ENABLED==='1'
    && validEndpoint && consentVersion.length>0;

export default function MuseumVisitorInquiryForm({kind}:{kind:MuseumInquiryKind}){
 const hydrated=useSyncExternalStore(subscribe,isClient,isServer);
 const requestId=useRef('');
 const [name,setName]=useState('');
 const [email,setEmail]=useState('');
 const [message,setMessage]=useState('');
 const [date,setDate]=useState('');
 const [groupSize,setGroupSize]=useState('1');
 const [consent,setConsent]=useState(false);
 const [website,setWebsite]=useState('');
 const [draft,setDraft]=useState<string|null>(null);
 const [receipt,setReceipt]=useState('');
 const [pending,setPending]=useState(false);
 const [error,setError]=useState('');
 const clear=()=>{requestId.current='';setDraft(null);setReceipt('');setError('');};
 const excursion=kind==='excursion';
 const submit=async(event:FormEvent<HTMLFormElement>)=>{
  event.preventDefault();
  if(pending)return;
  setDraft(null);setReceipt('');setError('');
  if(!enabled){
   try{
    setDraft(museumInquiryEmailDraft(kind,{name,message,...(excursion?{
     preferredDate:date,groupSize:Number(groupSize)}:{})}));
   }catch(ex){setError(ex instanceof Error?ex.message:'Проверьте данные');}
   return;
  }
  if(!consent){setError('Необходимо согласие на обработку данных');return;}
  setPending(true);
  if(!requestId.current){
   requestId.current=Array.from(crypto.getRandomValues(new Uint8Array(16)),
    n=>n.toString(16).padStart(2,'0')).join('');
  }
  try{
   const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},
    cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer',
    body:JSON.stringify({kind,name,email,message,consent:consentVersion,website,client_id:requestId.current,
     ...(excursion?{date,group_size:Number(groupSize)}:{})})});
   if(response.status!==202)throw new Error('Сервис не подтвердил получение обращения.');
   const data:unknown=await response.json();
   if(typeof data!=='object'||data===null||!('request_id' in data)
      ||typeof data.request_id!=='string'||!/^[a-f0-9]{32}$/.test(data.request_id)){
      throw new Error('Не удалось получить подтверждение отправки.');
   }
   setReceipt(data.request_id);
   setMessage('');
  }catch{
   setError('Не удалось подтвердить доставку. Попробуйте позднее или напишите в музей по электронной почте. Если сообщение уже отправлялось, уточните получение перед повтором.');
  }finally{setPending(false);}
 };
 return <section aria-label={excursion?'Запрос на экскурсию':'Форма обратной связи'}>
   <h2>{excursion?'Запросить экскурсию':'Написать в музей'}</h2>
   <p>{enabled?'Обращение поступает в защищённую очередь музея. Отправка не означает подтверждения экскурсии.':
      'Временный способ связи — письмо на официальный адрес музея. На сайте данные не сохраняются и в закрытую CMS не передаются. Для отправки нужна настроенная почтовая программа.'}</p>
   <noscript><p>Для связи используйте официальный адрес электронной почты музея.</p></noscript>
   <form onSubmit={submit} method="post" className="museum-visitor-inquiry-form">
    <fieldset disabled={!hydrated||pending} aria-label="Данные обращения">
     <p><label htmlFor={"inquiry-"+kind+"-name"}>Ваше имя</label>{' '}
      <input id={"inquiry-"+kind+"-name"} name="visitor-name" autoComplete="name"
       value={name} onChange={e=>{setName(e.target.value);clear();}} required maxLength={100}/></p>
     {enabled&&<p><label htmlFor={"inquiry-"+kind+"-email"}>Электронная почта для ответа</label>{' '}
      <input id={"inquiry-"+kind+"-email"} type="email" name="email" autoComplete="email"
       value={email} onChange={e=>{setEmail(e.target.value);clear();}} required maxLength={254}/></p>}
     {excursion&&<>
      <p><label htmlFor="inquiry-excursion-date">Предпочтительная дата экскурсии</label>{' '}
       <input id="inquiry-excursion-date" name="preferred-date" type="date"
        value={date} onChange={e=>{setDate(e.target.value);clear();}} required/></p>
      <p><label htmlFor="inquiry-excursion-group">Количество посетителей</label>{' '}
       <input id="inquiry-excursion-group" name="group-size" type="number" min={1} max={100} step={1}
        value={groupSize} onChange={e=>{setGroupSize(e.target.value);clear();}} required/></p>
     </>}
     <p><label htmlFor={"inquiry-"+kind+"-message"}>{excursion?'Дополнительная информация':'Ваш вопрос'}</label>{' '}
      <textarea id={"inquiry-"+kind+"-message"} name="message" rows={5} maxLength={1200}
       value={message} onChange={e=>{setMessage(e.target.value);clear();}} required/></p>
     {enabled&&<>
      <div style={{position:'absolute',left:'-9999px'}} aria-hidden="true">
       <label htmlFor="museum-website">Сайт</label>
       <input id="museum-website" tabIndex={-1} autoComplete="off" name="website"
        value={website} onChange={e=>setWebsite(e.target.value)}/>
      </div>
      <p><label><input type="checkbox" checked={consent} required
        onChange={e=>setConsent(e.target.checked)}/> Согласен(на) на обработку данных
        для рассмотрения обращения согласно <Link href="/guide/museum-privacy/">политике музея</Link>.</label></p>
     </>}
     <button type="submit" disabled={pending}>{pending?'Отправляется…':enabled?'Отправить обращение':'Сформировать письмо'}</button>
    </fieldset>
   </form>
   {error&&<p role="alert">{error}</p>}
   <div role="status" aria-live="polite">
    {receipt&&<p>Обращение получено для обработки. Номер: {receipt}. Это не подтверждение записи на экскурсию.</p>}
    {draft&&<p>Черновик готов. <MuseumAnchor href={draft} className="text-link">
     Открыть письмо в почтовой программе ↗</MuseumAnchor>. Проверьте письмо и отправьте его самостоятельно.
     {excursion?' Дата и время экскурсии ещё не подтверждены музеем.':''}</p>}
   </div>
   <p>Можно также написать напрямую: <MuseumAnchor href={museumReference.emailHref}>
    {museumReference.email}</MuseumAnchor> или позвонить <MuseumAnchor href={museumReference.phoneHref}>
    {museumReference.phone}</MuseumAnchor>.</p>
   <p>Официальный документ: <Link href="/guide/museum-privacy/">Политика обработки персональных данных музея</Link>.</p>
 </section>;

}
