"""Прогулки по паркам: маршрут по связным дорожкам из выгрузки троп (parks/catalog/trails-*.txt).
Запуск: python3 tools/build_park_walks.py  ->  parks/catalog/walks.json
Остановки заданы вручную (WALKS): название, широта, долгота (центр объекта в OpenStreetMap), короткая подпись.
Линия строится кратчайшим путём по графу дорожек между соседними остановками; на месте маршруты не проверялись.
Методика подбора остановок — tools/park-routes.md.
"""
import json, gzip, base64, math, heapq, os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = f'{REPO}/parks/catalog'
WALKS = {
 '7': dict(id='rozarii-i-prudy', name='От главного входа к розарию и прудам', loop=True,
   description='Круг по парадной части парка: фонтан, Малый розарий, Собачий и Золотой пруды. Ровные аллеи, подходит для коляски.',
   stops=[('Главный вход', 55.79251, 37.677007, 'Со стороны метро «Сокольники», 10 минут пешком по Сокольническому Валу.'),
          ('Фонтанная площадь', 55.794712, 37.676545, 'Центр парка: отсюда лучами расходятся аллеи.'),
          ('Малый розарий', 55.797094, 37.676793, 'Сад за оградой, вход свободный.'),
          ('Собачий пруд', 55.797179, 37.681289, 'Небольшой пруд в стороне от главных аллей.'),
          ('Золотой пруд', 55.798259, 37.664475, 'Пруд в западной части парка.')]),
 '19': dict(id='gosudarev-dvor', name='Государев двор и церковь Вознесения', loop=True,
   description='Главное в Коломенском за одну прогулку: от Спасских ворот через Государев двор к шатровой церкви над рекой.',
   stops=[('Спасские ворота', 55.669343, 37.665792, 'Вход со стороны метро «Коломенская».'),
          ('Церковь Казанской иконы Божией Матери', 55.668689, 37.667794, 'Действующий храм XVII века.'),
          ('Домик Петра I', 55.667355, 37.667114, 'Деревянный дом, перевезённый из Архангельска. Внутри музей.'),
          ('Половецкая баба', 55.667082, 37.66831, 'Каменная скульптура под открытым небом.'),
          ('Передние ворота', 55.667606, 37.669425, 'Парадный въезд Государева двора.'),
          ('Церковь Вознесения Господня', 55.667295, 37.670719, 'Шатровый храм 1532 года на берегу Москвы-реки, объект ЮНЕСКО.'),
          ('Водовзводная башня', 55.66688, 37.670041, 'Башня XVII века рядом с церковью Георгия Победоносца.'),
          ('Борисов камень', 55.66805, 37.665938, 'Камень с надписью XII века.')]),
 '8': dict(id='dvortsy-i-mosty', name='Дворцы, мосты и павильоны', loop=True,
   description='От Фигурного моста к Большому дворцу и Хлебному дому, затем по пейзажному парку к павильонам над прудом.',
   stops=[('Фигурный мост', 55.616454, 37.680763, 'Парадный въезд в ансамбль со стороны метро «Царицыно».'),
          ('Хлебный дом', 55.616032, 37.684398, 'Кухонный корпус, сейчас музей.'),
          ('Большой дворец', 55.615486, 37.682146, 'Главное здание ансамбля. Вход в музей по билетам.'),
          ('Малый дворец', 55.615362, 37.680584, 'Небольшой дворец на склоне к пруду.'),
          ('Оперный дом', 55.614828, 37.68025, 'Средний дворец.'),
          ('Виноградные ворота', 55.614206, 37.68082, 'Ворота в пейзажный парк.'),
          ('Павильон «Миловида»', 55.612329, 37.681621, 'Павильон с видом на Верхний пруд.'),
          ('Беседка «Храм Цереры»', 55.608873, 37.687568, 'Беседка-ротонда в дальней части парка.'),
          ('Павильон «Нерастанкино»', 55.611111, 37.687372, 'Павильон на высоком берегу.')]),
# Парк Горького: в выгрузке троп нет сети у главного входа (площади партера размечены полигонами), маршрут не строится.
}
def dist(a, b):
    return 6371000 * math.hypot(math.radians(b[1] - a[1]) * math.cos(math.radians((a[0] + b[0]) / 2)), math.radians(b[0] - a[0]))
parks = {p['id']: p for p in json.load(open(f'{CAT}/parks.json', encoding='utf-8'))}
out = {}
for pid, w in WALKS.items():
    rec = json.loads(gzip.decompress(base64.b64decode(open(f'{CAT}/trails-{parks[pid]["group"]}.txt').read())))[pid]
    G = {}
    for kind, lines in rec['t'].items():
        cost = 3 if kind == 'steps' else (1.15 if kind in ('unpaved', 'unknown') else 1)   # ступени и грунт — только если иначе далеко
        for ln in lines:
            for a, b in zip(ln, ln[1:]):
                a, b = tuple(a), tuple(b); d = dist(a, b)
                G.setdefault(a, []).append((b, d, d * cost)); G.setdefault(b, []).append((a, d, d * cost))
    nodes = list(G)
    # берём только самую большую связную часть сети, чтобы не привязать остановку к обрывку дорожки
    seen = {}; comp = 0
    for n in nodes:
        if n in seen: continue
        comp += 1; st = [n]; seen[n] = comp
        while st:
            x = st.pop()
            for y, _, _ in G[x]:
                if y not in seen: seen[y] = comp; st.append(y)
    big = max(set(seen.values()), key=lambda c: sum(1 for v in seen.values() if v == c))
    main = [n for n in nodes if seen[n] == big]
    def snap(pt): return min(main, key=lambda n: dist(n, pt))
    def path(a, b):
        D = {a: 0}; prev = {}; pq = [(0, a)]
        while pq:
            d, x = heapq.heappop(pq)
            if x == b: break
            if d > D.get(x, 1e18): continue
            for y, real, c in G[x]:
                nd = d + c
                if nd < D.get(y, 1e18): D[y] = nd; prev[y] = x; heapq.heappush(pq, (nd, y))
        p = [b]
        while p[-1] != a: p.append(prev[p[-1]])
        return p[::-1]
    stops = w['stops'] + ([w['stops'][0]] if w['loop'] else [])
    snapped = [snap((s[1], s[2])) for s in stops]
    track = [list(snapped[0])]; metres = 0
    for a, b in zip(snapped, snapped[1:]):
        if a == b: continue
        seg = path(a, b)
        metres += sum(dist(x, y) for x, y in zip(seg, seg[1:]))
        track += [list(x) for x in seg[1:]]
    ids = [f'walk-{i + 1}' for i in range(len(w['stops']))]
    out[pid] = {
        'places': [{'id': ids[i], 'name': s[0], 'category': 'stop', 'lat': s[1], 'lon': s[2], 'description': s[3]} for i, s in enumerate(w['stops'])],
        'routes': [{'id': w['id'], 'name': w['name'], 'description': w['description'] + ' Линия построена по дорожкам OpenStreetMap, на месте не проверялась.',
                    'metres': round(metres), 'stops': ids + ([ids[0]] if w['loop'] else []), 'approaches': [list(x) for x in snapped], 'track': track}]}
    print(pid, parks[pid]['name'], round(metres), 'м;', 'до дорожки от остановок, м:', [round(dist(n, (s[1], s[2]))) for n, s in zip(snapped, stops)], 'частей сети:', comp)
json.dump(out, open(f'{CAT}/walks.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
