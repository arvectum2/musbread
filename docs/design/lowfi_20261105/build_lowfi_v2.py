#!/usr/bin/env python3
"""Revised Museum of Bread low-fi presentation. Native VectorCraft authoring via CLI."""
import json,subprocess,html,shutil
from pathlib import Path
R=Path(__file__).resolve().parent;SVG=R/'svg';SVG.mkdir(exist_ok=True)
VC='/Volumes/ArvectumSSD/Arvectum/labs/vectorcraft-test/bin/vectorcraft-cli-0.13.1-macos-universal/vectorcraft-cli'
W,H=1440,900
BG='#ffffff';INK='#1c2a3b';TEXT='#314052';MUT='#627284';BORDER='#d4dce4';SOFT='#f5f7f9';DEEP='#e9edf2';ACC='#4b6176'
pages=[]
class Slide:
 def __init__(self,title='',sub=''):
  self.s=['<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="900" viewBox="0 0 1440 900">']
  self.rect(0,0,W,H,BG,0,None)
  if title:
   self.text(64,88,title,42,INK,700)
   if sub:self.text(66,128,sub,19,MUT)
 def rect(self,x,y,w,h,fill=BG,r=8,stroke=BORDER,sw=1):
  self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}"'+(f' stroke="{stroke}" stroke-width="{sw}"' if stroke else '')+'/>')
 def text(self,x,y,t,size=18,color=TEXT,bold=400,anchor=None):
  a=f' x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" font-weight="{bold}" fill="{color}"'
  if anchor:a+=f' text-anchor="{anchor}"'
  self.s.append('<text'+a+'>'+html.escape(str(t))+'</text>')
 def line(self,x,y,x2,y2,color=BORDER,width=1):
  self.s.append(f'<path d="M{x} {y} L{x2} {y2}" stroke="{color}" stroke-width="{width}" fill="none"/>')
 def label(self,x,y,t):self.text(x,y,t,15,MUT,700)
 def lines(self,x,y,lines,size=18,lh=32,color=TEXT,bold=400):
  for i,t in enumerate(lines):self.text(x,y+i*lh,t,size,color,bold)
 def outline(self,x,y,w,h,text='ИЗОБРАЖЕНИЕ'):
  self.rect(x,y,w,h,DEEP,5,None)
  self.text(x+18,y+31,text,14,MUT,700)
 def btn(self,x,y,w,s,filled=True):
  self.rect(x,y,w,42,ACC if filled else BG,6,ACC,1)
  self.text(x+w/2,y+27,s,15,BG if filled else ACC,700,'middle')
 def site_header(self,x,y,w,compact=False):
  self.rect(x,y,w,87,BG,0,None);self.line(x,y+86,x+w,y+86,BORDER)
  self.text(x+21,y+42,'МУЗЕЙ ХЛЕБА',21,INK,700)
  if compact:self.text(x+w-56,y+42,'Меню',16,ACC,700,'end')
  else:
   for offset,name in [(218,'Музей'),(292,'Посетителям'),(417,'Афиша'),(494,'Экскурсии'),(609,'Детям'),(681,'Выставки'),(784,'Наука')]:self.text(x+offset,y+39,name,15,TEXT)
   self.text(x+225,y+66,'Поиск',14,ACC,700)
   self.text(x+316,y+66,'Для слабовидящих',14,ACC,700)
   self.text(x+510,y+66,'Доступная среда',14,ACC,700)
   self.text(x+733,y+66,'Соцсети',14,MUT,700)
   self.btn(x+w-169,y+15,147,'Купить билет')
 def card(self,x,y,w,h,title,desc='',meta=''):
  self.rect(x,y,w,h,BG,8,BORDER)
  self.outline(x+14,y+14,w-28,90 if h<=200 else (138 if h<=245 else 150),'ФОТО СОБЫТИЯ')
  self.text(x+18,y+h-(49 if h<=245 else 89),title,19,INK,700)
  if desc:self.text(x+18,y+h-(20 if h<=245 else 56),desc,16,TEXT)
  if meta:self.text(x+18,y+h-25,meta,14,MUT)
 def section(self,x,y,w,h,title,details):
  self.rect(x,y,w,h,SOFT,9,None)
  self.text(x+20,y+42,title,21,INK,700)
  for j,t in enumerate(details):self.text(x+20,y+77+30*j,t,16,TEXT)
 def end(self,name):
  self.s.append('</svg>');p=SVG/(name+'.svg');p.write_text('\n'.join(self.s),encoding='utf-8');pages.append(p)
# 01 — restrained cover with explicit outcome
s=Slide()
s.text(75,142,'UX-модель сайта',54,INK,700);s.text(75,209,'Музея хлеба',54,INK,700)
s.text(78,264,'Для очного обсуждения · 6 ноября 2026',22,MUT)
s.line(78,302,1360,302)
s.text(78,363,'ЧТО ПРОВЕРЯЕМ',16,MUT,700)
s.lines(78,405,['Сценарии основных групп посетителей','Структуру разделов и навигацию','Расположение блоков ключевых страниц'],22,52,INK)
s.text(78,646,'16 ЛИСТОВ',16,MUT,700)
s.lines(78,688,['Модели поведения · карта сайта','Экраны для компьютера, планшета и телефона','Поиск · билеты · доступность · вопросы'],18,35)
# decorative cover sample serves concrete layout example
s.rect(910,343,456,342,SOFT,12,None)
s.rect(935,369,407,60,BG,5,BORDER);s.text(954,405,'Музей хлеба',19,INK,700)
s.outline(935,445,241,102,'ОСНОВНОЙ БЛОК')
s.rect(1191,445,151,102,BG,5,BORDER);s.text(1204,482,'ПОСЕЩЕНИЕ',13,MUT,700)
for x in [935,1074,1213]:
 s.rect(x,563,129,99,BG,5,BORDER);s.rect(x+11,576,107,43,DEEP,3,None);s.line(x+12,634,x+112,634,MUT)
s.end('01_cover')
# 02 — audience journeys
s=Slide('Пользовательские сценарии','Какие задачи должен решать сайт за минимальное число шагов')
cols=[78,349,626,1007];head=['Аудитория','Задача','Маршрут','Результат']
s.rect(66,187,1309,65,INK,8,None)
for x,t in zip(cols,head):s.text(x,228,t,17,BG,700)
rows=[
 ('Первый посетитель','Режим и адрес','Главная  /  Посетителям','Спланирован визит'),
 ('Семья с детьми','Подобрать программу','Детям  /  Афиша','Выбрано событие'),
 ('Турист','Приобрести билет','Посетителям  /  Билеты','Переход к оператору'),
 ('Исследователь','Найти материал','Наука  /  Публикации','Найден документ'),
 ('Маломобильный гость','Проверить условия','Доступная среда','Понятны условия визита')]
for i,row in enumerate(rows):
 y=265+i*110
 s.rect(66,y,1309,99,SOFT if i%2==0 else BG,7,BORDER)
 for x,t in zip(cols,row):s.text(x,y+57,t,18,INK if x==78 else TEXT,700 if x==78 else 400)
s.end('02_audiences')
# 03 — complete IA with seven columns, no tiny footers
s=Slide('Структура сайта','Разделы и подразделы из действующего технического задания')
s.rect(522,165,396,63,INK,8,None);s.text(720,203,'Главная',24,BG,700,'middle')
s.line(720,228,720,254,ACC,2);s.line(140,254,1300,254,ACC,2)
groups=[
 ('Музей',['История музея','История здания','Экспозиция','Команда','Друзья музея','Официальные','документы','Новости','Медиа','Вакансии','Контакты']),
 ('Посетителям',['Спланировать визит','Билеты и льготы','Пушкинская карта','Доступная среда','Магазин','Частые вопросы']),
 ('Афиша',['Все события','Экскурсии','Детям','Выставки','Встречи','Фестивали','Мастер-классы','Архив']),
 ('Экскурсии',['Обзорная','Интерактивные','Тематические','Мастер-классы','для взрослых']),
 ('Детям',['Интерактивные','Тематические','Мастер-классы','для детей']),
 ('Выставки',['Текущие','Будущие','Передвижные']),
 ('Наука',['Семинары','Публикации','Коллекция','Исследователям','Материалы по теме'])
]
for i,(title,subs) in enumerate(groups):
 x=49+i*198;s.line(x+91,254,x+91,281,ACC,2)
 s.rect(x,283,183,54,ACC,7,None);s.text(x+13,317,title,17,BG,700)
 s.rect(x,346,183,459,SOFT,7,None)
 for j,a in enumerate(subs):s.text(x+12,379+36*j,a,15,TEXT)
s.end('03_sitemap')
# 04 desktop
s=Slide('Главная · компьютер','Основная информация о музее и наиболее частые действия посетителя')
s.rect(61,166,1318,656,BG,11,BORDER)
s.site_header(78,181,1284)
s.text(101,347,'Музей хлеба',37,INK,700)
s.text(102,386,'История и современная жизнь музея',20,MUT)
s.btn(102,421,194,'Купить билет')
s.btn(308,421,212,'Спланировать визит',False)
s.outline(769,306,577,177,'ФОТОГРАФИЯ МУЗЕЯ')
s.text(101,533,'Афиша',25,INK,700)
s.text(1195,531,'Все события',16,ACC,700)
for i,(t,d) in enumerate([('Выставка','Дата и название'),('Экскурсия','Расписание'),('Мастер-класс','Возраст и запись')]):
 s.card(101+i*415,551,398,190,t,d)
s.rect(101,751,1245,53,SOFT,7,None)
for i,(a,b) in enumerate([('Режим работы','Часы посещения'),('Адрес','Маршрут'),('Билеты','Стоимость и льготы'),('Контакты','Связаться с музеем')]):
 x=117+i*309;s.text(x,773,a,14,INK,700);s.text(x,794,b,13,MUT)
s.end('04_home_desktop')
# 05 tablet: responsive variant
s=Slide('Главная · планшет','Уплотнение навигации и двухколоночная сетка событий')
s.rect(247,164,946,661,BG,15,BORDER);s.site_header(264,180,912,True)
s.rect(277,296,888,192,SOFT,9,None)
s.text(300,352,'Музей хлеба',30,INK,700);s.text(300,390,'Посещение, выставки и события',19,MUT)
s.btn(300,412,198,'Купить билет');s.btn(511,412,206,'Как добраться',False)
s.outline(825,315,320,146,'ФОТО МУЗЕЯ')
s.text(278,536,'Ближайшие события',25,INK,700)
s.card(278,555,427,238,'Выставка','Дата / подробности')
s.card(725,555,439,238,'Мастер-класс','Возраст / запись')
s.end('05_home_tablet')
# 06 mobile responsive
s=Slide('Главная · телефон','Первый экран и продолжение страницы после прокрутки')
for x in [238,795]:
 s.rect(x,164,404,662,BG,20,BORDER,2)
 s.site_header(x+12,185,380,True)
# first viewport
s.outline(266,300,348,133,'ФОТО МУЗЕЯ')
s.text(266,476,'Музей хлеба',28,INK,700);s.text(266,506,'Посещение и события',17,MUT)
s.btn(266,536,170,'Купить билет');s.btn(446,536,166,'Маршрут',False)
s.line(266,618,614,618)
s.text(266,659,'Ближайшие события',20,INK,700)
s.rect(266,676,348,120,SOFT,7,None);s.text(283,715,'Выставка',19,INK,700)
s.text(283,743,'Дата и место проведения',15,MUT)
# continuation
s.text(825,311,'Афиша',25,INK,700)
s.outline(825,332,344,146,'ФОТО СОБЫТИЯ')
s.text(825,512,'Мастер-класс',21,INK,700);s.text(825,538,'Возраст, дата, формат участия',16,MUT)
s.rect(825,579,344,117,SOFT,7,None)
s.text(843,612,'Планирование визита',18,INK,700)
s.text(843,641,'Часы работы · билеты · льготы',15,TEXT)
s.rect(825,720,344,73,BG,7,BORDER);s.text(844,761,'Контакты и документы',17,INK,700)
s.end('06_home_mobile')
# 07 visitors section
s=Slide('Раздел «Посетителям»','Шесть практических сценариев, которые предусмотрены ТЗ')
s.rect(61,166,1318,656,BG,11,BORDER);s.site_header(78,181,1284)
s.text(102,346,'Посетителям',32,INK,700)
s.text(102,383,'Всё необходимое для планирования визита',18,MUT)
items=[
 ('Спланировать визит',['Часы работы','Адрес и маршрут']),('Билеты и льготы',['Категории билетов','Условия возврата']),('Пушкинская карта',['Условия программы','Ссылка на сервис']),
 ('Доступная среда',['Возможности музея','Контакты для связи']),('Магазин',['Информация и товары','Без онлайн-продажи']),('Частые вопросы',['Правила посещения','Краткие ответы'])]
for i,(t,d) in enumerate(items):
 x=101+(i%3)*417;y=407+(i//3)*173;s.section(x,y,398,159,t,d)
s.end('07_visitors')
# 08 events listing
s=Slide('Раздел «Афиша»','События музея, рубрики и переход к подробной информации')
s.rect(61,166,1318,656,BG,11,BORDER);s.site_header(78,181,1284)
s.text(101,337,'Афиша',32,INK,700)
for xx,name in [(101,'Все события'),(260,'Экскурсии'),(390,'Детям'),(483,'Выставки'),(617,'Встречи'),(744,'Фестивали'),(869,'Мастер-классы')]:s.text(xx,376,name,16,ACC,700)
s.line(100,392,1344,392);s.line(101,393,230,393,ACC,3)
s.text(103,429,'Категория',14,MUT,700);s.rect(193,405,286,43,SOFT,6,BORDER);s.text(213,433,'Все события',16,TEXT)
s.text(504,429,'Период',14,MUT,700);s.rect(574,405,286,43,SOFT,6,BORDER);s.text(594,433,'Любая дата',16,TEXT)
s.btn(875,405,166,'Показать')
s.text(1181,431,'Архив событий',15,ACC,700)
for i,(t,d,m) in enumerate([('Экскурсия','Тематический маршрут','Дата · билет'),('Выставка','Событие музея','Дата · вход'),('Мастер-класс','Программа для гостей','Возраст · запись')]):
 s.card(102+i*418,482,398,287,t,d,m)
s.end('08_events')
# 09 event detail
s=Slide('Страница события / экскурсии','Информация для выбора мероприятия и перехода к билетному сервису')
s.rect(61,166,1318,656,BG,11,BORDER);s.site_header(78,181,1284)
s.text(102,314,'Главная / Афиша / Событие',15,MUT)
s.text(102,361,'Название мероприятия',31,INK,700)
s.outline(102,388,723,318,'ФОТО ИЛИ АФИША')
s.rect(849,388,497,318,SOFT,8,None)
s.text(869,429,'Информация о посещении',21,INK,700)
for i,t in enumerate(['Дата и время','Продолжительность','Возраст','Стоимость и льготы','Место проведения']):
 y=471+i*40;s.text(869,y,t,16,TEXT);s.text(1238,y,'—',18,MUT)
s.btn(869,658,215,'Купить билет')
s.text(103,758,'Описание программы · Условия участия · Доступная среда',18,TEXT)
s.end('09_event')
# 10 article templates
s=Slide('Типовые внутренние страницы','Контентный шаблон для разделов «Музей» и «Наука»')
for x,title,nav in [(65,'Музей',['История музея','История здания','Экспозиция','Команда','Официальные документы']),
                      (735,'Наука',['Семинары','Публикации','Коллекция','Исследователям','Материалы по теме'])]:
 s.rect(x,169,641,649,BG,9,BORDER)
 s.rect(x+18,187,605,66,SOFT,6,None);s.text(x+32,226,'МУЗЕЙ ХЛЕБА',19,INK,700)
 s.text(x+32,284,'Главная / '+title,15,MUT)
 s.text(x+32,327,title,29,INK,700)
 s.rect(x+32,349,186,437,SOFT,6,None)
 for j,n in enumerate(nav):
  if n=='Официальные документы':
   s.text(x+45,392+j*59,'Официальные',15,TEXT);s.text(x+45,412+j*59,'документы',15,TEXT)
  else:s.text(x+45,392+j*59,n,15,TEXT)
 s.outline(x+235,349,370,180,'ИЗОБРАЖЕНИЕ')
 s.text(x+235,565,'Заголовок материала',20,INK,700)
 s.text(x+235,599,'Текст, иллюстрации',16,TEXT)
 s.text(x+235,626,'и документы раздела',16,TEXT)
 s.line(x+235,663,x+596,663)
 s.text(x+235,701,'Связанные материалы',16,ACC,700)
s.end('10_interiors')
# 11 forms actual UI vs text placeholder
s=Slide('Контакты и обращение','Информация о музее и формы, предусмотренные ТЗ')
s.rect(61,166,1318,656,BG,11,BORDER);s.site_header(78,181,1284)
s.text(103,329,'Контакты',31,INK,700)
s.rect(103,365,452,421,SOFT,8,None)
s.text(124,408,'Как связаться',22,INK,700)
s.lines(124,454,['Адрес музея','Часы работы','Телефон','Электронная почта'],17,56)
s.rect(580,365,768,421,BG,8,BORDER)
s.text(603,407,'Обратная связь',22,INK,700)
for i,(title,ph) in enumerate([('Ваше имя','Имя'),('Контакт для ответа','E-mail или телефон'),('Сообщение','Текст сообщения')]):
 y=436+i*84;s.text(604,y,title,15,INK,700)
 s.rect(604,y+12,717,54,SOFT,5,BORDER);s.text(620,y+47,ph,16,MUT)
s.rect(604,705,18,18,BG,3,BORDER);s.text(633,720,'Согласие на обработку персональных данных',15,TEXT)
s.btn(1140,737,182,'Отправить')
s.end('11_forms')
# 12 — Search states and autocomplete
s=Slide('Поиск по сайту','Поиск с автодополнением и понятными результатами — п. 2.2.3.6.2')
for x,number,title in [(67,'01','Ввод запроса'),(510,'02','Подсказки'),(953,'03','Результаты')]:
 s.rect(x,177,417,621,BG,9,BORDER)
 s.text(x+20,217,number,15,MUT,700)
 s.text(x+61,218,title,22,INK,700)
 s.line(x+20,240,x+396,240)
s.text(88,280,'Поиск',17,INK,700)
s.rect(88,300,372,54,SOFT,5,BORDER);s.text(108,335,'Введите запрос',16,MUT)
s.text(88,392,'Поиск доступен из шапки',17,TEXT)
s.text(88,424,'на любой странице сайта.',16,TEXT)
s.text(88,483,'Частые переходы',17,INK,700)
for i,t in enumerate(['Посетителям','Экскурсии','Новости','Контакты']):
 s.rect(88,504+i*53,371,44,SOFT,5,None);s.text(107,531+i*53,t,16,TEXT)
s.text(531,280,'Запрос',17,INK,700)
s.rect(531,300,370,53,SOFT,5,BORDER);s.text(551,333,'Экспозиция',16,TEXT)
s.rect(531,363,370,199,BG,7,BORDER)
for i,(t,d) in enumerate([('Экспозиция','Раздел музея'),('Выставки','Раздел сайта'),('Материалы по теме','Научные публикации')]):
 y=394+i*58;s.text(551,y,t,17,INK,700);s.text(551,y+22,d,14,MUT)
 if i<2:s.line(546,y+30,881,y+30)
s.text(531,600,'Подсказки ведут к страницам',16,TEXT)
s.text(531,628,'опубликованного сайта.',16,TEXT)
s.text(974,281,'Результаты по запросу',17,INK,700)
for i,(t,d) in enumerate([('Страница музея','Раздел / короткий фрагмент'),('Публикация','Наука / короткий фрагмент'),('Выставка','Выставки / короткий фрагмент')]):
 y=318+i*101;s.rect(974,y,370,87,SOFT,5,None);s.text(990,y+31,t,17,INK,700);s.text(990,y+57,d,14,MUT)
s.rect(974,648,370,109,BG,7,BORDER);s.text(990,681,'Если совпадений нет',17,INK,700)
s.text(990,710,'Предложить вернуться к',15,TEXT);s.text(990,731,'разделам и поиску.',15,TEXT)
s.end('12_search')
# 13 — Ticket journey
s=Slide('Путь к покупке билета','Пользовательская задача: попасть из музея в действующую билетную систему')
steps=[('01','Вход на сайт',['Кнопка «Купить билет»','в шапке всех страниц']),('02','Билеты и льготы',['Виды билетов, правила','и информация о возврате']),('03','Внешняя система',['Переход на билетного','оператора по ссылке']),('04','Оформление',['Покупка в интерфейсе','внешнего оператора'])]
for i,(num,name,body) in enumerate(steps):
 x=66+i*335;s.rect(x,231,308,234,SOFT,9,None);s.text(x+22,277,num,17,MUT,700)
 s.text(x+22,315,name,23,INK,700)
 s.lines(x+22,359,body,17,31)
 if i<3:s.text(x+314,350,'→',28,ACC,700)
s.text(68,534,'Что нужно уточнить на встрече',25,INK,700)
for i,(title,body) in enumerate([('Билетный оператор','Точный URL, способ передачи'),('Стоимость','Утверждённый прейскурант'),('Возвраты','Где описаны правила'),('Проверка сценария','Тест перехода на телефоне')]):
 x=66+i*335;s.rect(x,565,308,152,BG,8,BORDER);s.text(x+19,602,title,19,INK,700);s.text(x+19,637,body,16,TEXT)
s.end('13_tickets')
# 14 — Site header and footer mandatory global elements
s=Slide('Сквозные элементы интерфейса','Единая навигация, поиск, доступность и служебные ссылки')
s.text(69,196,'ШАПКА САЙТА',16,MUT,700)
s.rect(66,215,1307,213,BG,10,BORDER)
s.text(88,257,'Логотип  МУЗЕЙ ХЛЕБА',21,INK,700)
for x,label in [(435,'Музей'),(526,'Посетителям'),(688,'Афиша'),(786,'Экскурсии'),(922,'Детям'),(1005,'Выставки')]:
 s.text(x,257,label,15,TEXT)
s.btn(1208,230,144,'Купить билет')
s.line(87,284,1354,284)
for x,t in [(91,'Поиск по всему сайту'),(358,'Режим для слабовидящих'),(711,'Доступная среда'),(995,'VK / MAX и другие официальные сети')]:
 s.text(x,332,t,17,ACC,700)
s.text(91,389,'Меню закрепляется при прокрутке, подразделы раскрываются.',17,MUT)
s.text(69,472,'НИЖНЯЯ ЧАСТЬ САЙТА',16,MUT,700)
s.rect(66,491,1307,311,SOFT,10,None)
for x,title,body in [
 (90,'О музее',['Полное официальное наименование','Фактический адрес','Телефон, электронная почта','Часы работы']),
 (515,'Информация',['Политика конфиденциальности','Иные обязательные документы','Оценить работу музея','Переходы по разделам']),
 (940,'Связь',['Подписка на рассылку','Контакты и обратная связь','Ссылки на официальные соцсети'])]:
 s.text(x,542,title,23,INK,700);s.lines(x,588,body,17,41)
s.end('14_global')
# 15 — Accessibility mode and excursion request
s=Slide('Доступность и запись на экскурсию','Два независимых сценария: режим просмотра и обращение к музею')
s.rect(67,177,632,636,BG,9,BORDER)
s.text(91,222,'Режим для слабовидящих',24,INK,700)
s.text(91,257,'Настройки представления',17,MUT)
s.rect(91,283,577,91,SOFT,8,None)
s.text(110,322,'Размер текста',18,INK,700)
s.btn(440,298,100,'А+');s.btn(552,298,98,'А−',False)
s.rect(91,398,577,216,BG,8,BORDER)
s.text(114,441,'Заголовок крупным шрифтом',24,INK,700)
s.text(114,484,'Повышенный контраст, видимый фокус',18,TEXT)
s.text(114,518,'и управление с клавиатуры.',18,TEXT)
s.rect(115,554,22,22,BG,3,ACC,2);s.text(154,572,'Контрастная тема',17,TEXT)
s.text(91,676,'Проверка: Tab / Shift+Tab / Enter / Space',16,MUT)
s.rect(744,177,628,636,BG,9,BORDER)
s.text(768,222,'Заявка на экскурсию',24,INK,700)
s.text(768,255,'Отдельная форма от обратной связи',17,MUT)
for i,(name,value) in enumerate([('Программа','Выберите экскурсию'),('Дата посещения','Укажите желаемую дату'),('Контакт для ответа','E-mail или телефон'),('Комментарий','Дополнительная информация')]):
 y=290+i*87
 s.text(767,y,name,16,INK,700);s.rect(766,y+13,579,53,SOFT,6,BORDER);s.text(783,y+47,value,16,MUT)
s.rect(768,652,20,20,BG,3,ACC)
s.text(800,669,'Согласие на обработку данных',15,TEXT)
s.btn(1134,714,210,'Отправить')
s.end('15_accessibility_forms')


# 16 interview with well-spaced cards
s=Slide('Вопросы к интервью 6 ноября','Решения, необходимые для дальнейшей UX-разработки')
topics=[
 ('Аудитории',['Какая группа посетителей в приоритете?','Какие сценарии вызывают затруднения?']),
 ('Навигация',['Какие разделы чаще всего ищут?','Что вынести на главную страницу?']),
 ('Билеты и визит',['Какой билетный сервис используется?','Кто подтверждает тарифы и льготы?']),
 ('Афиша',['Нужны ли фильтры по дате и возрасту?','Как показывать архив событий?']),
 ('Контент',['Какие материалы и фото доступны?','Кто отвечает за первичное наполнение?']),
 ('Согласование',['Кто утверждает структуру и UX?','Как фиксируем замечания к макетам?'])
]
for i,(title,questions) in enumerate(topics):
 x=66+(i%2)*665;y=179+(i//2)*218
 s.rect(x,y,640,196,SOFT,9,None)
 s.text(x+23,y+45,title,23,INK,700)
 s.text(x+24,y+97,'01',14,MUT,700);s.text(x+59,y+97,questions[0],17,TEXT)
 s.text(x+24,y+145,'02',14,MUT,700);s.text(x+59,y+145,questions[1],17,TEXT)
s.end('16_questions')
# Export native master through VectorCraft; artwork stays editable (not embedded as raster)
cmd=[VC,'run','--cmd','file.new','--params',json.dumps({'name':'Музей хлеба - UX low-fi','width':W,'height':H,'units':'Pixels','artboards':len(pages),'artboardLayout':{'layout':'gridByRow','columns':3,'spacing':80},'backgroundContents':'white'},ensure_ascii=False)]
for i,p in enumerate(pages):cmd+=['--cmd','file.place','--params',json.dumps({'path':str(p),'at':[(i%3)*1520+720,(i//3)*980+450],'link':False},ensure_ascii=False)]
nat=R/'museum_lowfi_20261105.vectorcraft';pdf=R/'museum_lowfi_20261105.pdf'
cmd+=['--export',str(nat),'--export',str(pdf)]
print('READY',len(pages),flush=True)
res=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
print('EXPORT',res.returncode,res.stdout[-3000:],res.stderr[-1200:],flush=True)
if res.returncode:raise SystemExit(res.returncode)
print('SIZES',nat.stat().st_size,pdf.stat().st_size,flush=True)

