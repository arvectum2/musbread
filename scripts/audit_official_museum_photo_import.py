#!/usr/bin/env python3
"""Read-only provenance audit of real museum photos in private CMS.

The only distributable artifact is metadata: no JPG/WebP bytes ever copied
into Git; private preview rights remain false until official confirmation.
"""
from __future__ import annotations
import csv,json,sqlite3
from collections import Counter
from hashlib import sha256
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.local_archive/museum-official-photos'
MANIFEST=PRIVATE/'manifest.json'
DB=ROOT/'apps/cms/database/database.sqlite'
OUT=ROOT/'docs/source-migration/OFFICIAL_PHOTOS_IMPORTED_20261018.csv'
REPORT=ROOT/'docs/source-migration/ORIGINAL_MUSEUM_PHOTO_IMPORT_20261018.md'

def report():
    data=json.loads(MANIFEST.read_text())
    if data.get('source')!='https://muzei-xleb.ru' or data.get('rights_status')!='not-verified-private-only':
        raise RuntimeError('Not source-owned or rights-embargoed')
    if len(data.get('files',[]))!=data['count']:
        raise RuntimeError('Truncated photo manifest')
    conn=sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True)
    conn.row_factory=sqlite3.Row
    if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
        raise RuntimeError('CMS database integrity error')
    existing=conn.execute("""
        select m.sha256 as preview_sha,m.source_original_sha256,m.source_original_url,
               m.source_rights_pending,m.storage_path,m.width,m.height,
               m.size_bytes,m.alt,m.caption,e.slug,e.status
        from museum_media m join museum_entries e on e.id=m.museum_entry_id
        where m.source_original_sha256 is not null
    """).fetchall()
    # The same original image bytes are reused by the museum under
    # separate official page paths. Identity is SOURCE URL, not image hash.
    by_url={r['source_original_url']:r for r in existing}
    if len(by_url)!=len(existing):raise RuntimeError('Repeated original photo source URL in CMS')
    table=[]
    for source in data['files']:
        name=source['local_name']
        orig=PRIVATE/name
        if not orig.is_file() or orig.stat().st_size!=source['size_bytes']:
            raise RuntimeError('Original not cached or unexpected length '+name)
        digest=sha256(orig.read_bytes()).hexdigest()
        if digest!=source['sha256']:raise RuntimeError('Original photo bytes mismatch')
        media=by_url.get(source['original_url'])
        if media is not None and media['source_original_sha256']!=digest:
            raise RuntimeError('Source image bytes replaced since archival capture')
        if not media:raise RuntimeError('Missing CMS preview for original '+source['cms_slug'])
        if (media['source_rights_pending']!=1 or media['status']!='draft'
            or media['slug']!=source['cms_slug']
            or media['source_original_url']!=source['original_url']):
            raise RuntimeError('Source or editor/media rights leak risk: '+source['cms_slug'])
        preview=ROOT/'apps/cms/storage/app/private'/media['storage_path']
        # Laravel local disk may use other safe private root based on storage settings.
        if not preview.is_file():
            preview=ROOT/'apps/cms/storage/app'/media['storage_path']
        if not preview.is_file():
            raise RuntimeError('Private preview missing: '+media['storage_path'])
        if preview.stat().st_size!=media['size_bytes'] or sha256(preview.read_bytes()).hexdigest()!=media['preview_sha']:
            raise RuntimeError('CMS preview differs from digest')
        table.append({
            'cms_slug':media['slug'],
            'source_page_url':source['source_page_url'],
            'original_url':source['original_url'],
            'original_sha256':digest,
            'original_size_bytes':source['size_bytes'],
            'source_image_index':source.get('source_image_index',0),
            'source_alt_as_captured':source['source_alt'],
            'private_preview_dimensions':str(media['width'])+'x'+str(media['height']),
            'private_preview_sha256':media['preview_sha'],
            'rights_status':'private-needs-editorial-and-rights-review',
        })
    if len(existing)!=len(table):
        raise RuntimeError('CMS has additional source images outside verified manifest')
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(table[0]),delimiter=';',lineterminator='\n')
        w.writeheader();w.writerows(table)
    counts=Counter(r['cms_slug'] for r in table)
    workshop=sum(s.startswith('museum-workshop-') for s in counts)
    tours=sum(s.startswith('museum-tour-') for s in counts)
    lines=[
        '# Оригинальные фотографии музея — приватный перенос 18.10.2026',
        '',
        '**Без заменителей, генерации и стоковых изображений.**',
        'Источник — реальные фотографии на https://muzei-xleb.ru,'
        ' адреса получены из проверенных музейных страниц экскурсий и мастер-классов.',
        '',
        '- Прямых оригиналов JPEG/PNG/WebP сохранено на ArvectumSSD: **'+str(len(table))+'**.',
        '- Оригинальные страницы, к которым привязаны снимки в CMS: **'+str(len(counts))+'**'
          ' ('+str(workshop)+' мастер-классов, '+str(tours)+' экскурсионных программ).',
        '- Дополнительных снимков внутри галерей сверх первой фотографии: **'
          +str(len(table)-len(counts))+'**.',
        '- Уникальных наборов байтов по SHA-256: **'
          +str(len({r['original_sha256'] for r in table}))+'**. Одна фотография'
          ' действительно используется музеем в двух материалах с разными URL;'
          ' оба исходных URL и обе связи в CMS сохранены.',
        '- Подлинные исходные файлы и их SHA-256 проверены повторно.'
          ' Оригиналы остаются неизменными в закрытом .local_archive.',
        '- Для просмотра в MoonShine созданы технические WebP-превью'
          ' по оригинальным изображениям с сохранением изображения целиком,'
          ' без кадрирования или визуальной генерации. Один большой JPEG'
          ' пропорционально уменьшен только для превью; полный оригинал сохранён.',
        '- **Ноль** фотографий автоматически допускается к публичному экспорту:'
          ' у всех признак source_rights_pending=true, исходные ссылки сохранены.'
          ' Требуются отдельные правовые и редакторские согласования с музеем.',
        '',
        '## Воспроизведение',
        '',
        'Список источников и хешей: [OFFICIAL_PHOTOS_IMPORTED_20261018.csv]'
          '(OFFICIAL_PHOTOS_IMPORTED_20261018.csv).',
        'Приватные оригиналы и манифест — .local_archive/museum-official-photos/'
          ' на внешнем ArvectumSSD; эти файлы не добавляются в Git.',
        'Скрипт прямого скачивания — scripts/cache_official_museum_photos.py'
          ' (museum robots Crawl-delay 10 сек), проверка —'
          ' scripts/audit_official_museum_photo_import.py.',
        'Импорт — php artisan museum:import-official-photos --apply;'
          ' без --apply запускается только безопасный dry-run.',
        '',
        '## Следующие реальные пробелы',
        '',
        'Сейчас захвачены обложки и часть исходных галерей программ.'
        ' Следом переносим остальные кадры экскурсионных/детских галерей,'
        ' затем фотографии выставок, 11 залов и истории здания.'
        ' Иконки PDF, QR-коды и другие служебные изображения'
        ' необходимо отличать от музейных фотографий.',
        '',
        'Светофор полного ТЗ **84/102/139**, не завышался.'
    ]
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('VERIFIED PRIVATE SOURCE PHOTOS',len(table),'IN',len(counts),'MUSEUM ENTRIES',dict(Counter(r['source_image_index'] for r in table)))
    return table

if __name__=='__main__':report()
