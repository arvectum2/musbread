import assert from 'node:assert/strict';
import {test} from 'node:test';
import {museumInquiryEmailDraft} from './visitor-inquiry-email.ts';
const DEST='musbread@cult.gugov.spb.ru';
test('TZ-080/203: feedback addresses only exact existing official museum mailbox, sanitises and preserves visitor questions in OS mail draft',()=>{
 const href=museumInquiryEmailDraft('feedback',{name:'  Тестовый Посетитель  ',message:'  Вопрос о доступности музея  '});
 assert.equal(href.startsWith('mailto:'+DEST+'?'),true);
 const uri=new URL(href);
 assert.match(uri.searchParams.get('subject')||'',/Обратная связь/);
 assert.match(uri.searchParams.get('body')||'',/Имя: Тестовый Посетитель/);
 assert.match(uri.searchParams.get('body')||'',/Вопрос о доступности музея/);
 assert.ok(!href.includes('https://'));
 assert.ok(!href.includes('payment'));
});
test('TZ-081/204: excursion draft requires valid date and group, does not claim reservation confirmation',()=>{
 const href=museumInquiryEmailDraft('excursion',{name:'Семья',message:'Нужна экскурсия',preferredDate:'2026-11-04',groupSize:6});
 const body=new URL(href).searchParams.get('body')!;
 assert.match(body,/Количество посетителей: 6/);
 assert.match(body,/Предпочтительная дата: 2026-11-04/);
 assert.match(body,/не является подтверждением записи/);
 for(const groupSize of [0,101,1.5,NaN]){
  assert.throws(()=>museumInquiryEmailDraft('excursion',{name:'Тест',message:'Запись',preferredDate:'2026-11-04',groupSize}));
 }
 for(const date of ['2026-13-33','2026-02-31','tomorrow','']){
  assert.throws(()=>museumInquiryEmailDraft('excursion',{name:'Тест',message:'Запись',preferredDate:date,groupSize:1}));
 }
});
test('No arbitrary mailbox or unsafe visitors can become a recipient; required fields remain required',()=>{
 assert.throws(()=>museumInquiryEmailDraft('feedback',{name:' ',message:'hello'}));
 assert.throws(()=>museumInquiryEmailDraft('feedback',{name:'Test',message:''}));
 const data=museumInquiryEmailDraft('feedback',{name:'Иван\r\nBcc: stolen@example.com',message:'Здравствуй'});
 assert.equal(data.split('?')[0],'mailto:'+DEST);
 assert.ok(!data.includes('&bcc='));
});
