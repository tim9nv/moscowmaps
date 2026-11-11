"""Ночная тема и широкая раскладка «слева заголовок и управление, справа карта» (с 10.11.2026).
Запуск: python3 tools/night_theme.py — идемпотентно: блоки NIGHT-THEME и WIDE-LAYOUT заменяются целиком.
Вешает data-theme="dark" на <html> (включает тёмные шкалы страниц), поверх — ночные цвета и звёзды.
"""
import glob, os, re, random, urllib.parse
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
random.seed(7)
st = ''.join(f'<circle cx="{random.randint(0,899)}" cy="{random.randint(0,899)}" r="{random.choice([.6,.6,.8,.8,1,1.3])}" fill="#fff" opacity="{random.choice([.35,.5,.5,.7,.9])}"/>' for _ in range(70))
STARS = "url('data:image/svg+xml," + urllib.parse.quote('<svg xmlns="http://www.w3.org/2000/svg" width="900" height="900">' + st + '</svg>') + "')"
NIGHT = ('/*NIGHT-THEME*/:root[data-theme="dark"]{--bg:#070D22;--surface:#0F1A3C;--fg:#F2F5FF;--muted:#B4C1E4;--line:#27376B;--soft:#16244D;'
         '--edge:#0F1A3C;--nodata:#2A3766;--rhalo:#0F1A3C;--nav-bg:#0A1230;--nav-fg:#F2F5FF;--nav-muted:#B4C1E4;--nav-line:#1F2D5C;--nav-hover:#16244D;--nav-accent:#FFD86B;'
         '--s1:#EC5B4C;--s2:#F5A04E;--s3:#F4D76E;--s4:#3DB88F;--s5:#8BEAB5;color-scheme:dark}'
         'body{background:#070D22}'
         '.topbar{background:rgb(10 18 48 / 92%);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px)}'
         '.topbar .tabs a[aria-current="page"]{background:#FFD86B;color:#0B1330}@media (min-width:1000px){.topbar .in{max-width:1240px}}'
         '::selection{background:#FFD86B;color:#0B1330}'
         'input,select,textarea{color-scheme:dark}'
         '.map .atlas-zoom{left:auto;right:12px}'   # кнопки масштаба справа: слева вверху вставка «ЗелАО» с подписью
         '/*NIGHT-THEME-END*/')
WIDE = ('/*WIDE-LAYOUT*/@media (min-width:1000px){'
        '.topbar .in{max-width:1240px}'
        '.wrap{max-width:1240px;display:grid;grid-template-columns:minmax(0,380px) minmax(0,1fr);grid-template-rows:repeat(11,auto) 1fr;column-gap:44px;row-gap:0;align-items:start}'
        '.wrap>*{grid-column:1/-1;order:5;margin-top:0;margin-bottom:24px}'
        '.wrap>header{display:contents}'
        '.wrap>header>*,.wrap>.L,.wrap>.filt,.wrap>.seg,.wrap>.geo-controls,.wrap>#card,.wrap>.card,.wrap>.atlas-zoom-hint{grid-column:1;order:1}'
        '.wrap>header>h1{order:0}.wrap>.walks{order:5}'
        '.wrap>header>h1{text-align:left;white-space:normal;font-size:clamp(44px,4.6vw,64px);letter-spacing:-.04em;line-height:1;margin:6px 0 18px}'
        '.wrap>header>.lede{margin:0 0 20px;font-size:17px}'
        '.wrap>.map{grid-column:2;grid-row:1/span 12;order:1;position:sticky;top:76px}'
        '.wrap>.map>svg{max-height:calc(100vh - 150px)}'
        '.wrap>.card{grid-template-columns:minmax(0,1fr)}.wrap>.card>*{min-width:0;grid-row:auto;grid-column:1/-1}.wrap>.card .score{grid-row:auto}'
        '.wrap:has(>.wrap){display:block}.wrap>.wrap{margin:0}'   # «Цены» и «Транспорт»: обёртка в обёртке
        '}/*WIDE-LAYOUT-END*/')
TABS = {'index.html', 'housing.html', 'ecology.html', 'transport.html', 'social.html', 'parks.html', 'sport.html', 'climate.html', 'new-moscow.html'}
def strip(s, a, b): return re.sub(re.escape(a) + r'.*?' + re.escape(b), '', s, flags=re.S)
n = 0
pages = [p for p in glob.glob(f'{REPO}/*.html') + glob.glob(f'{REPO}/rayon/**/index.html', recursive=True) + glob.glob(f'{REPO}/reyting/**/index.html', recursive=True)
         if '<nav class="tabs"' in open(p, encoding='utf-8').read()]
for p in pages:
    s = open(p, encoding='utf-8').read(); o = s
    s = re.sub(r'<html lang="ru"[^>]*>', '<html lang="ru" data-theme="dark">', s, count=1)
    s = strip(s, '/*NIGHT-THEME*/', '/*NIGHT-THEME-END*/'); s = strip(s, '/*WIDE-LAYOUT*/', '/*WIDE-LAYOUT-END*/'); s = strip(s, '/*STARS*/', '/*STARS-END*/')
    s = re.sub(r"\n?body\{background:#070D22 url\('data:image/svg\+xml,[^']*'\) repeat\}", '', s)   # старые строки без меток
    GOOD = ['#EC5B4C', '#F5A04E', '#F4D76E', '#3DB88F', '#8BEAB5']   # плохо → хорошо, яркие под синий фон
    base = os.path.basename(p) if os.path.dirname(p) == REPO else ''
    sc = GOOD[::-1] if base == 'ecology.html' else GOOD               # в экологии 1 = чисто
    scale = ':root[data-theme="dark"]{' + ''.join(f'--c{i+1}:{c};' for i, c in enumerate(sc)) + ''.join(f'--e{i+1}:{c};' for i, c in enumerate(GOOD[::-1])) + '}'
    tab = os.path.basename(p) in TABS and os.path.dirname(p) == REPO
    add = NIGHT.replace('/*NIGHT-THEME-END*/', scale + '/*NIGHT-THEME-END*/') + (WIDE + f'/*STARS*/body{{background:#070D22 {STARS} repeat}}/*STARS-END*/' if tab else '')   # звёзды только на страницах с картой: под длинным текстом они мешают читать
    i = s.rindex('</style>', 0, s.index('</head>')) if '</head>' in s and '</style>' in s[:s.index('</head>')] else s.rindex('</style>')   # стили темы — в шапке, не в блоках внутри страницы; s = s[:i] + add + '\n' + s[i:]
    h = s.find('</head>'); s = re.sub(r'\n{2,}', '\n', s[:h]) + s[h:] if h > 0 else s   # пустые строки от прошлых запусков
    if s != o: open(p, 'w', encoding='utf-8').write(s); n += 1
# парки: свой стиль guide.css
g = f'{REPO}/parks/vdnh/guide.css'; s = open(g, encoding='utf-8').read()
s = strip(s, '/*NIGHT-THEME*/', '/*NIGHT-THEME-END*/')
s += '\n' + '/*NIGHT-THEME*/:root{color-scheme:dark;--bg:#070D22;--surface:#0F1A3C;--ink:#F2F5FF;--muted:#B4C1E4;--border:#27376B;--green:#8BEAB5;--hero:#13235A;--onhero:#F2F5FF;--focus:#FFD86B}body{background:#070D22}.bar{background:#0A1230}.leaflet-tile-pane{filter:brightness(.9) saturate(.9)}.leaflet-container{background:#0A1230}::selection{{background:#FFD86B;color:#0B1330}}.leaflet-bar a,.leaflet-bar a:hover,.leaflet-touch .leaflet-bar a{background:#0F1A3C!important;color:#F2F5FF!important;border-color:#27376B!important}.leaflet-bar{border:1px solid #27376B!important}.leaflet-control-attribution,.leaflet-control-scale-line{background:rgb(10 18 48 / 85%)!important;color:#B4C1E4!important;border-color:#B4C1E4!important}.leaflet-control-attribution a{color:#8BEAB5!important}.leaflet-attribution-flag{display:none!important}/*NIGHT-THEME-END*/'   # светлая подложка (тёмная перевёрнутая владельцу не понравилась), без флажка Leaflet, ночные кнопки
open(g, 'w', encoding='utf-8').write(s)
print(n, 'страниц')
