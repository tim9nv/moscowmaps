"""Блок «Балл для жизни: из чего сложился» на страницах районов (идемпотентно, <!--LIFE-SCORE-->).

Данные — tools/data/life_parts.json (пишет tools/gen_pages.py). Запускать после district_layout.py.
"""
import json, os, re, glob
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(f'{REPO}/tools/data/life_parts.json', encoding='utf-8'))
NAMES = [('tr', 'Метро, МЦК, МЦД'), ('roads', 'Дороги: пробки'), ('eco', 'Экология'), ('soc', 'Школы и поликлиники'), ('green', 'Зелень и парки рядом'), ('quiet', 'Тишина'), ('height', 'Без высоток'), ('live', 'Кафе и магазины'), ('sport', 'Спорт')]
LIMN = {'eco': 'экология', 'tr': 'метро и электрички'}
fmt = lambda v: f'{v:.1f}'.replace('.', ',')
CSS = ('<style>.lifeb{box-sizing:border-box;max-width:100%;border:1px solid var(--border,#27376B);padding:16px 18px;margin:16px 0}.lifeb h2{margin:0 0 4px!important}'
       '.lifeb .tot{font-size:15px;color:var(--muted);margin:0 0 12px}.lifeb .tot b{color:#FFD86B;font-size:22px;font-weight:600}'
       '.lifeb ul{list-style:none;margin:0;padding:0;max-width:640px}.lifeb li{display:grid;grid-template-columns:190px minmax(0,1fr) 40px 44px;gap:0 12px;align-items:center;padding:4px 0;font-size:15px}'
       '.lifeb .v{font-variant-numeric:tabular-nums;text-align:right}.lifeb .bar{height:8px;background:#1a2752}.lifeb .bar i{display:block;height:100%;background:#FFD86B}'
       '.lifeb .bar.low i{background:#F59AB0}.lifeb .w{color:var(--muted);font-size:13px;text-align:right}.lifeb .n{font-size:13.5px;color:var(--muted);margin:10px 0 0;max-width:72ch}'
       '@media (max-width:560px){.lifeb li{grid-template-columns:minmax(0,1fr) 40px 44px;gap:3px 10px}.lifeb .bar{grid-column:1/-1;grid-row:2}}</style>')
def block(sl):
    d = D['d'].get(sl)
    if not d: return ''
    rows = ''.join(f'<li><span>{n}</span><span class="bar{" low" if d["p"][k] < 3 else ""}"><i style="width:{d["p"][k] * 10:.0f}%"></i></span><span class="v">{fmt(d["p"][k])}</span><span class="w">{D["w"][k]} %</span></li>'
                   for k, n in NAMES if k in d['p'])
    note = (f'Без потолка вышло бы {fmt(d["raw"])}: балл ограничен, потому что {LIMN[d["lim"]]} здесь — слабое место '
            f'(итог не выше этого показателя плюс {D["cap_plus"]} балла). ') if d.get('lim') else ''
    return ('<!--LIFE-SCORE--><section class="lifeb">' + CSS + '<h2>Балл для жизни</h2>'
            f'<p class="tot"><b>{fmt(d["v"])}</b> из 10 · {d["rank"]}-е место из 125 районов</p><ul>{rows}</ul>'
            f'<p class="n">{note}Каждый показатель — от 0 до 10, справа его вес в общем балле. Цена жилья не учитывается. Тишина, высотность и «парки рядом» посчитаны по домам из OpenStreetMap (тишина — не замер шума, а расстояние до магистралей и станций; смотрите кнопки на карте района). «Дороги» — сколько квартир приходится на крупные дороги вокруг, <a href="../../roads.html">карта «Машиной»</a>. '
            '<a href="../../reyting/luchshie-rayony/">Весь рейтинг и как он считается →</a></p></section><!--LIFE-SCORE-END-->')
n = 0
for f in glob.glob(f'{REPO}/rayon/*/index.html'):
    sl = f.split('/')[-2]
    h = open(f, encoding='utf-8').read()
    h2 = re.sub(r'<!--LIFE-SCORE-->.*?<!--LIFE-SCORE-END-->', '', h, flags=re.S)
    b = block(sl)
    i = h2.find('</header>', h2.find('<h1'))   # шапка района, а не верхнее меню
    if b and i > 0:
        h2 = h2[:i + 9] + b + h2[i + 9:]; n += 1
    if h2 != h: open(f, 'w', encoding='utf-8').write(h2)
print('балл для жизни: блок на', n, 'страницах районов')
