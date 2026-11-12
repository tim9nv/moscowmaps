#!/usr/bin/env python3
"""Картинки для соцсетей (og:image, 1200×630) → assets/og/*.jpg.

Главная и вкладки — снимок самой страницы (заголовок слева, карта справа).
Рейтинги и «За город» — карточка в стиле сайта: заголовок и рисунок из шапки страницы.
Нужны playwright, Chrome и Pillow. Запуск из корня: python3 tools/og_images.py  (потом tools/seo_fix.py пропишет og:image).
"""
import asyncio, html, io, os, re, subprocess, sys, time
from PIL import Image
from playwright.async_api import async_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets/og')
PORT = 8799
B = f'http://localhost:{PORT}/'
D3 = '/opt/npm-tools/node_modules/d3/dist/d3.min.js'

PAGES = {'home': 'index.html', 'housing': 'housing.html', 'ecology': 'ecology.html', 'transport': 'transport.html',
         'social': 'social.html', 'parks': 'parks.html', 'sport': 'sport.html', 'climate': 'climate.html',
         'new-moscow': 'new-moscow.html'}

CARD = '''<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;width:1200px;height:630px;background:#070D22;font-family:"Golos Text",system-ui,sans-serif}
.c{position:absolute;inset:36px;border-radius:28px;background:#13235A;display:grid;grid-template-columns:1.25fr 1fr;align-items:center;padding:0 56px;overflow:hidden}
.e{color:#FFD86B;font:700 22px/1 system-ui;letter-spacing:.12em;text-transform:uppercase;margin:0 0 22px}
h1{color:#F2F5FF;font:800 {fs}px/1.02 system-ui;letter-spacing:-.04em;margin:0 0 22px}
p{color:#B4C1E4;font:500 26px/1.35 system-ui;margin:0}
svg{width:100%;height:auto;color:#F2E6C4}
.u{position:absolute;right:60px;bottom:52px;color:#8BEAB5;font:600 22px/1 system-ui}
</style></head><body><div class="c"><div><p class="e">{eyebrow}</p><h1>{title}</h1><p>{sub}</p></div><div>{art}</div></div><div class="u">mskatlas.ru</div></body></html>'''


def card_html(eyebrow, title, sub, art):
    fs = 84 if len(title) <= 14 else 68 if len(title) <= 24 else 56
    return (CARD.replace('{fs}', str(fs)).replace('{eyebrow}', html.escape(eyebrow))
            .replace('{title}', html.escape(title)).replace('{sub}', html.escape(sub)).replace('{art}', art))


def hero(path):
    s = open(os.path.join(ROOT, path), encoding='utf-8').read()
    h1 = html.unescape(re.sub('<[^>]+>', '', re.search(r'<h1>(.*?)</h1>', s, re.S).group(1)))
    m = re.search(r'<header class="hero[^"]*">.*?(<svg class="hero-art".*?</svg>)', s, re.S)
    eb = re.search(r'<p class="eyebrow">(.*?)</p>', s, re.S)
    return h1, (m.group(1) if m else ''), html.unescape(re.sub('<[^>]+>', '', eb.group(1))) if eb else ''


def save(png, name):
    im = Image.open(io.BytesIO(png)).convert('RGB').resize((1200, 630))
    im.save(os.path.join(OUT, name + '.jpg'), quality=84, optimize=True, progressive=True)


async def main():
    os.makedirs(OUT, exist_ok=True)
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    d3 = open(D3).read() if os.path.exists(D3) else None
    try:
        async with async_playwright() as p:
            b = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox'])
            ctx = await b.new_context(viewport={'width': 1200, 'height': 630}, device_scale_factor=1)

            async def rt(route):
                u = route.request.url
                if u.startswith(B): await route.continue_()
                elif d3 and 'd3' in u and u.endswith('.js'): await route.fulfill(body=d3, content_type='application/javascript')
                else: await route.abort()
            await ctx.route('**/*', rt)
            pg = await ctx.new_page()
            for name, path in PAGES.items():
                await pg.goto(B + path, wait_until='load'); await pg.wait_for_timeout(2500)
                await pg.evaluate("document.querySelectorAll('.go-out').forEach(e=>e.style.visibility='hidden')")
                save(await pg.screenshot(), name)
            # карточки
            items = [('reyting', 'Атлас Москвы', 'Рейтинги районов Москвы', 'Лучшие для жизни, экология, зелень, цены и транспорт — все 125 районов', None)]
            h1, art, _ = hero('zagorod/index.html')
            items.append(('zagorod', 'Атлас Москвы · за город', 'Куда поехать из Москвы', 'На день или выходные: как добраться, маршрут, где поесть', art))
            for d in sorted(os.listdir(os.path.join(ROOT, 'zagorod'))):
                f = os.path.join('zagorod', d, 'index.html')
                if os.path.exists(os.path.join(ROOT, f)):
                    h1, art, eb = hero(f)
                    items.append(('zagorod-' + d, eb or 'За город', h1, 'Как добраться из Москвы, маршрут, где поесть', art))
            for name, eb, t, sub, art in items:
                await pg.set_content(card_html(eb, t, sub, art or ''))
                await pg.wait_for_timeout(150)
                save(await pg.screenshot(), name)
            await b.close()
    finally:
        srv.terminate()
    print('og-картинок:', len(os.listdir(OUT)))


asyncio.run(main())
