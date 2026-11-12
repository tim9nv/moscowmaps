"""Схема «За город» для хаба: Москва в центре, лучи железнодорожных направлений, кольца расстояний.

Точка места стоит по настоящему направлению (азимут от центра Москвы) и на расстоянии по прямой,
радиус сжат корнем, чтобы Подмосковье и Углич поместились на одном листе. Это схема, а не карта:
так и подписано. Подключается из tools/build_zagorod.py (scheme_html).
"""
import html, math

C = (55.7520, 37.6175)  # Кремль
KMAX = 240              # край схемы, км
W, H = 1100, 760
CX, CY = W / 2, H / 2
RMAX = 350
MKAD_KM = 17.5          # средний радиус МКАД

TYPES = [  # ключ, подпись, цвет
    ('city', 'Города', '#FFD86B'),
    ('estate', 'Усадьбы', '#8BEAB5'),
    ('holy', 'Монастыри', '#F2C9A0'),
    ('museum', 'Музеи', '#9CC3FF'),
    ('nature', 'Природа', '#7FD6C2'),
    ('kids', 'С детьми и арт-парки', '#F59AB0'),
]
TYPE_OF = {
    'sergiev-posad': 'city', 'kolomna': 'city', 'zvenigorod': 'city', 'dmitrov': 'city', 'zaraysk': 'city',
    'serpuhov': 'city', 'borovsk': 'city', 'mozhaysk-borodino': 'city', 'egorevsk': 'city', 'klin': 'city',
    'pereslavl-zalesskiy': 'city', 'rostov-velikiy': 'city', 'uglich': 'city', 'tarusa-polenovo': 'city',
    'arhangelskoe': 'estate', 'abramtsevo': 'estate', 'melihovo': 'estate', 'muranovo': 'estate',
    'ostafevo': 'estate', 'serednikovo': 'estate', 'gorki-leninskie': 'estate',
    'novyy-ierusalim': 'holy', 'monino': 'museum', 'zubry': 'nature', 'senezh': 'nature',
    'etnomir': 'kids', 'kochevnik': 'kids', 'vorobi': 'kids', 'fermy': 'kids', 'nikola-lenivets': 'kids',
}
# направление вокзала — по городу на этой линии, к которому мы и так даём «как добраться»
RAYS = [('Ленинградское', 'klin'), ('Савёловское', 'dmitrov'), ('Ярославское', 'sergiev-posad'),
        ('Казанское', 'kolomna'), ('Павелецкое', 'gorki-leninskie'), ('Курское', 'serpuhov'),
        ('Киевское', 'borovsk'), ('Белорусское', 'mozhaysk-borodino'), ('Рижское', 'novyy-ierusalim')]
E = lambda s: html.escape(str(s), quote=True)


def km(a, b=C):
    k = math.cos(math.radians((a[0] + b[0]) / 2))
    return math.hypot((a[0] - b[0]) * 111.2, (a[1] - b[1]) * 111.2 * k)


def bearing(p):
    k = math.cos(math.radians(C[0]))
    return math.atan2((p[1] - C[1]) * k, p[0] - C[0])  # 0 = север, по часовой


def rad(d):
    return RMAX * (min(d, KMAX) / KMAX) ** 0.6


def xy(b, r):
    return CX + r * math.sin(b), CY - r * math.cos(b)


def scheme_html(places, hubpt):
    items = [dict(name=p['name'], href=p['slug'] + '/', ll=hubpt[p['slug']], t=TYPE_OF.get(p['slug'], 'city'),
                  tip=f"{p['name']} — {p['kind']}") for p in places]
    note = ('Схема, а не карта: место стоит в своём направлении от Москвы, а расстояние по прямой сжато, '
            'чтобы ближние усадьбы и Углич поместились на одном листе. Лучи — железнодорожные направления от московских вокзалов. '
            'Нажмите на точку, чтобы открыть страницу места.')
    return scheme_items(items, TYPES, hubpt, note)


def scheme_items(items, types, hubpt, note, uid='zs'):
    pts = []
    for it in items:
        ll = it['ll']
        d = km(ll)
        b = bearing(ll)
        x, y = xy(b, rad(d))
        pts.append(dict(p=it, d=d, b=b, x=x, y=y, t=it['t']))
    col = {k: c for k, _, c in types}
    o = [f'<svg class="zs" viewBox="0 0 {W} {H}" role="img" aria-labelledby="zs-t"><title id="zs-t">Схема: места за городом по направлениям от Москвы</title>']
    # кольца расстояний
    o.append('<g class="zs-rings">')
    for r_km in (50, 100, 150, 200):
        r = rad(r_km)
        o.append(f'<circle cx="{CX:.0f}" cy="{CY:.0f}" r="{r:.1f}"/>'
                 f'<text x="{CX + 4:.0f}" y="{CY - r - 5:.0f}">{r_km} км</text>')
    o.append('</g>')
    # лучи направлений
    o.append('<g class="zs-rays">')
    for i, (name, slug) in enumerate(RAYS):
        b = bearing(hubpt[slug])
        x0, y0 = xy(b, rad(MKAD_KM) + 4)
        x1, y1 = xy(b, RMAX + 6)
        lx, ly = xy(b, RMAX + 18)
        anchor = 'start' if math.sin(b) > 0.25 else 'end' if math.sin(b) < -0.25 else 'middle'
        o.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" style="--i:{i}"/>'
                 f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="{anchor}">{E(name)}</text>')
    o.append('</g>')
    # Москва
    rm = rad(MKAD_KM)
    o.append(f'<g class="zs-msk"><circle cx="{CX:.0f}" cy="{CY:.0f}" r="{rm:.1f}"/>'
             f'<text x="{CX:.0f}" y="{CY - 2:.0f}" text-anchor="middle">Москва</text>'
             f'<text class="s" x="{CX:.0f}" y="{CY + 15:.0f}" text-anchor="middle">внутри МКАД</text></g>')
    # подписи: пробуем справа и слева от точки и сдвиги по вертикали; не налезаем на другие подписи и точки
    dots = [(q['x'], q['y']) for q in pts]
    boxes, labels = [], []
    def free(x0, x1, y):
        if x0 < 4 or x1 > W - 4 or y < 14 or y > H - 4:
            return False
        if any(not (x1 < a or x0 > b2) and abs(y - yy) < 15 for a, b2, yy in boxes):
            return False
        return not any(x0 - 7 < dx < x1 + 7 and y - 16 < dy < y + 6 for dx, dy in dots)
    for q in sorted(pts, key=lambda q: q['d']):
        w = len(q['p']['name']) * 7.3 + 4
        pref = 'start' if q['x'] >= CX else 'end'
        best = None
        for dy in (0, -15, 15, -30, 30, -45, 45, -60, 60):
            for side in (pref, 'end' if pref == 'start' else 'start'):
                lx = q['x'] + 11 if side == 'start' else q['x'] - 11
                ly = q['y'] + 5 + dy
                x0, x1 = (lx, lx + w) if side == 'start' else (lx - w, lx)
                if free(x0, x1, ly):
                    best = (side, lx, ly, x0, x1); break
            if best: break
        if not best:
            side = pref; lx = q['x'] + 11 if side == 'start' else q['x'] - 11; ly = q['y'] + 5
            best = (side, lx, ly, *((lx, lx + w) if side == 'start' else (lx - w, lx)))
        side, lx, ly, x0, x1 = best
        boxes.append((x0, x1, ly))
        labels.append((q, side, lx, ly))
    o.append('<g class="zs-pts">')
    for n, (q, side, lx, ly) in enumerate(sorted(labels, key=lambda t: t[0]['d'])):
        p = q['p']
        c = col[q['t']]
        lead = ''
        if abs(ly - 5 - q['y']) > 3:
            lead = f'<path class="ld" d="M{q["x"]:.1f} {q["y"]:.1f}L{lx:.1f} {ly - 5:.1f}"/>'
        tip = f'{p["tip"]}, около {round(q["d"] / 5) * 5} км по прямой'
        o.append(f'<a href="{E(p["href"])}" class="zp" data-t="{q["t"]}" style="--d:{n}">'
                 f'<title>{E(tip)}</title>{lead}'
                 f'<circle class="h" cx="{q["x"]:.1f}" cy="{q["y"]:.1f}" r="14"/>'
                 f'<circle class="dot" cx="{q["x"]:.1f}" cy="{q["y"]:.1f}" r="6" style="fill:{c}"/>'
                 f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{side}">{E(p["name"])}</text></a>')
    o.append('</g></svg>')
    legend = ''.join(f'<button type="button" class="zs-f" data-t="{k}" aria-pressed="true"><i style="background:{c}"></i>{E(lbl)}</button>'
                     for k, lbl, c in types if any(q['t'] == k for q in pts))
    css = ('<style>'
           '.zs-wrap{position:relative;border:1px solid #3a4a80;outline:1px solid #27376B;outline-offset:5px;background:#0A1230;padding:14px 10px 6px;margin-top:6px}'
           '.zs{display:block;width:100%;height:auto;font-family:var(--label,"Arial Narrow",sans-serif)}'
           '.zs-rings circle{fill:none;stroke:#27376B;stroke-dasharray:2 5}.zs-rings text{fill:#6f80b3;font-size:12px;letter-spacing:.08em}'
           '.zs-rays line{stroke:#3a4a80;stroke-width:1.5;stroke-dasharray:420;stroke-dashoffset:420;animation:zsdraw 1.1s cubic-bezier(.23,1,.32,1) forwards;animation-delay:calc(var(--i)*60ms)}'
           '.zs-rays text{fill:#8f9fd0;font-size:12.5px;letter-spacing:.1em;text-transform:uppercase}'
           '.zs-msk circle{fill:#13235A;stroke:#F2F5FF;stroke-width:1.5}.zs-msk text{fill:#F2F5FF;font:400 19px var(--display,Georgia,serif)}.zs-msk text.s{font:500 11px var(--label,sans-serif);letter-spacing:.12em;text-transform:uppercase;fill:#B4C1E4}'
           '.zp{cursor:pointer;opacity:0;animation:zsin .5s cubic-bezier(.23,1,.32,1) forwards;animation-delay:calc(400ms + var(--d)*28ms)}'
           '.zp text{fill:#E6EBFA;font-size:14px;font-weight:500;letter-spacing:.02em;paint-order:stroke;stroke:#0A1230;stroke-width:4px}'
           '.zp .dot{stroke:#0A1230;stroke-width:2.5;transition:r .15s ease}.zp .h{fill:transparent}.zp .ld{stroke:#8f9fd0;stroke-width:1;fill:none;opacity:.7}.zp:hover .ld{stroke:#FFD86B;opacity:1}'
           '.zp:hover text,.zp:focus-visible text{fill:#FFD86B}.zp:hover .dot,.zp:focus-visible .dot{r:9}'
           '.zp.off{display:none}'
           '@keyframes zsdraw{to{stroke-dashoffset:0}}@keyframes zsin{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}'
           '@media (prefers-reduced-motion:reduce){.zp,.zs-rays line{animation:none;opacity:1;stroke-dashoffset:0}}'
           '.zs-legend{display:flex;flex-wrap:wrap;gap:6px 8px;margin:0 0 10px}'
           '.zs-legend .zs-f{display:inline-flex!important;align-items:center;gap:8px;min-height:36px;padding:0 12px;border:1px solid #3a4a80!important;border-radius:3px!important;background:transparent!important;color:#E6EBFA!important;font:500 14px/1 var(--label,sans-serif)!important;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;box-shadow:none!important}'
           '.zs-f i{width:10px;height:10px;border-radius:50%;display:inline-block}.zs-f[aria-pressed=false]{opacity:.45}.zs-f[aria-pressed=false] i{background:transparent!important;outline:1px solid #6f80b3}'
           '.zs-note{font-size:13px;color:var(--muted,#B4C1E4);margin:8px 2px 0}'
           '@media (max-width:820px){.zs-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}.zs{min-width:860px}.zs-hint{display:block!important}}'
           '</style>')
    jsx = ('<script>(function(){var w=document.querySelector(".zs-wrap");if(w&&w.scrollWidth>w.clientWidth)w.scrollLeft=(w.scrollWidth-w.clientWidth)/2;var b=document.querySelectorAll(".zs-f");b.forEach(function(x){x.addEventListener("click",function(){'
           'var on=x.getAttribute("aria-pressed")!=="true";x.setAttribute("aria-pressed",on);'
           'document.querySelectorAll(\'.zp[data-t="\'+x.dataset.t+\'"]\').forEach(function(p){p.classList.toggle("off",!on)})})})})();</script>')
    return (css + f'<div class="zs-legend" role="group" aria-label="Что показать">{legend}</div>'
            f'<p class="zs-note zs-hint" style="display:none">Схема шире экрана — листайте вбок.</p><div class="zs-wrap">{"".join(o)}</div>'
            f'<p class="zs-note">{E(note)}</p>' + jsx)
