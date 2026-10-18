#!/usr/bin/env python3
"""Capture 7 real museum seminars from official index and each detail via Mac mini.

Only true museum-authored headlines, seminar dates (from heading), HTML body
text and original VK video iframe references. No copyrighted video rehosting.
"""
import json,re,hashlib
from pathlib import Path
from time import sleep
from urllib.request import urlopen,Request
from urllib.parse import urlsplit,parse_qs,urlencode,urlunsplit
from datetime import datetime,timezone
from lxml import html
SITE='https://muzei-xleb.ru'
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'apps/web/src/data/official-museum-seminars.json'
MONTHS={'января':'01','февраля':'02','марта':'03','апреля':'04','мая':'05','июня':'06','июля':'07','августа':'08','сентября':'09','октября':'10','ноября':'11','декабря':'12'}
HEADERS={'User-Agent':'Mozilla/5.0 (MuseumBread original scientific source)','Accept':'text/html'}
def fetch(path):
    with urlopen(Request(SITE+path,headers=HEADERS),timeout=35) as resp:
        if resp.status!=200 or 'text/html' not in resp.headers.get('Content-Type',''):
            raise ValueError('Seminar source did not return HTTP200 HTML '+path)
        return resp.read(1800000).decode('utf-8','replace'),resp.url
def to_date(text):
    # Last stated seminar calendar date in the museum's heading; ranges separately.
    found=re.findall(r'(\d{1,2})(?:\s*[-–]\s*(\d{1,2}))?\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(20\d{2})\s*г\.?',text,re.I)
    if len(found)!=1:raise ValueError('Seminar heading does not have exactly one date '+text)
    day,end,month,year=found[0]
    value=f'{year}-{MONTHS[month.lower()]}-{int(day):02d}'
    return value, bool(end), (f'{year}-{MONTHS[month.lower()]}-{int(end):02d}' if end else None)
def get_video(src):
    if src.startswith('//'):src='https:'+src
    url=urlsplit(src)
    if url.scheme!='https' or url.hostname not in ('vk.com','vkvideo.ru') or url.path!='/video_ext.php':
        raise ValueError('Unsupported documentary science video '+src)
    params=parse_qs(url.query)
    if not {'oid','id'}<=params.keys() or set(params)-{'oid','id','hd','hash','autoplay'}:
        raise ValueError('Invalid external VK video query')
    if not re.fullmatch(r'-?\d{1,14}',params['oid'][0]) or not re.fullmatch(r'\d{5,16}',params['id'][0]):
        raise ValueError('Broken VK identity')
    normalized=[piece for piece in url.query.split('&') if not piece.startswith('autoplay=')]
    return {'original_iframe_src':src,'embed_url':urlunsplit(('https',url.hostname,url.path,'&'.join(normalized),'')),
      'owner_id':params['oid'][0],'is_museum_vk_channel':params['oid'][0]=='-37126776'}
def main():
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    original,url=fetch('/seminary')
    if url!=SITE+'/seminary':raise ValueError('Unexpected museum seminar index route')
    index=html.fromstring(original)
    container=index.xpath('//article[contains(@class,"node-page")]')
    if len(container)!=1:raise ValueError('Museum seminars original index changed')
    rows=[]
    for h in container[0].xpath('.//h2'):
        a=h.xpath('.//a[@href]')
        if len(a)!=1:raise ValueError('Original seminary index heading has no unique detail link')
        title=' '.join(a[0].text_content().split())
        path=a[0].get('href')
        if not re.fullmatch(r'/node/\d{2,4}',path or ''):
            raise ValueError('External or unknown original scientific item: '+str(path))
        date,range_day,end=to_date(title)
        rows.append((title,path,date,range_day,end))
    if len(rows)!=7 or len({x[1] for x in rows})!=7:raise ValueError('Expected 7 exact museum seminars')
    records=[]
    for i,(title,path,meeting_date,range_day,end) in enumerate(rows):
        sleep(10)
        raw,final_url=fetch(path)
        page=html.fromstring(raw)
        detail_title=' '.join(page.xpath('string(//h1)').split())
        if detail_title!=title or not final_url.startswith(SITE+'/'):
            raise ValueError('Seminar index/detail H1 mismatch '+path)
        body=page.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," field-name-body ")]')
        if len(body)!=1:raise ValueError('Original seminar main content not found '+path)
        embeds=[get_video(frame.get('src') or '') for frame in body[0].xpath('.//iframe[@src]')]
        # Original titles for video parts, only text names found in official source.
        for frame,video in zip(body[0].xpath('.//iframe[@src]'),embeds):
            prev=frame.getparent().getprevious()
            while prev is not None and prev.tag not in ('h2','h3','p'):
                prev=prev.getprevious()
            label=' '.join(prev.text_content().split()) if prev is not None else ''
            video['part_label']=label if 1<=len(label)<=90 else ''
        source_text=' '.join(body[0].text_content().split())
        record={
          'id':'science-seminar-'+meeting_date+'-'+path.rsplit('/',1)[-1],
          'title':detail_title,'date_start':meeting_date,'date_end':end,
          'dated_range':range_day,'index_source_url':SITE+'/seminary',
          'index_detail_path':path,'source_url':final_url,
          'page_html_sha256':hashlib.sha256(raw.encode()).hexdigest(),
          'original_body_text':source_text,
          'video_count':len(embeds),'videos':embeds,
          'media_rehosted':False,'photo_rights_confirmed':False,
        }
        records.append(record)
        print('VERIFIED',i+1,'/7',title[:75],meeting_date,'VK embeds',len(embeds),flush=True)
    seen=set()
    for r in records:
        if r['id'] in seen:raise ValueError('Duplicate seminar ID')
        seen.add(r['id'])
    result={
       'source':SITE,'index_url':SITE+'/seminary','index_html_sha256':hashlib.sha256(original.encode()).hexdigest(),
       'snapshot_utc':stamp,'count':len(records),
       'video_count':sum(x['video_count'] for x in records),
       'seminars':records,
       'editorial_policy':'Only genuine original dated seminars. Videos load after click; original publisher captions/rights may need confirmation. Future science events not guessed.'
    }
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(OUT)
    print('SAVED',len(records),'seminars and',result['video_count'],'true original VK recordings')
if __name__=='__main__':main()
