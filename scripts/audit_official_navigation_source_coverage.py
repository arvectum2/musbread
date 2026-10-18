#!/usr/bin/env python3
"""Single direct original homepage read; classify real menu coverage."""
from urllib.request import Request,urlopen
from urllib.parse import urljoin,urlparse
from lxml import html as lx
from pathlib import Path
from collections import Counter
import json,csv
ROOT=Path(__file__).resolve().parents[1]
BASE='https://muzei-xleb.ru'
OUT=ROOT/'docs/source-migration/ORIGINAL_MENU_COVERAGE_20261018.csv'
MD=ROOT/'docs/source-migration/ORIGINAL_MENU_COVERAGE_20261018.md'

def main():
    with urlopen(Request(BASE+'/',headers={'User-Agent':'Mozilla/5.0 (MusBread main menu official audit)'}),timeout=30) as r:
        if r.status!=200:raise RuntimeError('Original source unavailable')
        dom=lx.fromstring(r.read(2_000_000))
    menus=dom.xpath('//nav//ul[contains(concat(" ",normalize-space(@class)," ")," menu ")]')
    if not menus:raise RuntimeError('No original Drupal menu')
    rows=[];seen=set()
    for a in menus[0].xpath('.//a[@href]'):
        url=urljoin(BASE+'/',a.get('href'))
        u=urlparse(url)
        if u.hostname not in ('muzei-xleb.ru','www.muzei-xleb.ru') or u.path in seen:continue
        seen.add(u.path)
        rows.append({'path':u.path,'label':' '.join(a.text_content().split())[:180],
                     'original_url':BASE+u.path})
    source=json.loads((ROOT/'apps/web/src/data/official-page-snapshots.json').read_text())
    gaps=json.loads((ROOT/'apps/web/src/data/official-museum-menu-gaps.json').read_text())
    captured={x['path'] for x in source['pages']}
    captured.update(x['path'] for x in gaps['pages'] if x['path'] not in ('/gostevaya-kniga','/covid-19'))
    for name in ('official-visitor-guidance.json','official-science-sources.json',
                 'official-excursion-pages.json','official-exhibition-indexes.json'):
        data=json.loads((ROOT/'apps/web/src/data'/name).read_text())
        for key in ('pages','indexes'):
            for x in data.get(key,[]):
                path=x.get('path') or urlparse(x.get('source_url','')).path
                if path:captured.add(path)
    categories={
        '/novosty','/vistavky','/vistavky/tekushchie-vystavki',
        '/vistavky/proshedshie-vystavki','/vistavky/virtualnye-vystavki',
        '/vistavky/vyezdnye-vystavki','/ekskursii','/obzornaya-ekskursiya',
        '/interaktivnye-zanyatiya','/tematicheskie-ekskursii',
        '/teatralizovannye-ekskursii','/master-klassy','/video',
        '/nauchno-organizacionnaya-deyatelnost','/nauchno-metodicheskiy-sovet',
        # These are original navigation/service indexes, represented by
        # working site routes rather than a duplicative Drupal article body.
        '/posetitelyam','/search/node','/dokumenty','/glavnaya',
    }
    exceptional={
        '/gostevaya-kniga':'Есть отзывы посетителей; не копировать частные сообщения',
        '/covid-19':'Исторические ограничения 2021 года не выдавать за действующие',
        '/informaciya-dlya-dariteley':'Нет содержательного официального текста статьи в Drupal',
        '/dokumenty':'Это индекс меню; внутренние документные разделы перенесены',
        '/glavnaya':'Дубликат входа на главную, которая имеется в прототипе',
    }
    for item in rows:
        p=item['path']
        if p in captured:state='Исходный текст перенесён';note=''
        elif p in categories:state='Исходный каталог перенесён';note=''
        else:state='Ссылка / отдельная проверка';note=exceptional.get(p,'Проверить реальный исходный раздел')
        item['status']=state;item['note']=note
    counts=Counter(r['status'] for r in rows)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter=';',lineterminator='\n')
        w.writeheader();w.writerows(rows)
    lines=[
      '# Сверка оригинального меню музея с контентной копией — 18.10.2026',
      '',
      'Источник: прямой GET главной страницы muzei-xleb.ru на Mac mini; все уникальные ссылки основного Drupal-меню.',
      '',
      'Оригинальных ссылок: **'+str(len(rows))+'**.',
      '',
      '- Исходный текст перенесён: '+str(counts['Исходный текст перенесён'])+'.',
      '- Исходные каталоги/разделы перенесены: '+str(counts['Исходный каталог перенесён'])+'.',
      '- Осталась только ссылка или требуется проверка: '+str(counts['Ссылка / отдельная проверка'])+'.',
      '',
      '### Непереносимые как новый действующий материал',
      '',
    ]
    for x in rows:
        if x['status']=='Ссылка / отдельная проверка':
            lines.append('- '+x['label']+' ('+x['path']+'): '+x['note'])
    lines+=['',
       '### Реальный перенос на этом этапе',
       '',
       'Созданы 3 приватных редактируемых материала: учётная политика, противодействие терроризму, антимонопольный комплаенс.',
       '11 исходных PDF получены без OCR. 6 разрешённых валидатором файлов добавлены в CMS, остальные оставлены прямыми оригинальными ссылками.',
       'Отдельная оригинальная инструкция как пройти от Финляндского вокзала перенесена в раздел планирования визита.',
       '',
       'Это аудит меню, а не утверждение о полном переносе архивов и фотогалерей.',
       'Следующая важная работа — перенос подлинных фотографий и галерей (медиатека CMS пока пуста).',
       '',
       'Подробная таблица: ORIGINAL_MENU_COVERAGE_20261018.csv.',
       'Светофор ТЗ остаётся 84 / 102 / 139.',
    ]
    MD.write_text('\n'.join(lines)+'\n')
    print('SOURCE MENU',len(rows),dict(counts))
    print('EXCEPTIONS',[(x['path'],x['note']) for x in rows if x['status']=='Ссылка / отдельная проверка'])
if __name__=='__main__':main()
