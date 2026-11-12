#!/usr/bin/env python3
"""Вид «атлас, а не дашборд» (идемпотентно). Запускать после night_theme.py, перед seo_fix.py.

Блок <!--ATLAS-STYLE-->…<!--ATLAS-STYLE-END--> в конце <head> всех страниц:
- шрифты (свои файлы в assets/fonts, кириллица + латиница): Literata — заголовки, IBM Plex Sans — текст,
  Fira Sans Extra Condensed — подписи, ярлыки, меню; цифры табличные;
- без «таблеток» и прыгающих карточек: скругления 0–4 px, ховер — жёлтое подчёркивание;
- списки-указатели вместо плашек; карта в рамке листа с колофоном.
Плюс переключатель «В Москве / За городом» на главной и в хабе «За город» (блок <!--WHERE-->).
Цвета «ночного неба» не меняются.
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

FONTS = [('Literata', 'literata', ((300, 'normal'), (400, 'normal'), (400, 'italic'))),
         ('IBM Plex Sans', 'ibm-plex-sans', ((400, 'normal'), (500, 'normal'), (600, 'normal'))),
         ('Fira Sans Extra Condensed', 'fira-sans-extra-condensed', ((500, 'normal'), (600, 'normal')))]
LAT = 'U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD'
CYR = 'U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116'


def face(pre):
    out = []
    for fam, f, vs in FONTS:
        for w, st in vs:
            for sub, rng in (('cyrillic', CYR), ('latin', LAT)):
                out.append(f'@font-face{{font-family:"{fam}";font-style:{st};font-weight:{w};font-display:swap;'
                           f'src:url({pre}assets/fonts/{f}-{sub}-{w}-{st}.woff2) format("woff2");unicode-range:{rng}}}')
    return ''.join(out)


CSS = r'''
:root{--display:"Literata",Georgia,"Times New Roman",serif;--body:"IBM Plex Sans",system-ui,-apple-system,"Segoe UI",sans-serif;--label:"Fira Sans Extra Condensed","Arial Narrow",sans-serif;--gold:#FFD86B}
html body{font-family:var(--body)!important;font-feature-settings:"kern"}
body h1,body h2,body h3,.hero h1,.wrap>header>h1{font-family:var(--display)!important;font-weight:400!important;letter-spacing:-.015em!important}
body h1{line-height:1!important}
body h2{font-size:clamp(22px,2.4vw,28px)!important;line-height:1.15}
body h3{font-size:19px!important;line-height:1.2}
.lede,.hero p:not(.eyebrow){font-family:var(--display);font-weight:300;line-height:1.5}
table,td,th,.v,.top6 b,.zg-facts,.meta,.stat .v{font-variant-numeric:tabular-nums lining-nums}
/* меню: подписи как на карте, активная вкладка — жёлтое подчёркивание */
.topbar .brand{font-family:var(--display)!important;font-weight:400!important;letter-spacing:-.01em}
.topbar .tabs a{font:500 14px/1 var(--label)!important;text-transform:uppercase;letter-spacing:.045em;border-radius:0!important;padding:9px 7px 7px!important;border-bottom:2px solid transparent}
.topbar .tabs a:hover{background:transparent!important;color:var(--gold)!important}
.topbar .tabs a[aria-current="page"]{background:transparent!important;color:var(--gold)!important;border-bottom-color:var(--gold)}
.topbar .go-out{border-radius:3px!important;font:600 14.5px/1 var(--label)!important;text-transform:uppercase;letter-spacing:.07em}
@media (max-width:600px){.topbar .in,.topbar .tabs{min-width:0}.topbar .tabs{overflow-x:auto;flex:1 1 auto}.topbar .go-out{letter-spacing:.02em!important;padding:7px 9px!important}.topbar .brand{flex:none}}
/* ярлыки над заголовками и подписи к цифрам */
.eyebrow,.stat .l,.tile .l,.hsearch label,.legend b,.zg-note b{font-family:var(--label)!important;font-weight:500!important;text-transform:uppercase;letter-spacing:.12em;font-size:13px!important}
/* без таблеток и прыгающих карточек */
.allr,.top6 .allr,.chips a,.chip,.chips button,.filters button,.park-links a,.zg-facts li,.hsearch .search,.search,input[type=search]{border-radius:3px!important}
.top6 b{border-radius:2px!important}
.hero,.card,.zg-card,.zg-promo,.top6 a,#park-list a,.stat,.tile,.nb,.scores>*,section.map,.leaflet-container,#zgmap,.pc>div,.faq details{border-radius:2px!important}
.zg-card:hover,.top6 a:hover,.nb:hover,#park-list a:hover{transform:none!important}
@media (hover:hover){.zg-card:hover h3,.nb:hover b,.top6 a:hover .nm,.top6 a:hover span:first-of-type{text-decoration:underline;text-decoration-color:var(--gold);text-underline-offset:4px;text-decoration-thickness:2px}}
/* «Лучшие для жизни» — указатель, а не стопка плашек */
.top6 ol{gap:0!important}
.top6 a{background:transparent!important;border:0!important;border-bottom:1px dotted var(--line,#27376B)!important;min-height:54px!important;padding:0 2px!important}
.top6 a>*:nth-child(2){font-family:var(--display);font-weight:400;font-size:19px}
.top6 a>*:first-child{font-family:var(--label);font-weight:500;color:var(--muted);font-variant-numeric:tabular-nums}
.top6 h2{font-size:22px!important}
.allr,.top6 .allr{background:transparent!important;color:var(--gold)!important;border:1px solid var(--gold)!important;font:600 14.5px/1 var(--label)!important;text-transform:uppercase;letter-spacing:.08em}
.zg-promo{background:transparent!important;border:1px solid var(--gold)!important}
/* карта — лист атласа: двойная рамка и колофон */
section.map{border:1px solid #3a4a80!important;outline:1px solid #27376B;outline-offset:5px;position:relative;overflow:hidden}
.atlas-home section.map::after{content:"Данные: OpenStreetMap, Росстат, Циан · ноябрь 2026";position:absolute;right:14px;top:10px;font:500 12px/1 var(--label);letter-spacing:.08em;text-transform:uppercase;color:#7f8fbf;pointer-events:none}
svg .lbl{font-family:var(--label)!important}
svg .lbl.okr{font-weight:600!important;font-size:13px!important;text-transform:uppercase}
section.map svg{overflow:hidden}
.atlas-home .wrap>header>.where,.atlas-home .wrap>.where{grid-column:1}

/* карта не «едет» при прокрутке — ни на главной, ни на вкладках (владелец, 12.11.2026). Главная на компьютере: сверху заголовок и крупный переключатель, ниже поиск и рейтинг слева, карта справа */
@media (min-width:1000px){
.wrap>.map{position:relative!important;top:auto!important}
.atlas-home .wrap>header>h1{grid-column:1;grid-row:1;margin-bottom:12px!important}
.atlas-home .wrap>header>.lede{grid-column:1;grid-row:2}
.atlas-home .wrap>.where{grid-column:2;grid-row:1/span 2;align-self:center;margin:0 0 8px;justify-self:stretch}
.atlas-home .wrap>.map{grid-row:3/span 12!important}
.atlas-home .where .q{font-size:20px}
}
.zg-hub .where{max-width:none!important}
/* «Где остаёмся?» */
.where{margin:6px 0 22px}
.where .q{font:italic 300 17px/1.3 var(--display);color:var(--muted);margin:0 0 10px}
.where .wsg{display:grid;grid-template-columns:1fr 1fr;border:1px solid #3a4a80;border-radius:2px;overflow:hidden}
.where .wsg a{display:block;padding:18px 20px 16px;color:var(--fg,#F2F5FF);text-decoration:none;min-height:44px}
.where .wsg a+a{border-left:1px solid #3a4a80}
.where .wsg b{display:block;font:400 clamp(26px,3vw,38px)/1.05 var(--display);letter-spacing:-.015em}
.where .wsg span{display:block;margin-top:8px;font:500 12.5px/1 var(--label);text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}
.where .wsg a[aria-current]{background:var(--gold);color:#0B1330}
.where .wsg a[aria-current] span{color:#3d3a26}
@media (hover:hover){.where .wsg a:not([aria-current]):hover b{text-decoration:underline;text-decoration-color:var(--gold);text-underline-offset:5px;text-decoration-thickness:2px}}
.zg-hub .hero .eyebrow{display:none}
.zg-hub .where{max-width:480px;margin-top:22px}
'''


def block(pre):
    return ('<!--ATLAS-STYLE--><link rel="preload" href="' + pre + 'assets/fonts/literata-cyrillic-400-normal.woff2" as="font" type="font/woff2" crossorigin>'
            '<style>' + face(pre) + re.sub(r'\s*\n\s*', '', CSS) + '</style><!--ATLAS-STYLE-END-->')


def where(pre, here):
    a = 'aria-current="page" '
    return ('<!--WHERE--><nav class="where" aria-label="Где остаёмся"><p class="q">Где остаёмся?</p><div class="wsg">'
            f'<a {a if here == "msk" else ""}href="{pre}"><b>В Москве</b><span>125 районов: цены, экология, школы</span></a>'
            f'<a {a if here == "out" else ""}href="{pre}zagorod/"><b>За городом</b><span>30 мест на день и выходные</span></a>'
            '</div></nav><!--WHERE-END-->')


# Порядок вкладок (владелец, 12.11.2026): районы и рейтинги — главное; климат рядом с экологией;
# «Новая Москва» из меню убрана — ссылка на неё в разделе «За город».
NAV_ORDER = ['Районы', 'Рейтинги', 'Цены', 'Экология', 'Климат и рельеф', 'Транспорт', 'Школы и поликлиники', 'Парки и прогулки']


def nav_fix(s):
    m = re.search(r'(<nav class="tabs"[^>]*>)(.*?)(</nav>)', s, re.S)
    if not m:
        return s
    links = {re.sub('<[^>]+>', '', a): a for a in re.findall(r'<a[^>]*>.*?</a>', m.group(2), re.S)}
    if not all(k in links for k in NAV_ORDER):
        return s
    return s[:m.start(2)] + ''.join(links[k] for k in NAV_ORDER) + s[m.end(2):]


def main():
    n = 0
    files = sorted(set(glob.glob('*.html') + glob.glob('*/index.html') + glob.glob('*/*/index.html')))
    for f in files:
        if os.path.basename(f).startswith(('yandex_', 'google')):
            continue
        s0 = s = open(f, encoding='utf-8').read()
        if '</head>' not in s:
            continue
        pre = '../' * f.count('/')
        s = nav_fix(s)
        s = re.sub(r'<!--ATLAS-STYLE-->.*?<!--ATLAS-STYLE-END-->', '', s, flags=re.S)
        # старые шрифты больше не грузим
        s = re.sub(r'<link[^>]*fonts\.googleapis\.com/css2\?family=Unbounded[^>]*>\s*', '', s)
        s = s.replace('</head>', block(pre) + '</head>', 1)
        s = re.sub(r'<!--WHERE-->.*?<!--WHERE-END-->', '', s, flags=re.S)
        # на главной переключатель стоит в шаблоне assets/atlas.js (класс .where)
        if f == 'zagorod/index.html':
            s = s.replace('<body>', '<body class="zg-hub">', 1) if '<body>' in s else s
            s = re.sub(r'(<header class="hero[^"]*">.*?</header>)', lambda m: m.group(1) + where('../', 'out'), s, count=1, flags=re.S)
        if s != s0:
            open(f, 'w', encoding='utf-8').write(s)
            n += 1
    print('atlas_style: страниц', n)


if __name__ == '__main__':
    main()
