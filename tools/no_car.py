"""Проверенные по источникам поездки без машины. Данные — data/no_car.json."""
from pathlib import Path
import html, json, re
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
E = lambda s: html.escape(str(s), quote=True)
TRIPS = json.loads((ROOT / 'tools/data/no_car.json').read_text(encoding='utf-8'))
BY_SLUG = {p['slug']: p for p in TRIPS}
CHECKED = '17 ноября 2026'

def attributes(slug):
    p = BY_SLUG.get(slug)
    if not p:
        return ''
    minutes = f' data-walk-min="{p["walk_min"]}"' if p.get('walk_min') else ''
    return f' data-access="{p["access"]}"' + minutes

def badge(slug):
    p = BY_SLUG.get(slug)
    if not p:
        return ''
    text = 'От станции пешком' if p['access'] == 'walk' else 'Электричка + автобус'
    return f'<p class="nc-badge">Без машины · {text}</p>'

def filters():
    return ('<div class="zc-access-row"><label for="zc-access">Как добраться'
            '<select id="zc-access"><option value="all">Все места</option>'
            f'<option value="verified">Без машины: {len(TRIPS)} проверенных поездок</option>'
            '<option value="walk">От станции пешком</option><option value="transfer">С автобусом от станции</option></select></label>'
            '<label for="zc-walk">Пеший подход<select id="zc-walk"><option value="all">Любой / без оценки</option>'
            '<option value="20">До 20 минут по источнику</option></select></label></div>'
            '<p class="zg-note">Отмечены только поездки, дорогу к которым мы проверили по источникам. '
            'Минуты — ориентир из источника; с автобусом считаем подход от конечной остановки. '
            'При выборе времени места без оценки не показаны. '
            '<a href="bez-mashiny/">Дорога туда и обратно: вся подборка →</a></p>')

def links(p):
    return ' · '.join(f'<a href="{E(u)}" rel="noopener">{E(t)}</a>' for t,u in p['sources'])

def travel_html(p):
    steps = [('Из Москвы',p['outbound']),('От станции до места',p['walk']),('Обратно',p['return']),('Перед поездкой',p['notes'])]
    bus = (f'<p class="nc-links"><a href="{E(p["bus_out"])}">Автобус туда</a> · <a href="{E(p["bus_back"])}">Автобус обратно</a></p>') if p.get('bus_out') else ''
    if p['slug'] in ('klin','novyy-ierusalim'):
        query = 'Клинское подворье, Клин, Староямская 4' if p['slug']=='klin' else 'Музей Новый Иерусалим, Истра, Ново-Иерусалимская набережная 1'
        bus += f'<p><a href="https://yandex.ru/maps/?text={quote(query)}">Музей на карте →</a></p>'
    return ('<div class="nc-travel"><p class="nc-badge">Без машины · дорога проверена по источникам</p>'
            '<dl class="zg-get">'+''.join(f'<dt>{E(t)}</dt><dd>{E(v)}</dd>' for t,v in steps)+'</dl>'
            f'<p class="nc-links"><a href="{E(p["timetable_out"])}" rel="noopener">Расписание туда</a> · '
            f'<a href="{E(p["timetable_back"])}" rel="noopener">Расписание обратно</a></p>' + bus +
            f'<p class="zg-note">Проверено по источникам {CHECKED}; маршрут на месте не проверяли. '
            'Выберите дату поездки в расписании и проверьте остановку вашего поезда. Обратный рейс выберите до выезда: время последних отправлений зависит от даты.</p>'
            f'<p class="zg-note">Источники дороги: {links(p)}.</p></div>')

def enrich_place(page, slug):
    p=BY_SLUG.get(slug)
    if not p:return page
    if slug=='novyy-ierusalim':
        page=page.replace('>Маршрут на машине</a>','>К монастырю: на машине</a>').replace('>На электричке и автобусе</a>','>К монастырю: транспорт</a>')
        page=page.replace('до точки «Новый Иерусалим» на карте ниже.','до монастыря на карте ниже. Дорога к музею описана отдельно ниже.')
    page=re.sub(r'<link rel="stylesheet" href="../no-car.css[^\"]*">','',page)
    page=page.replace('</head>','<link rel="stylesheet" href="../no-car.css?v=20261117"></head>',1)
    if '<!--NO-CAR-TRAVEL-->' in page:
        return re.sub(r'<!--NO-CAR-TRAVEL-->.*?<!--NO-CAR-TRAVEL-END-->',
                      lambda m:'<!--NO-CAR-TRAVEL-->'+travel_html(p)+'<!--NO-CAR-TRAVEL-END-->',page,flags=re.S)
    # Обновляем прежнее описание дороги; сохраняем кнопки маршрутов и связи с районами.
    page=re.sub(r'(<section class="zg-sec"(?: id="[^"]*")?><h2>Как добраться</h2>.*?)<dl class="zg-get">.*?</dl>',
                lambda m:m[1]+'<!--NO-CAR-TRAVEL-->'+travel_html(p)+'<!--NO-CAR-TRAVEL-END-->',page,count=1,flags=re.S)
    # Повторный запуск: если старого dl уже нет, обновление выполняется внутри блока.
    if '<!--NO-CAR-TRAVEL-->' not in page:
        page=re.sub(r'(<section class="zg-sec"(?: id="[^"]*")?><h2>Как добраться</h2>.*?)(</section>)',
                    lambda m:m[1]+'<!--NO-CAR-TRAVEL-->'+travel_html(p)+'<!--NO-CAR-TRAVEL-END-->'+m[2],page,count=1,flags=re.S)
    return page

def promo():
    return ('<!--NO-CAR-PROMO--><section class="zg-sec nc-promo"><h2>На день без машины</h2>'
            f'<p>{len(TRIPS)} поездок на электричке: где выйти, как дойти до входа и как вернуться. '
            'Отдельно отмечены варианты с автобусом.</p><p><a href="bez-mashiny/">Выбрать поездку без машины →</a> · '
            '<a href="?access=verified#all">Показать на схеме и в каталоге →</a></p></section><!--NO-CAR-PROMO-END-->')

def collection_page(head, metrika):
    title=f'{len(TRIPS)} поездок из Москвы без машины на один день'
    desc='Поездки на электричке: станции, подход к музеям и центрам городов, обратная дорога, источники и ссылки на расписание.'
    page=head(title,desc,'https://www.mskatlas.ru/zagorod/bez-mashiny/','../../')
    page=page.replace('</head>','<link rel="stylesheet" href="../no-car.css?v=20261117"><script defer src="../navigation.js?v=20261115-nav"></script>'
                      '<meta property="og:image" content="https://www.mskatlas.ru/assets/og/zagorod.jpg"></head>',1)
    items=''.join(f'<a href="#{E(p["slug"])}">{E(p["name"])}</a>' for p in TRIPS)
    articles=''.join(f'<article class="zg-sec nc-trip" id="{E(p["slug"])}"><h2><a href="../{E(p["slug"])}/">{E(p["name"])}</a></h2>'
                     f'<p class="nc-station">{E(p["station"])} · {"пешком от станции" if p["access"]=="walk" else "с автобусом"}</p>'
                     +travel_html(p)+f'<a href="../{E(p["slug"])}/#route">Что посмотреть и маршрут по месту →</a></article>' for p in TRIPS)
    return page+f'''<main class="wrap"><nav class="crumb" aria-label="Навигация"><a href="../">За город</a> / Без машины</nav>
<header class="hero"><p class="eyebrow">Атлас Москвы · поездки на день</p><h1>{title}</h1>
<p>Города и музеи, к которым можно доехать на электричке. У каждой поездки — станция, подход до места и обратный путь. Две поездки требуют автобуса после поезда.</p></header>
<p class="zg-note">Дорога проверена по официальным источникам {CHECKED}, а не на месте. Расписания и условия посещения меняются. На день поездки выберите поезд туда и обратно заранее; проверяйте остановки, часы работы и билет в музей. На лесной тропе световой день особенно важен.</p>
<p><a href="../?access=verified#all">Все поездки без машины на схеме и с фильтрами →</a></p>
<nav class="nc-jumps" aria-label="Выбрать поездку">{items}</nav>{articles}
<footer class="zg-src"><p>Другие варианты: <a href="../">все места «За город»</a>. Источники и расписания приведены у каждой поездки.</p></footer></main>{metrika}</body></html>'''
