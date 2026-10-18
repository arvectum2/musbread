#!/usr/bin/env python3
"""Only official-current museum facts in public FAQ; new questions are authored.

Never turns other museums' house rules into the Bread Museum's legal rules.
Source phrases and HTML SHA256 are checked before emitting new FAQ baseline.
"""
from __future__ import annotations
import html as html_escape
import json
from hashlib import sha256
from pathlib import Path
from lxml import html as lx

ROOT=Path(__file__).resolve().parents[1]
OFFICIAL=ROOT/'apps/web/src/data/official-page-snapshots.json'
GUIDANCE=ROOT/'apps/web/src/data/official-visitor-guidance.json'
OUTPUT=ROOT/'apps/web/src/data/official-visitor-faq.json'
FAQ=[
 ('hours','Когда открыт музей?',
  'Музей работает со среды по понедельник с 10:00 до 18:00. Касса и вход открыты до 17:00. Вторник — выходной; санитарный день — последний четверг месяца.',
  '/chasy-raboty',['с 10.00 до 18.00','до 17.00','последний четверг месяца']),
 ('address','Где находится музей?',
  'Санкт-Петербург, улица Михайлова, дом 2. Ближайшее метро — «Площадь Ленина», выход к Финляндскому вокзалу.',
  '/kontakty',['Михайлова, д.2','Площадь Ленина','Финляндский вокзал']),
 ('tickets','Где посмотреть цены на билеты и льготы?',
  'Стоимость входного билета для взрослых в прейскуранте с 1 сентября 2026 года — 400 рублей. Остальные тарифы и льготные категории приведены на официальной странице цен музея.',
  '/stoimost',['01.09.2026','400 рублей/чел.','Входной билет для льготных категорий']),
 ('excursion','Нужно ли заранее записываться на экскурсию?',
  'Да. Музей указывает, что занятия и экскурсии проводятся только по предварительной записи; телефон записи: (812) 294-50-82.',
  '/ekskursii',['только по предварительной записи','294-50-82']),
 ('group','Сколько человек может быть в экскурсионной группе?',
  'Согласно музейной странице экскурсий, одна детская группа — не более 20 детей и двух сопровождающих взрослых; одновременно музей принимает не более 40 человек (две группы). Условия относятся к экскурсионным группам.',
  '/ekskursii',['не более 40 человек','не более 20 детей плюс 2 сопровождающих взрослых']),
 ('photo','Можно ли фотографировать экспозицию?',
  'На странице экскурсий музея указано, что любительская фото- и видеосъёмка бесплатна и разрешена только без вспышки.',
  '/ekskursii',['Любительская фото- и видеосъемка - бесплатные','только без вспышки']),
 ('accessible','Есть ли условия для маломобильных посетителей?',
  'На действующем сайте музей сообщает о пандусах, подъёмнике и оборудованном туалете на первом этаже. Музей просит связаться с сотрудниками до визита для уточнения условий.',
  '/informaciya-dlya-mgn',['пандусами и подъемником','Специально оборудованный туалет','Просим Вас позвонить нам заранее']),
 ('pushkin','Как приобрести билет по «Пушкинской карте»?',
  'На странице музея указано, что билеты по «Пушкинской карте» продаются только онлайн. Билет именной и не может передаваться другому человеку.',
  '/pushkinskaya-karta',['можно купить только онлайн','является именным']),
 ('refund','Где найти порядок возврата билетов?',
  'Официальные документы о приобретении и возврате билетов и заявление к ним размещены на странице музея «Цены и условия предоставления услуг».',
  '/ceny-i-usloviya-predostavleniya-uslug',['Положение о порядке приобретения и возврата','Приложение № 1']),
]

def main():
    primary=json.loads(OFFICIAL.read_text())
    addition=json.loads(GUIDANCE.read_text())
    assert primary['source']==addition['source']=='https://muzei-xleb.ru'
    sources={x['path']:x for x in primary['pages']+addition['pages']}
    out=[]
    for slug,q,a,path,phrases in FAQ:
        source=sources[path]
        content=' '.join(lx.fromstring('<div>'+source['html']+'</div>').text_content().split())
        if sha256(source['html'].encode()).hexdigest()!=source['html_sha256']:
            raise RuntimeError('Source snapshot HTML changed '+path)
        for phrase in phrases:
            if ' '.join(phrase.split()) not in content:
                raise RuntimeError('Missing official fact: '+path+' '+phrase)
        out.append({'id':slug,'question':q,'answer':a,
                    'source_path':path,'source_url':source['source_url'],
                    'source_html_sha256':source['html_sha256'],
                    'source_phrases':phrases})
    result={'source':'https://muzei-xleb.ru','scope':'Editor-prepared questions on already published museum facts, not formal visiting regulations',
            'snapshot_utc':max(primary['snapshot_utc'],addition['snapshot_utc']),
            'count':len(out),'questions':out}
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('VERIFIED',len(out),'FAQ answers from',len({e['source_path'] for e in out}),'real museum source pages')
if __name__=='__main__':main()
