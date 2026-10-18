#!/usr/bin/env python3
"""Pre-release Nginx redirect-graph validation against the FULL offline build.

Checks all 881 generated 301 targets, source-loop absence, chains, and actual
static content byte availability. This is NOT nginx -t and NOT live HTTP.
No DNS, production web server, SSL or public website is touched.
"""
from __future__ import annotations
import json,re,hashlib
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]
NGINX=ROOT/'deploy/nginx/legacy_museum_redirects.map.conf'
OUT=ROOT/'apps/web/out'
REPORT=ROOT/'docs/seo/NGINX_301_GRAPH_PREFLIGHT_20261018.md'
MAP_RULE=re.compile(r'^    (/[^\s"]+) "(/[^"]+)";$')
HTML_CANONICAL=re.compile(r'<link rel="canonical" href="([^"]+)"')

def preflight():
    raw=NGINX.read_text(encoding='utf-8').splitlines()
    pairs=[m.groups() for line in raw if (m:=MAP_RULE.fullmatch(line))]
    if len(pairs)!=881 or len({s for s,_ in pairs})!=881:
        raise RuntimeError('Prepared 301 map altered or includes duplicate source paths')
    redirects=dict(pairs)
    problems=[]
    typed=Counter()
    for old,target in pairs:
        if not old.startswith('/') or not target.startswith('/') or '?' in old or '?' in target or '#' in target:
            problems.append(('unsafe old/target',old,target));continue
        path=urlsplit(target).path
        if (path.rstrip('/') or '/')==(old.rstrip('/') or '/'):
            problems.append(('self redirect loop',old,target))
        if (path.rstrip('/') or '/') in redirects:
            problems.append(('another mapped redirect target: 2+ hops',old,target))
        if path.startswith('/media/museum-source/'):
            typed['image']+=1
            static=OUT/path.lstrip('/')
            if not re.fullmatch(r'/media/museum-source/[a-f0-9]{64}\.webp',path) or not static.is_file():
                problems.append(('missing image file',old,target))
            else:
                with static.open('rb') as file:
                    if file.read(4)!=b'RIFF':problems.append(('invalid WebP file bytes',old,target))
        else:
            typed['page']+=1
            static=OUT/path.lstrip('/')/'index.html'
            if not static.is_file():
                problems.append(('missing source-backed target HTML',old,target))
            else:
                body=static.read_text(encoding='utf-8')
                if '<meta http-equiv="refresh"' in body.lower():
                    problems.append(('source redirects to another HTML meta-refresh',old,target))
                else:
                    canonical=HTML_CANONICAL.search(body)
                    if not canonical:
                        problems.append(('redirect target HTML has no explicit canonical',old,target))
                    elif canonical.group(1)!='https://muzei-xleb.ru'+path.rstrip('/'):
                        problems.append(('redirect target canonical mismatch',old,target))
    actual={'rules':len(pairs),'page_rules':typed['page'],'image_rules':typed['image'],
      'missing_targets_or_loops_or_chains':len(problems),'examples':problems[:25],
      'http_status_test':'NOT RUN — no nginx installed and no production host authorized',
      'production_status':'UNDEPLOYED / NO-GO'}
    if problems:
        raise RuntimeError('Museum Nginx redirect chain/preflight failed: '+str(actual))
    REPORT.write_text(f'''# CP-SEO-02 · проверка графа 301 без включения сайта · 18.10.2026

**Подготовлено, но НЕ развёрнуто.** Локальный контроль всех **{len(pairs)}** правил Nginx на Mac mini относительно собранной неизменной статической версии музея `apps/web/out`. Проверены только исходные URL из музейного первоисточника; рабочий DNS и сайт заказчика не тронуты.

| Проверка | Результат |
|---|---:|
| Количество целевых HTTP 301 в подготовленной конфигурации | {len(pairs)} |
| Исторические /node/N + технические /news/ | {typed['page']} |
| Исторические JPEG/thumbnail → собственные WebP | {typed['image']} |
| Повторные источники URL | 0 |
| Редиректы на собственный старый путь (loop) | 0 |
| Редирект на другую строку таблицы (chain) | 0 |
| Отсутствующие конечные HTML/WebP по загруженному статическому пакету | 0 |
| Промежуточные `meta refresh` как конечная цель Nginx | 0 |
| Несовпадения canonical на конечной HTML-странице | 0 |

Карта [лежит в `deploy/nginx`](../../deploy/nginx/legacy_museum_redirects.map.conf); исходные страницы и контент — в [общей матрице старых URL](URL_MIGRATION_MATRIX_20261018.csv). Здесь проверена **структура**, а не реальное поведение HTTP: нет установленного Nginx на Mac mini в PATH, не выполнен `nginx -t`, не проверены коды 301/200 на боевом хосте, HTTP `HEAD`, `robots.txt`, sitemap и сертификат. Применять только после согласования инфраструктуры, проверки оборудования и плана отката. **NO-GO до договора/утверждения и реального HTTP-теста.**
''',encoding='utf-8')
    print('ALL_MUSEUM_NGINX_REDIRECTS_OFFLINE_GRAPH_PASS',actual,flush=True)
    return actual
if __name__=='__main__':preflight()
