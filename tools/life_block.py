"""Блок «Балл для жизни: из чего сложился» на страницах районов (идемпотентно, <!--LIFE-SCORE-->).

Данные — tools/data/life_parts.json (пишет tools/gen_pages.py). Запускать после district_layout.py.
"""
import argparse
import json
import os
from pathlib import Path
import re
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(open(f'{REPO}/tools/data/life_parts.json', encoding='utf-8'))
NAMES = [('tr', 'На метро'), ('roads', 'На автомобиле'), ('eco', 'Экология'), ('soc', 'Школы и поликлиники'), ('green', 'Зелень и парки рядом'), ('quiet', 'Тишина'), ('height', 'Без высоток'), ('live', 'Кафе и магазины'), ('sport', 'Спорт')]
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
            f'<p class="n">{note}Каждый показатель — от 0 до 10, справа его вес в общем балле. Цена жилья не учитывается. Тишина, высотность и «парки рядом» посчитаны по домам из OpenStreetMap (тишина — не замер шума, а расстояние до магистралей и станций; смотрите кнопки на карте района). «На автомобиле» — сколько квартир приходится на крупные дороги вокруг, <a href="../../roads.html">карта «На автомобиле»</a>. '
            '<a href="../../reyting/">Рейтинг районов: что важно вам →</a></p></section><!--LIFE-SCORE-END-->')
def insert_block(page, slug):
    score = block(slug)
    if not score:
        return page
    content = re.sub(r'<!--LIFE-SCORE-->.*?<!--LIFE-SCORE-END-->', '', page, flags=re.S)
    header = content.find('</header>', content.find('<h1'))
    if header < 0:
        return page
    end = header + len('</header>')
    if slug == 'otradnoe':
        # Отрадное — образец новой раскладки районных страниц.
        district_map = re.search(r'<section class="map"[^>]*>.*?</section>', content[end:], re.S)
        if not district_map or 'id="dm"' not in district_map[0]:
            raise ValueError('Карта Отрадного не найдена')
        tail = content[end:]
        return (content[:end] + '\n' + district_map[0] + '\n' + score
                + tail[:district_map.start()] + tail[district_map.end():].lstrip('\n'))
    return content[:end] + score + content[end:]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--district', choices=sorted(D['d']))
    args = parser.parse_args()
    root = Path(REPO) / 'rayon'
    paths = [root / args.district / 'index.html'] if args.district else sorted(root.glob('*/index.html'))
    changed = 0
    for path in paths:
        original = path.read_text(encoding='utf-8')
        updated = insert_block(original, path.parent.name)
        if updated != original:
            path.write_text(updated, encoding='utf-8', newline='\n')
            changed += 1
    print('Балл для жизни: обновлено страниц', changed)
