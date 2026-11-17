"""Обновить только подборку, каталог и дорогу 8 мест без пересборки остальных страниц.

python tools/refresh_no_car.py. Полная сборка build_zagorod.py включает эти же изменения.
"""
from pathlib import Path
import re
from no_car import TRIPS, enrich_place, promo, collection_page
from atlas_style import block

ROOT=Path(__file__).resolve().parents[1]
generator=ROOT/'tools/build_zagorod.py'
scope={'__file__':str(generator)}
source=generator.read_text(encoding='utf-8').split("os.makedirs(f'{REPO}/zagorod', exist_ok=True)")[0]
exec(compile(source,str(generator),'exec'),scope)
hub=ROOT/'zagorod/index.html'
page=hub.read_text(encoding='utf-8')
page,count=re.subn(r'(<section class="zg-sec zg-cat" id="all"><h2>Все места</h2>).*?(</section>)',lambda m:m[1]+scope['catalog_html']()+m[2],page,count=1,flags=re.S)
assert count==1
page=re.sub(r'<!--NO-CAR-PROMO-->.*?<!--NO-CAR-PROMO-END-->','',page,flags=re.S)
page,count=re.subn(r'(<p class="zc-jump">.*?</p>)',lambda m:m[1]+promo(),page,count=1,flags=re.S)
assert count==1
hub.write_text(page,encoding='utf-8')
for p in TRIPS:
    path=ROOT/'zagorod'/p['slug']/'index.html'
    before=path.read_text(encoding='utf-8')
    after=enrich_place(before,p['slug'])
    assert enrich_place(after,p['slug'])==after,p['slug']
    path.write_text(after,encoding='utf-8')
page=collection_page(scope['head'],scope['METRIKA'])
reference=(ROOT/'zagorod/abramtsevo/index.html').read_text(encoding='utf-8')
header=re.search(r'<header class="topbar">.*?</header>',reference,re.S)[0]
page=re.sub(r'<header class="topbar">.*?</header>',lambda m:header,page,count=1,flags=re.S)
page=page.replace('</head>',block('../../')+'</head>',1)
path=ROOT/'zagorod/bez-mashiny/index.html'
path.parent.mkdir(exist_ok=True)
path.write_text(page,encoding='utf-8')
path=ROOT/'sitemap.xml'
sm=path.read_text(encoding='utf-8')
url='https://www.mskatlas.ru/zagorod/bez-mashiny/'
if '<loc>'+url+'</loc>' not in sm:
    sm=sm.replace('</urlset>',f'  <url><loc>{url}</loc><lastmod>2026-11-17</lastmod></url>\n</urlset>')
path.write_text(sm,encoding='utf-8')
print('Обновлены каталог, подборка и дорога',len(TRIPS),'мест')
