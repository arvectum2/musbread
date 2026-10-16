#!/usr/bin/env python3
"""Build a TZ-first, auditable 325-item grouped status/roadmap tracker.

Keeps original primary-source requirements.psv immutable. `queue` means the
next *internal* development action can start; it does NOT mean real UAT or
customer acceptance is independent of museum materials/access/approval.
"""
from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/tz-audit/requirements.psv'
OUT = ROOT / 'docs/tz-audit'

GROUPS = [
    ('01', 1, 6, 'Договор, сроки и очное интервью', 'D0 · организация'),
    ('02', 7, 16, 'Три концепции и утверждение айдентики', 'D0–D5 · концепции'),
    ('03', 17, 34, 'Фирменный стиль, логотип, типографика', 'D6–D14 · бренд'),
    ('04', 35, 61, 'Печатные и цифровые носители, мерч', 'D6–D14 · носители'),
    ('05', 62, 71, 'Правки, исходники и передача айдентики', 'D6–D14 · бренд'),
    ('06', 72, 91, 'Архитектура, роли и управление CMS', 'S0–S1 · CMS'),
    ('07', 92, 113, 'Защита, инфраструктура, обмен и SLA', 'S0–S1 · инфраструктура'),
    ('08', 114, 128, 'Главная, хедер и футер', 'S2 · публичный UI'),
    ('09', 129, 146, 'Музей и раздел для посетителей', 'S2 · структура/контент'),
    ('10', 147, 172, 'Афиша, экскурсии, выставки и наука', 'S2 · каталог'),
    ('11', 173, 197, 'Навигация, поиск, SEO, медиа и EN', 'S2 · публичный UI'),
    ('12', 198, 205, 'Билеты, формы и внешние интеграции', 'D9–D30 · интеграции'),
    ('13', 206, 213, 'Доступность интерфейса и документов', 'S2 / D25–D40 · доступность'),
    ('14', 214, 236, 'Технологии и администрирование', 'S0–S1 · backend'),
    ('15', 237, 262, 'Адаптивность, UX/UI и производительность', 'S2 / D25–D40 · UX'),
    ('16', 263, 277, 'Прототипы, согласования и этапы сдачи', 'D0–D40 · приёмка'),
    ('17', 278, 295, 'Нормативные требования и правовая проверка', 'D25–D40 · нормативы'),
    ('18', 296, 302, 'Гарантия и сопровождение', 'После сдачи · гарантия'),
    ('19', 303, 325, 'Передача файлов, исходников, прав и документов', 'D35–D40 · передача'),
]

# A curated list of tasks with an actionable local step that is not blocked by
# a required museum decision *today*. Approval may still be required at finish.
CAN_START_NOW = {
  72,73,74,75,76,77,78,82,83,85,86,87,88,89,90,91,
  94,95,96,97,101,102,104,105,106,107,110,111,113,
  114,115,117,118,120,122,123,125,126,
  134,135,136,138,139,142,147,148,150,154,163,
  173,174,175,176,177,179,181,182,184,185,186,187,188,189,190,191,192,193,194,195,197,
  206,207,208,209,210,214,215,217,218,219,220,221,223,224,225,226,228,229,230,231,
  233,234,235,236,237,238,240,241,242,245,246,249,250,251,252,256,257,260,261,262,
  267,278,279,280,281,282,283,284,285,286,287,288,289,290,291,292,293,294,295,
  308,309,310,312,315,316,317,
}

GROUP_FOR = {}
for code, lo, hi, label, phase in GROUPS:
    for n in range(lo, hi + 1):
        assert n not in GROUP_FOR, f'duplicate group for TZ-{n:03}'
        GROUP_FOR[n] = (code, label, phase)
assert set(GROUP_FOR) == set(range(1, 326))

with SOURCE.open(encoding='utf-8', newline='') as fd:
    source = list(csv.DictReader(fd, delimiter='^'))
assert len(source) == 325, f'Expected exactly 325 source clauses, got {len(source)}'
ids = [int(r['ID'][3:]) for r in source]
assert ids == list(range(1, 326)), 'Primary TZ IDs must be ordered and complete'
assert set(CAN_START_NOW) <= set(ids)
assert all(r['Фактически готово'] in ('Да','Частично','Нет') for r in source)

priority = {'P0':0, 'P1':1, 'P2':2}
phase_order = {'S0':0, 'S1':1, 'S2':2, 'D9':3, 'D25':4, 'D35':5, 'После':6, 'D0':7, 'D6':8}

def stage_priority(n):
    _,_,phase=GROUP_FOR[n]
    return next((i for prefix,i in phase_order.items() if phase.startswith(prefix)), 5)

queue_rows = [r for r in source if r['Фактически готово']!='Да' and int(r['ID'][3:]) in CAN_START_NOW]
queue_rows.sort(key=lambda r: (priority[r['Приоритет']], stage_priority(int(r['ID'][3:])), int(r['ID'][3:])))
queue_rank = {r['ID']: i for i,r in enumerate(queue_rows, 1)}
assert len(queue_rank) == len(queue_rows)

HEADERS = [
  'Группа', 'Код группы', 'ID ТЗ', 'Пункт ТЗ', 'Строки оригинала', 'Требование', 'Приоритет',
  'Светофор', 'Готовность', 'Режим', '№ очереди', 'Этап дорожной карты',
  'Что сделать для завершения', 'Что нужно от музея / внешний блокер',
  'Следующее действие / комментарий', 'Что уже есть (доказательство)', 'Учтено в плане',
]
DATA=[]
for r in source:
    n = int(r['ID'][3:])
    code, group, phase = GROUP_FOR[n]
    status = r['Фактически готово']
    if status == 'Да':
        workflow='Готово в прототипе'
        number=''
        traffic='🟢 Готово'
        action='Технически подтверждено. Сверить с фактическими критериями приёмки музея; не равно принятому контракту.'
        blocker=''
    elif r['ID'] in queue_rank:
        workflow='В очереди (можно начать сейчас)'
        number=queue_rank[r['ID']]
        traffic='🟡 Частично' if status=='Частично' else '🔴 Не готово'
        action=f'Задача в очереди #{number:03}. {r["Осталось выполнить"].strip() or "Выполнить и проверить по ТЗ"}'
        blocker='Зависимость для полного закрытия (не блокирует подготовительную разработку): '+r['Нужно от заказчика'].strip() if r['Нужно от заказчика'].strip() else ''
    else:
        workflow='Внешний блокер / наступление этапа'
        number=''
        traffic='🟡 Частично' if status=='Частично' else '🔴 Не готово'
        action='Приступить после получения указанного подтверждения/данных либо наступления контрактной стадии. '+(r['Осталось выполнить'].strip() or '')
        blocker=r['Нужно от заказчика'].strip() or 'Подтверждение/событие по договору либо согласование результата с музеем'
    DATA.append({
        'Группа':group,'Код группы':code,'ID ТЗ':r['ID'],'Пункт ТЗ':r['Пункт ТЗ'],
        'Строки оригинала':r['Строки tz.txt'],'Требование':r['Атомарное обязательство'],
        'Приоритет':r['Приоритет'],'Светофор':traffic,'Готовность':status,
        'Режим':workflow,'№ очереди':number,'Этап дорожной карты':phase,
        'Что сделать для завершения':r['Осталось выполнить'],
        'Что нужно от музея / внешний блокер':blocker,
        'Следующее действие / комментарий':action,
        'Что уже есть (доказательство)':r['Чекпоинт/доказательство'],
        'Учтено в плане':r['Учли в плане']
    })

stats=Counter(row['Готовность'] for row in DATA)
regime=Counter(row['Режим'] for row in DATA)
assert stats==Counter(r['Фактически готово'] for r in source),stats
assert sum(regime.values())==325
assert sorted([r['№ очереди'] for r in DATA if r['№ очереди']!=''])==list(range(1,len(queue_rank)+1))

with (OUT/'TZ_EXECUTION_MATRIX.csv').open('w',newline='',encoding='utf-8-sig') as fd:
    w=csv.DictWriter(fd,HEADERS,delimiter=';',lineterminator='\n');w.writeheader();w.writerows(DATA)

# JSON explicitly intended for portable, spreadsheet-independent rendering.
(OUT/'TZ_EXECUTION_MATRIX.json').write_text(json.dumps({
    'source':'requirements.psv, 325 verified primary-source clauses',
    'date':'2026-10-16','columns':HEADERS,'rows':DATA,
    'counts':stats,'workflow':regime,
},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

by_group=defaultdict(list)
for row in DATA:by_group[row['Код группы']].append(row)

def escape_md(text):
    return str(text).replace('\\','\\\\').replace('|','\\|').replace('\n',' ').replace('\r',' ')

lines=[
'# MusBread — матрица выполнения каждого пункта ТЗ по логическим группам',
'',
'> **Источник:** приложение 3 к извещению №0372200172326000015, построчный реестр [`requirements.psv`](requirements.psv). Точная формулировка оригинального DOCX при расхождении имеет приоритет. Дата контрольного снимка: 16.10.2026; актуальный источник `requirements.psv`.',
'',
'**Легенда:** 🟢 готово в техническом прототипе, 🟡 частично, 🔴 не готово. «Готово» **не означает приёмку заказчиком**. Номер очереди означает *можно начать следующий внутренний этап уже сейчас*, но не отсутствие будущих согласований. Нет номера = явный внешний блокер, обязательная стадия или решение музея.',
'',
f'**Всего {len(DATA)}:** 🟢 {stats["Да"]} · 🟡 {stats["Частично"]} · 🔴 {stats["Нет"]}. **В очереди внутренних работ: {len(queue_rank)}**, внешняя зависимость/этап: {regime["Внешний блокер / наступление этапа"]}.',
'',
'## Сводка по группам',
'',
'| № | Логическая группа | Всего | 🟢 | 🟡 | 🔴 | В очереди | Внешний блокер |',
'|---|---|---:|---:|---:|---:|---:|---:|',
]
for code,lo,hi,group,phase in GROUPS:
    rows=by_group[code];c=Counter(r['Готовность'] for r in rows);q=sum(bool(r['№ очереди']) for r in rows)
    lines.append(f'| {code} | {group} | {len(rows)} | {c["Да"]} | {c["Частично"]} | {c["Нет"]} | {q} | {len(rows)-c["Да"]-q} |')
lines+=['','## Пункты ТЗ — полная матрица','','Поля «следующее действие» и «что требуется» **не** заменяют официальные критерии приёмки и не создают обязательства сторон сверх ТЗ.','']
for code,lo,hi,group,phase in GROUPS:
    lines+=[f'### {code}. {group} — TZ-{lo:03}…TZ-{hi:03}', '',f'*Этап: {phase}*','',
            '| Пункт | P | Светофор | Очередь | Что требуется / блокер | Доказательство |',
            '|---|---|---|---:|---|---|']
    for row in by_group[code]:
        task=row['Что сделать для завершения']
        if row['№ очереди']:
            follow=f'**Следующий шаг:** {task}.'
            if row['Что нужно от музея / внешний блокер']:
                follow+=f' **Для окончательного закрытия:** {row["Что нужно от музея / внешний блокер"]}.'
        elif row['Готовность']=='Да':follow='Реализовано и проверено в прототипе; приёмка заказчика отдельно.'
        else:
            follow=f'**Блокер:** {row["Что нужно от музея / внешний блокер"]}. **После:** {task}.'
        lines.append('| '+' | '.join(map(escape_md,[
          f'{row["ID ТЗ"]} · {row["Требование"]} (п. {row["Пункт ТЗ"]})',
          row['Приоритет'],row['Светофор'],f'№{row["№ очереди"]:03}' if row['№ очереди'] else '—',
          follow,row['Что уже есть (доказательство)'],
        ]))+' |')
    lines.append('')
lines+=['## Принцип дальнейшей работы', '',
'1. Перед каждым действием сверять оригинальный текст ТЗ (TZ-ID и строка).',
'2. Если есть номер очереди — брать следующий доступный номер с учётом технологических зависимостей; после выполнения обновлять доказательства и статус в `requirements.psv`, затем заново собирать матрицу.',
'3. Если есть блокер — запрашивать конкретные исходники, доступ или согласование у музея. Не выдавать «сделано» до завершения.',
'4. Порядок — рабочая версия до решения по закупке и интервью; после контракта уточнить реальные сроки и взаимозависимости.',
'', '**Для фильтрации в Excel/Numbers:** [`TZ_EXECUTION_MATRIX.csv`](TZ_EXECUTION_MATRIX.csv). Для просмотра без таблиц: [`TZ_EXECUTION_MATRIX.html`](TZ_EXECUTION_MATRIX.html).', '']
(OUT/'TZ_EXECUTION_MATRIX.md').write_text('\n'.join(lines),encoding='utf-8')

# Standalone offline HTML viewer: no CDN, cookies, network, server or user data.
style='''
:root{color-scheme:light;--ink:#172b3d;--muted:#576a78;--line:#dce5ec;--bg:#f5f7fb;--green:#d9f3e5;--yellow:#fff1c7;--red:#ffdddd;--accent:#164d66}
*{box-sizing:border-box}body{margin:0;font:14px/1.55 system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--ink)}
header{background:#12384e;color:#fff;padding:30px max(24px,calc((100% - 1460px)/2))}h1{font-size:1.55rem;margin:0 0 .4rem}header p{margin:0;color:#d4e4ed}
main{max-width:1510px;padding:24px;margin:auto}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px}
.tile{background:#fff;padding:17px 19px;border:1px solid var(--line);border-radius:9px}.tile b{display:block;font-size:28px}.sub{font-size:12px;color:var(--muted)}
.note{background:#fff;border-left:3px solid var(--accent);padding:12px 16px;margin:18px 0;border-radius:5px}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}.controls input,.controls select{border:1px solid #b8c8d2;background:#fff;padding:10px;border-radius:6px;font:inherit;max-width:100%}.controls input{min-width:280px;flex:1}
.wrap{overflow:auto;border:1px solid var(--line);border-radius:9px;background:#fff;max-height:73vh}table{width:100%;border-collapse:separate;border-spacing:0;min-width:1260px}thead th{position:sticky;top:0;background:#e9f0f4;z-index:1;text-align:left;padding:11px 12px;border-bottom:1px solid #aec3cf;white-space:nowrap}td{padding:10px 12px;border-bottom:1px solid #e8edf1;vertical-align:top}tr:hover td{background:#f5f9ff}td:nth-child(4){max-width:420px;min-width:300px}td:nth-child(8){max-width:425px;min-width:300px}.muted{color:var(--muted)}.state{font-weight:650;white-space:nowrap;padding:4px 8px;border-radius:5px;display:inline-block}.state.ok{background:var(--green)}.state.part{background:var(--yellow)}.state.no{background:var(--red)}.queue{color:#034f7c;font-variant-numeric:tabular-nums;font-weight:700}.tag{font-size:11px;background:#e9f1f5;border-radius:4px;padding:3px 6px;white-space:nowrap}footer{color:#526775;margin:20px 2px}a{color:#045b87}button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #d38a32;outline-offset:2px}
'''
first='''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MusBread · Матрица ТЗ 325 пунктов</title><style>'''+style+'''</style></head><body>
<header><h1>Матрица выполнения ТЗ · MusBread</h1><p>325 атомарных требований · исходник: ЕИС, приложение 3 · снимок 16.10.2026 · проект до контракта</p></header>
<main><div class="grid"><div class="tile"><b>325</b><span>всего требований</span></div>
<div class="tile"><b>🟢 '''+str(stats['Да'])+'''</b><span>готово в прототипе</span></div><div class="tile"><b>🟡 '''+str(stats['Частично'])+'''</b><span>частично готово</span></div>
<div class="tile"><b>🔴 '''+str(stats['Нет'])+'''</b><span>не готово</span></div><div class="tile"><b>'''+str(len(queue_rank))+'''</b><span>можно брать в разработку</span></div></div>
<div class="note"><strong>Как читать:</strong> номер очереди — есть самостоятельная работа, которую можно начинать сейчас; в комментарии показана остающаяся зависимость для полной сдачи. Если номер не указан, пункт ждёт музей, контрактную стадию или внешнюю инфраструктуру. Зелёный не означает официальный акт приёмки. <a href="TZ_EXECUTION_MATRIX.csv">Открыть CSV</a> · <a href="TZ_EXECUTION_MATRIX.md">Открыть Markdown</a>.</div>
<div class="controls"><input id="search" aria-label="Искать пункт, номер или комментарий" placeholder="Номер ТЗ, слово, пункт, блокер…"><select id="group" aria-label="Логическая группа"><option value="">Все группы</option>'''
first+=''.join(f'<option value="{code}">{html.escape(code+" · "+name)}</option>' for code,_,_,name,_ in GROUPS)
first+='''</select><select id="state" aria-label="Статус"><option value="">Все статусы</option><option value="Да">🟢 Готово</option><option value="Частично">🟡 Частично</option><option value="Нет">🔴 Не готово</option></select><select id="regime" aria-label="Блокер или очередь"><option value="">Все задачи</option><option value="queued">С номером очереди</option><option value="blocked">Внешний блокер</option><option value="done">Готово</option></select><select id="priority" aria-label="Приоритет"><option value="">Любой приоритет</option><option>P0</option><option>P1</option><option>P2</option></select></div>
<p class="sub" id="shown" role="status" aria-live="polite">Показано 325 из 325</p><div class="wrap"><table><thead><tr><th>ТЗ</th><th>Блок</th><th>P</th><th>Требование</th><th>Светофор</th><th>Очередь</th><th>Этап</th><th>Что нужно для завершения</th><th>Пункт/стр.</th></tr></thead><tbody id="results">'''
body=[]
for row in DATA:
    status=row['Готовность'];flag='ok' if status=='Да' else 'part' if status=='Частично' else 'no'
    task=row['Что сделать для завершения']
    if row['№ очереди']:
        context=f'Сейчас: {task}. Для сдачи: {row["Что нужно от музея / внешний блокер"] or "последующая приёмка"}.'
    elif status=='Да':context=f'Подтверждено: {row["Что уже есть (доказательство)"]}. Окончательная клиентская приёмка отдельно.'
    else:context=f'Блокер: {row["Что нужно от музея / внешний блокер"]}. Затем: {task}.'
    escaped=lambda x:html.escape(str(x),quote=True)
    queue=f'<span class="queue">№{row["№ очереди"]:03}</span>' if row['№ очереди'] else '—'
    body.append(f'<tr data-group="{row["Код группы"]}" data-priority="{row["Приоритет"]}" data-state="{status}" data-regime="{"done" if status=="Да" else "queued" if row["№ очереди"] else "blocked"}"><td><strong>{row["ID ТЗ"]}</strong></td><td>{escaped(row["Группа"])}</td><td><span class="tag">{row["Приоритет"]}</span></td><td>{escaped(row["Требование"])}</td><td><span class="state {flag}">{row["Светофор"]}</span></td><td>{queue}</td><td>{escaped(row["Этап дорожной карты"])}</td><td>{escaped(context)}</td><td>{escaped(row["Пункт ТЗ"])}<br><span class="muted">стр. {escaped(row["Строки оригинала"])}</span></td></tr>')
end='''</tbody></table></div><footer>Источник первичных формулировок — requirements.psv. Без интернет-запросов; все фильтры выполняются локально в вашем браузере. При изменении статусов запускайте scripts/build_tz_execution_matrix.py.</footer></main><script>
const rows=[...document.querySelectorAll('#results tr')];const s=document.querySelector('#search'),g=document.querySelector('#group'),t=document.querySelector('#state'),p=document.querySelector('#priority'),r=document.querySelector('#regime');
function refresh(){const search=s.value.trim().toLocaleLowerCase('ru');let count=0;for(const tr of rows){const ok=(!search||tr.textContent.toLocaleLowerCase('ru').includes(search))&&(!g.value||tr.dataset.group===g.value)&&(!t.value||tr.dataset.state===t.value)&&(!p.value||tr.dataset.priority===p.value)&&(!r.value||tr.dataset.regime===r.value);tr.hidden=!ok;if(ok)count++;}document.querySelector('#shown').textContent=`Показано ${count} из ${rows.length}`;}
for(const el of [s,g,t,p,r])el.addEventListener(el===s?'input':'change',refresh);
</script></body></html>'''
(OUT/'TZ_EXECUTION_MATRIX.html').write_text(first+'\n'.join(body)+end,encoding='utf-8')

print('COUNTS',dict(stats),'REGIMES',dict(regime),'GROUPS',len(GROUPS),'QUEUE_LENGTH',len(queue_rows))
print('EXAMPLES_QUEUE',[(i,r['ID']) for i,r in enumerate(queue_rows[:12],1)])
print('GENERATED',*[f'{p.name}:{p.stat().st_size}' for p in [OUT/'TZ_EXECUTION_MATRIX.csv',OUT/'TZ_EXECUTION_MATRIX.md',OUT/'TZ_EXECUTION_MATRIX.json',OUT/'TZ_EXECUTION_MATRIX.html']])
