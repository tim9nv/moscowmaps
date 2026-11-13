"""Выносит тяжёлые данные подробной карты района из assets/atlas.js в assets/atlas-detail.js.

Главной нужны только границы районов, крупная вода и крупные дороги; мелкие улицы (уровни 3–4),
подробная вода WATER_F и рельеф REL нужны только карте района (drawDMap) на rayon/<slug>/.
Так главная грузит ~1,6 МБ вместо ~4,3 МБ.

Страницы районов загружают d3 и atlas-detail.js, затем atlas.js (загрузчик — в gen_pages.py).
atlas.js без atlas-detail.js работает: мелких улиц и рельефа просто нет.

Запуск: python3 tools/split_atlas.py — идемпотентно (если данные уже вынесены, ничего не делает).
Если в atlas.js снова записали полные LAY/REL/WATER_F — запустить ещё раз.
"""
import json
import re

REPO = __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__)))
A = f'{REPO}/assets/atlas.js'
D = f'{REPO}/assets/atlas-detail.js'

s = open(A, encoding='utf-8').read()
if 'window.ATLAS_DETAIL' in s:
    print('split_atlas: уже разделено')
    raise SystemExit


def take(name):
    """Вырезает `const NAME = {...};` (или `, NAME = {...};` в конце строки) и возвращает (json, start, end)."""
    m = re.search(r'^const ' + name + r' = ', s, re.M) or re.search(r', ' + name + r' = ', s)
    st = m.start()
    en = s.index('\n', st)
    body = s[m.end():en].rstrip().rstrip(';')
    return json.loads(body), st, en


lay, l0, l1 = take('LAY')
rel, r0, r1 = take('REL')
wf, w0, w1 = take('WATER_F')

small = {k: v for k, v in lay.items() if k != 'roads'}
small['roads'] = [r for r in lay['roads'] if r[0] <= 2]
detail = {'roads': [r for r in lay['roads'] if r[0] > 2], 'WATER_F': wf, 'REL': rel}

dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
rep = {
    (l0, l1): 'const LAY = ' + dump(small) + ';\n'
              'if(window.ATLAS_DETAIL)LAY.roads=LAY.roads.concat(window.ATLAS_DETAIL.roads);',
    (r0, r1): 'const REL = window.ATLAS_DETAIL?window.ATLAS_DETAIL.REL:null;',
    (w0, w1): ', WATER_F = window.ATLAS_DETAIL?window.ATLAS_DETAIL.WATER_F:WATER_C;',  # объявлен через запятую после WATER_C
}
out = s
for (a, b), t in sorted(rep.items(), reverse=True):
    out = out[:a] + t + out[b:]

open(D, 'w', encoding='utf-8').write('/* Данные подробной карты района: мелкие улицы, вода, рельеф. Делает tools/split_atlas.py */\n'
                                     'window.ATLAS_DETAIL=' + dump(detail) + ';\n')
open(A, 'w', encoding='utf-8').write(out)
print(f'split_atlas: atlas.js {len(s.encode())//1024} → {len(out.encode())//1024} КБ, atlas-detail.js {len(open(D, encoding="utf-8").read().encode())//1024} КБ')
