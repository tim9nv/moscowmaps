"""Порядок блоков и мелкие правки текста на страницах районов (идемпотентно).
Запускать после gen_pages.py и build_park_pages.py, до night_theme.py:
    python3 tools/district_layout.py
- главное сверху: жильё и транспорт, школы, парки; ниже экология, спорт, вопросы, соседи;
  «Рельеф и микроклимат» — в самом низу, свёрнут;
- возраст домов (tools/data/house_age.json, OpenStreetMap) — карточка в «Жильё и транспорт»,
  только если год постройки известен хотя бы у половины домов района и у 30+ домов;
- «до станции 77 минут пешком» — пишем «пешком далеко»; нулевые спортивные карточки — «нет».
"""
import re, os, json, glob
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGE = json.load(open(f'{REPO}/tools/data/house_age.json', encoding='utf-8'))
FAR = 25
ORDER = ['Жильё', 'Школы', 'Парки района', 'Экология', 'Спорт', 'Частые вопросы', 'Соседние', 'Рельеф']
MONTHS = ['январь','февраль','март','апрель','май','июнь','июль','август','сентябрь','октябрь','ноябрь','декабрь']

def key(chunk):
    m = re.search(r'<h2[^>]*>([^<]*)', chunk)
    t = m.group(1) if m else ''
    for i, k in enumerate(ORDER):
        if t.startswith(k): return i
    return 5.5

def age_card(slug):
    r = AGE['districts'].get(slug)
    if not r or r['dated'] < 30 or r['dated'] < r['all'] * 0.5: return ''
    b = r['bins']; k = max(range(len(b)), key=lambda i: b[i])
    share = round(b[k] / r['dated'] * 100)
    old = round(sum(b[:3]) / r['dated'] * 100)
    y, mo, _ = AGE['date'].split('-')
    period = AGE['bins'][k]
    v = period if period.startswith(('до', 'с ')) else f'{period} гг.'
    return (f'<!--HOUSE-AGE--><div class="stat"><div class="l">Чаще всего дома</div><div class="v">{v}</div>'
            f'<div class="s">{share} % жилых домов района · построено до 1981 года — {old} %</div></div><!--HOUSE-AGE-END-->', 
            f'<p class="small house-age-src">Возраст домов — годы постройки {r["dated"]} из {r["all"]} жилых домов района в OpenStreetMap ({MONTHS[int(mo)-1]} {y}).</p>')

def fix_text(h):
    def far(m):
        n = int(m.group(1))
        return f'ближайшая станция далеко — пешком в среднем {n} {m.group(2)}' if n > FAR else m.group(0)
    h = re.sub(r'до ближайшей станции в среднем (\d+) (минут[аы]?) пешком', far, h)
    def stat_far(m):
        return m.group(0) if int(m.group(1)) <= FAR else m.group(0).replace('пешком от типичной точки района', 'пешком, это далеко · от типичной точки района')
    h = re.sub(r'<div class="l">До станции</div><div class="v">(\d+) мин</div><div class="s">пешком от типичной точки района', stat_far, h)
    # нулевые спортивные карточки
    h = re.sub(r'(<div class="l">[^<]+</div>)<div class="v">0</div><div class="s">нет объектов · 0,0 на 10 тыс\.</div>',
               r'\1<div class="v">нет</div><div class="s">в районе таких объектов нет</div>', h)
    h = h.replace('Бассейнов в районе — 0, спортзалов', 'Бассейнов в районе нет, спортзалов')
    h = re.sub(r'спортзалов, клубов и катков — 0, ', 'спортзалов, клубов и катков нет, ', h)
    h = re.sub(r'<div class="s">([\d\u00a0 ]+) кафе и ресторанов · ([\d\u00a0 ]+) магазин[а-я]* ·', r'<div class="s">кафе и ресторанов: \1 · магазинов: \2 ·', h)
    return h

def process(path, slug):
    h = open(path, encoding='utf-8').read()
    o = h
    h = fix_text(h)
    # возраст домов
    h = re.sub(r'<!--HOUSE-AGE-->.*?<!--HOUSE-AGE-END-->', '', h, flags=re.S)
    h = re.sub(r'<p class="small house-age-src">.*?</p>', '', h, flags=re.S)
    card = age_card(slug)
    if card:
        i = h.find('<section><h2>Жильё и транспорт</h2>')
        if i >= 0:
            j = h.find('</div></div></div>', i) + len('</div></div>')  # конец последней карточки
            h = h[:j] + card[0] + h[j:]
            k = h.find('</section>', i)
            h = h[:k] + card[1] + h[k:]
    # порядок блоков
    a = h.find('<section class="map"')
    if a >= 0:
        a = h.find('</section>', a) + len('</section>')
        b = h.find('<p class="foot">', a)
        part = h[a:b]
        chunks = re.findall(r'(?:<!--DISTRICT-PARKS-->)?<section.*?</section>(?:<!--DISTRICT-PARKS-END-->)?', part, flags=re.S)
        if chunks and len(''.join(chunks)) >= len(part.replace('\n', '')) - 5:
            chunks.sort(key=key)
            out = []
            for c in chunks:
                if c.startswith('<section><h2>Рельеф'):
                    c = c.replace('<section><h2>Рельеф и микроклимат</h2>', '<section class="relief"><details><summary><h2>Рельеф и микроклимат</h2></summary>', 1)
                    c = c[:-len('</section>')] + '</details></section>'
                out.append(c)
            h = h[:a] + '\n' + '\n'.join(out) + '\n' + h[b:]
    # стиль свёрнутого блока
    css = '/*RELIEF*/.relief details{border:0;padding:0}.relief summary{cursor:pointer;list-style:none}.relief summary::-webkit-details-marker{display:none}.relief summary h2{display:inline}.relief summary h2::after{content:" ▾";color:var(--muted);font-size:.8em}.relief details[open] summary h2::after{content:" ▴"}/*RELIEF-END*/'
    h = re.sub(r'/\*RELIEF\*/.*?/\*RELIEF-END\*/', '', h, flags=re.S)
    h = h.replace('</style>', css + '</style>', 1)
    if h != o: open(path, 'w', encoding='utf-8').write(h); return 1
    return 0

n = 0
for p in sorted(glob.glob(f'{REPO}/rayon/*/index.html')):
    slug = p.split('/')[-2]
    if slug == 'gerb': continue
    n += process(p, slug)
print('изменено страниц:', n)

# рейтинги: на телефоне широкая таблица листается вбок — показываем подсказку, только если она правда не влезает
HINT = ('<!--SCROLL-HINT--><style>.scroll-hint{display:none;font-size:13px;color:var(--muted);margin:0 0 6px}.scroll-hint.on{display:block}</style>'
        '<p class="scroll-hint" id="sh">Таблица шире экрана — листайте её вбок →</p>'
        '<script>addEventListener("load",function(){var t=document.querySelector(".rtw"),h=document.getElementById("sh");if(t&&h&&t.scrollWidth>t.clientWidth+4){h.className="scroll-hint on";t.addEventListener("scroll",function(){h.className="scroll-hint"},{once:true})}})</script><!--SCROLL-HINT-END-->')
m = 0
for p in glob.glob(f'{REPO}/reyting/*/index.html'):
    h = open(p, encoding='utf-8').read(); o = h
    h = re.sub(r'<!--SCROLL-HINT-->.*?<!--SCROLL-HINT-END-->', '', h, flags=re.S)
    i = h.find('<section class="rtw"')
    if i >= 0: h = h[:i] + HINT + h[i:]
    if h != o: open(p, 'w', encoding='utf-8').write(h); m += 1
print('рейтингов с подсказкой:', m)
