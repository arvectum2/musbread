#!/usr/bin/env python3
"""Extract literal dated/timed event instances from museum weekly news.
Never infer event date from article publication date. Pinned original HTML,
calendar days and hours, strictly fail closed for unknown rows.
"""
from __future__ import annotations
from datetime import date,timedelta,datetime,timezone
from hashlib import sha256
from pathlib import Path
from lxml import html as lx
import json,re,unicodedata

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'apps/web/src/data/official-museum-news.json'
OUT=ROOT/'apps/web/src/data/official-agenda-sessions.json'
MONTHS={'сентября':9,'октября':10}
WEEKLY_SOURCE_DIGESTS={
  '2026-10-12':'280af595ad43d8ffe8d5d6d86a4ef5e64de84258c3875dc7421a506972d8991a',
  '2026-10-05':'38b2b74ca95977cf94faaf933ec72dfd25ff1c07eae1a70546ef4cdeb116037d',
  '2026-09-28':'fb802f1b385963f44851c85c883b4ce5b3e4d506000f910b0a59264825b7e805',
  '2026-09-21':'cd6ea2c5bffdd5d2d6f8206d1ce9e60d09abda5436568fc2173c5bce758fa777',
  '2026-09-14':'6e72e8da7b7f998aaa8b90c57decabe8392617bc334fdaf02c59e1be798df604',
  '2026-09-07':'d73bd62e39f5f1306d12dc9deda6b97877e492b7e16ad1d36f8ebd180f2f9a35',
}
# An exact, literal genre classification. No guess from minimum-age marker.
def category(label):
    lead=label.casefold()
    if 'экскурси' in lead.split('«',1)[0] or 'экскурси' in lead.split('“',1)[0]:
        return 'Экскурсия'
    if lead.startswith('мастер-класс') or lead.startswith('творческая мастерская'):
        return 'Мастер-класс'
    if lead.startswith('литературная гостиная'):
        return 'Литературная гостиная'
    if lead.startswith('интерактивное занятие') or lead.startswith('интерактивная программа'):
        return 'Интерактивное занятие'
    if lead.startswith('тематическая программа'):
        return 'Тематическая программа'
    raise RuntimeError('No verified genre classification: '+label)
def norm(label):
    text=unicodedata.normalize('NFKC',label)
    text=re.sub(r'[«»“”"]','',text)
    return re.sub(r'\s+',' ',text).strip().casefold()
def main():
    source=json.loads(SOURCE.read_text())
    if source['source']!='https://muzei-xleb.ru' or source['count']!=10:
        raise RuntimeError('Museum news source index changed')
    pages=[p for p in source['articles'] if p['published_on'] in WEEKLY_SOURCE_DIGESTS and p['title'].startswith('События в музее с ')]
    if len(pages)!=6:raise RuntimeError('Six source weekly programmes required')
    found={}
    raw_count=0
    for page in pages:
        published=page['published_on']
        expected=WEEKLY_SOURCE_DIGESTS[published]
        if page['html_sha256']!=expected or sha256(page['html'].encode()).hexdigest()!=expected:
            raise RuntimeError('Weekly source text not pinned: '+published)
        if not page['title'].startswith('События в музее с '):
            raise RuntimeError('Not a museum weekly events announcement')
        dom=lx.fromstring('<section>'+page['html']+'</section>')
        day=None
        in_program=False
        entries_in_page=0
        for el in dom.xpath('.//p|.//li'):
            label=' '.join(el.text_content().split())
            if el.tag=='p':
                if label=='ЭКСКУРСИИ. МАСТЕР-КЛАССЫ':
                    in_program=True
                    continue
                if label=='ВЫСТАВКИ':
                    in_program=False
                    continue
                match=re.fullmatch(r'(\d{1,2}) (сентября|октября)',label)
                if match and in_program:
                    day=date(2026,MONTHS[match[2]],int(match[1]))
                    pub=date.fromisoformat(published)
                    if not pub<=day<=pub+timedelta(days=8):
                        raise RuntimeError('Day not within original 8-day published museum bulletin: '+str(day))
                continue
            if el.tag=='li' and in_program:
                match=re.fullmatch(r'(\d\d):(\d\d)\s+(.+?)\s+\((\d{1,2})\+\)',label)
                if not match or day is None:raise RuntimeError('Unparseable timed museum programme row '+repr(label))
                hours,mins=int(match[1]),int(match[2])
                if not (8<=hours<=22 and 0<=mins<=59):
                    raise RuntimeError('Unexpected museum event hour')
                title=match[3].strip()
                age=int(match[4])
                if not (4<=age<=18) or '«' not in title and '“' not in title:
                    raise RuntimeError('Museum row has unexpected age or missing original named programme')
                event_category=category(title)
                normalized=norm(title)
                time=f'{hours:02}:{mins:02}'
                uid=f'{day.isoformat()}|{time}|{normalized}'
                original={
                    'date':day.isoformat(),'time':time,'title':title,'age_min':age,
                    'category':event_category,
                    'slug':f'museum-session-{day.isoformat()}-{hours:02}{mins:02}-{sha256(normalized.encode()).hexdigest()[:12]}',
                    'source_urls':[page['source_url']],
                    'source_html_sha256':[page['html_sha256']],
                    'original_row':label,
                    'source_rows':[label],
                }
                if uid in found:
                    prev=found[uid]
                    if prev['age_min']!=age or prev['category']!=event_category:
                        raise RuntimeError('Contradictory overlapping weekly museum row: '+uid)
                    prev['source_urls'].append(page['source_url'])
                    prev['source_html_sha256'].append(page['html_sha256'])
                    prev['source_rows'].append(label)
                else:found[uid]=original
                raw_count+=1
                entries_in_page+=1
        if not (10<=entries_in_page<=45):
            raise RuntimeError('Missing most of week programme '+published+': '+str(entries_in_page))
        print('VERIFIED WEEK',published,entries_in_page,'timed rows',flush=True)
    rows=sorted(found.values(),key=lambda x:(x['date'],x['time'],x['title']))
    if len({x['slug'] for x in rows})!=len(rows):raise RuntimeError('Colliding session slug IDs')
    if len(rows)<90:raise RuntimeError('Too few museum schedule entries')
    result={
        'source':'https://muzei-xleb.ru','created_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'original_bulletin_count':6,'raw_rows':raw_count,'unique_sessions':len(rows),
        'category_counts':{k:sum(x['category']==k for x in rows)
            for k in sorted({x['category'] for x in rows})},
        'sessions':rows,
        'evidence_policy':'Individual day, time, name and age must be explicit in official source. Only session start time is known, no invented end time, prices, bookings or image rights.'
    }
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(OUT)
    print('SOURCE SESSIONS',len(rows),'RAW',raw_count,'BY GENRE',result['category_counts'])
if __name__=='__main__':main()
