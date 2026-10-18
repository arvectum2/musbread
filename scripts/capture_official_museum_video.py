#!/usr/bin/env python3
"""Capture actual museum source video catalogues, titles, embeds and provenance.

No files, thumbnails, tracker scripts or rights assertions are copied.
Strict permitlist for already embedded VK players and one linked .mp4 file.
Respect robots.txt crawl-delay 10 sec, fail closed on surprising src.
"""
from __future__ import annotations
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,parse_qs,urlunsplit,urlencode
from urllib.request import Request,urlopen
from lxml import html as lx
from time import sleep

ROOT=Path(__file__).resolve().parents[1]
SITE='https://muzei-xleb.ru'
OUT=ROOT/'apps/web/src/data/official-museum-videos.json'
SECTIONS=[
 ('museum','О музее','/video/o-muzee'),
 ('exhibitions','Выставки','/video/vystavky'),
 ('unusual-tour','Проект «НЕобзорная экскурсия»','/video/proekt-neobzornaya-ekskursiya'),
]
SID='-37126776'
def fetch(path):
    with urlopen(Request(SITE+path,headers={'User-Agent':'Mozilla/5.0 (MusBread source video catalogue, museum original)',
                                             'Accept':'text/html'}),timeout=30) as r:
        if r.status!=200 or 'text/html' not in r.headers.get('Content-Type',''):
            raise ValueError('Not successful HTML '+path)
        return r.read(2500000).decode('utf-8','replace')
def parse_original(raw,kind,path):
    page=lx.fromstring(raw)
    heading=' '.join(page.xpath('string(//h1)').split())
    container=page.xpath('//article[contains(@class,"node-page")]')
    if len(container)!=1:raise ValueError('Museum video article container changed '+path)
    frames=container[0].xpath('.//iframe[@src]')
    if not 3<=len(frames)<=30:raise ValueError('Unexpected museum original iframe number '+path)
    items=[]
    for i,frame in enumerate(frames):
        src=frame.get('src','')
        if src.startswith('//'):src='https:'+src
        url=urlsplit(src)
        parent=frame.getparent()
        previous=parent.getprevious()
        while previous is not None and previous.tag not in ('h2','h3'):
            previous=previous.getprevious()
        if previous is None:
            raise ValueError('Official video embed lacks own preceding official heading: '+src)
        title=' '.join(previous.text_content().split())
        if not (6<=len(title)<=240):raise ValueError('Invalid official video title')
        if url.scheme!='https':raise ValueError('Insecure original video source '+src)
        key=f'{kind}-{i+1:02d}'
        if url.hostname in ('vk.com','vkvideo.ru') and url.path=='/video_ext.php':
            params=parse_qs(url.query,keep_blank_values=False)
            allowed={'oid','id','hd','hash','autoplay'}
            if set(params)-allowed or 'id' not in params or 'oid' not in params:
                raise ValueError('Unsafe original VK embed params: '+src)
            if not re.fullmatch(r'-?[0-9]{1,13}',params['oid'][0]) or not re.fullmatch(r'[0-9]{5,16}',params['id'][0]):
                raise ValueError('Invalid signed VK source identity: '+src)
            # Remove only autoplay to avoid auto-play after visitor has activated card.
            query='&'.join(fragment for fragment in url.query.split('&')
                           if fragment and not fragment.startswith('autoplay='))
            player_url=urlunsplit(('https',url.hostname,url.path,query,''))
            if 'autoplay=' in player_url:raise RuntimeError('autoplay unexpectedly retained')
            item={'id':key,'title':title,'source_page':SITE+path,
                  'source_iframe_src':src,'embed_url':player_url,
                  'kind':'vk','video_owner_id':params['oid'][0],
                  'hosted_in_museum_vk_group':params['oid'][0]==SID,
                  'third_party_embed_requires_click':True}
        elif (url.hostname=='cdnvideo.tvspb.ru'
              and url.path.endswith('.mp4')
              and url.path.startswith('/tvspbru-uploads/2026/09/')
              and not url.query):
            item={'id':key,'title':title,'source_page':SITE+path,
                  'source_iframe_src':src,'embed_url':None,
                  'kind':'external-mp4-link','direct_file_url':src,
                  'third_party_embed_requires_click':True}
        else:raise ValueError('Unknown original museum video provider '+src)
        items.append(item)
    return heading,items
def main():
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    groups=[]
    for i,(slug,display,path) in enumerate(SECTIONS):
        if i:sleep(10)
        raw=fetch(path)
        page_title,items=parse_original(raw,slug,path)
        groups.append({'slug':slug,'title':page_title,'source_url':SITE+path,
                       'source_html_sha256':hashlib.sha256(raw.encode()).hexdigest(),
                       'count':len(items),'videos':items})
        print('SOURCE PAGE',path,page_title,len(items),'videos',flush=True)
    all_items=[v for g in groups for v in g['videos']]
    vk=sum(x['kind']=='vk' for x in all_items)
    direct=sum(x['kind']=='external-mp4-link' for x in all_items)
    if (len(all_items),vk,direct)!=(32,31,1):
        raise RuntimeError('Museum source iframe/catalogue counts unexpected')
    key_set={(x['source_page'],x['source_iframe_src']) for x in all_items}
    if len(key_set)!=32:raise RuntimeError('Repeated embed on same museum source page')
    manifest={'source':SITE,'source_index_url':SITE+'/video','snapshot_utc':stamp,
              'group_count':len(groups),'video_count':len(all_items),
              'vk_embeds':vk,'external_mp4_file_links':direct,'groups':groups,
              'policy':'Existing original museum video titles and VK embeds. No video/image rehosting. Third party player loads by click only. No autoplay. Captions/transcripts/rights not established.'}
    tmp=OUT.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(OUT)
    print('SAVED',OUT,'SOURCE',len(groups),'GROUPS',len(all_items),'REFERENCES')
if __name__=='__main__':main()
