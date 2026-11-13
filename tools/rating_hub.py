"""Вкладка «Рейтинги» — одна страница reyting/: сразу ползунки «что важно вам» (их ставит my_rating.py) и как считаем.
Подборки «самые зелёные», «для семьи с детьми» и т. п. владелец убрал (13.11.2026): их адреса ведут на reyting/,
из sitemap они убраны, ссылки на них по всему сайту заменены одной ссылкой «Рейтинг районов».
Идемпотентно; запускать после life_block.py, перед my_rating.py.
"""
import glob, os, re, json
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUBS = ['luchshie-rayony', 'ekologiya', 'zelenye-rayony', 'deshevye-rayony', 'transport', 'dlya-semi-s-detmi']
L = json.load(open(f'{REPO}/tools/data/life_parts.json', encoding='utf-8'))

# 1. Страница reyting/: заголовок, ползунки (my_rating.py), как считаем
p = f'{REPO}/reyting/index.html'
s = open(p, encoding='utf-8').read()
m = re.search(r'(<main[^>]*>).*?(</main>)', s, re.S)
METHOD = ('<section class="rmeth"><h2>Как считаем</h2>'
          '<p>Каждый показатель оценён по своей шкале от 0 до 10 по настоящим данным, а не по месту среди районов. '
          'По умолчанию веса такие: метро, МЦК и МЦД — 20 %, экология — 20 %, школы, сады и поликлиники — 15 %, зелень и парки рядом с домом — 15 %, '
          'тишина (сколько домов далеко от магистралей и станций) — 10 %, на автомобиле (сколько жилья приходится на крупные дороги вокруг) — 5 %, '
          'без высоток (мало домов от 18 этажей) — 5 %, кафе и магазины — 5 %, спорт — 5 %. Ползунками вы меняете их под себя.</p>'
          f'<p>Плохое хорошим не перекрывается: если экология или метро вам важны, итог района не может быть выше их оценки плюс {L["cap_plus"]} балла — '
          'район у завода или без метро в лидеры не попадёт. Цена жилья в балл не входит — по ней можно отфильтровать.</p>'
          '<p>Откуда данные: экология — <a href="../ecology.html">вкладка «Экология»</a>, метро — <a href="../transport.html">«Транспорт»</a>, '
          'дороги — <a href="../roads.html">«На автомобиле»</a>, школы и поликлиники — <a href="../social.html">«Школы и поликлиники»</a>, '
          'зелень — <a href="../parks.html">«Парки и прогулки»</a>, тишина, высотки и парки рядом — дома из OpenStreetMap (кнопки на карте каждого района). '
          'Разбор балла по каждому району — на его странице.</p></section>'
          '<style>.rmeth{max-width:80ch;margin:28px 0 10px}.rmeth p{margin:0 0 12px}</style>')
HEAD = ('<header><h1>Рейтинг районов Москвы</h1><p class="lead">Выберите, что важно именно вам, — список из 125 районов пересчитается сразу. '
        'Можно ограничить цену метра.</p></header>')
s = s[:m.start()] + m.group(1) + HEAD + METHOD + m.group(2) + s[m.end():]
s = re.sub(r'<title>[^<]*</title>', '<title>Рейтинг районов Москвы: выберите, что важно вам</title>', s, count=1)
DESC = 'Рейтинг всех 125 районов Москвы под ваши приоритеты: метро, экология, школы, парки, тишина, пробки, цена метра. Подвиньте ползунки — список пересчитается.'
s = re.sub(r'(<meta name="description" content=")[^"]*', lambda x: x.group(1) + DESC, s, count=1)
s = re.sub(r'(<meta property="og:description" content=")[^"]*', lambda x: x.group(1) + DESC, s, count=1)
s = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda x: x.group(1) + 'Рейтинг районов Москвы: выберите, что важно вам', s, count=1)
open(p, 'w', encoding='utf-8').write(s)

# 2. Старые подборки — переадресация на reyting/
for sub in SUBS:
    d = f'{REPO}/reyting/{sub}'
    os.makedirs(d, exist_ok=True)
    open(f'{d}/index.html', 'w', encoding='utf-8').write(
        '<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8"><title>Рейтинг районов Москвы</title>'
        '<meta name="robots" content="noindex,follow"><link rel="canonical" href="https://www.mskatlas.ru/reyting/">'
        '<meta http-equiv="refresh" content="0; url=../"><script>location.replace("../")</script></head>'
        '<body><p>Рейтинг переехал: <a href="../">Рейтинг районов Москвы</a>.</p></body></html>')

# 3. sitemap без подборок
sp = f'{REPO}/sitemap.xml'
sm = open(sp, encoding='utf-8').read()
sm = re.sub(r'\s*<url><loc>https://www\.mskatlas\.ru/reyting/(?:' + '|'.join(SUBS) + r')/</loc>.*?</url>', '', sm, flags=re.S)
open(sp, 'w', encoding='utf-8').write(sm)

# 4. ссылки по сайту: «Рейтинги районов: лучшие, экология, …» -> одна ссылка; прочие ссылки на подборки -> reyting/
LIST = re.compile(r'(<a href="([^"]*?)reyting/">)Рейтинги районов</a>:(?:\s*(?:,|·)?\s*<a href="[^"]*?reyting/(?:' + '|'.join(SUBS) + r')/">[^<]*</a>)+')
ONE = re.compile(r'href="([^"]*?)reyting/(?:' + '|'.join(SUBS) + r')/"')
n = 0
for f in glob.glob(f'{REPO}/**/*.html', recursive=True):
    if '/reyting/' in f.replace(REPO, '') and any(f'/reyting/{x}/' in f for x in SUBS): continue
    t = open(f, encoding='utf-8').read()
    u = LIST.sub(lambda x: x.group(1) + 'Рейтинг районов: что важно вам</a>', t)
    u = ONE.sub(lambda x: f'href="{x.group(1)}reyting/"', u)
    if u != t:
        open(f, 'w', encoding='utf-8').write(u); n += 1
print('рейтинг: одна страница, подборки переадресованы, ссылок поправлено на страницах:', n)
