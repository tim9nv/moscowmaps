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
RAYS = [('Ленинградское', 'klin'), ('Савёловское', 'dmitrov'), ('Ярославское', 'sergiev-posad'), ('Яросл. вокзал: Монино', 'monino'),
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
    items = [dict(name=p.get('short') or p['name'], href=p['slug'] + '/', ll=hubpt[p['slug']], t=TYPE_OF.get(p['slug'], 'city'),
                  tip=f"{p['name']} — {p['kind']}") for p in places]
    note = ('Схема, а не карта: место стоит в своём направлении от Москвы, а расстояние по прямой сжато, '
            'чтобы ближние усадьбы и Углич поместились на одном листе. Лучи — железнодорожные направления от московских вокзалов. '
            'Колесо мыши, щипок или кнопки «+/−» приближают; подписи, которым не хватает места, появляются при приближении. Наведите на точку — откроется карточка места.')
    return scheme_items(items, TYPES, hubpt, note)


RANK = {'city': 0, 'holy': 1, 'estate': 2, 'museum': 3, 'nature': 4, 'kids': 5}


def scheme_items(items, types, hubpt, note, uid='zs'):
    """Схема с приближением: колесо мыши, щипок, кнопки +/−, перетаскивание.
    Подписи пересчитываются при каждом масштабе: если подпись налезает на другую, она прячется
    и появится при приближении; при наведении или нажатии на точку — карточка места."""
    pts = []
    for it in items:
        ll = it['ll']
        d = km(ll)
        b = bearing(ll)
        x, y = xy(b, rad(d))
        nm, _, kind = it['tip'].partition(' — ')
        pts.append(dict(n=it['name'], f=nm, k=kind, h=it['href'], t=it['t'], d=round(d / 5) * 5, x=round(x, 1), y=round(y, 1),
                        r=RANK.get(it['t'], 6) * 1000 + d))
    pts.sort(key=lambda q: q['r'])
    col = {k: c for k, _, c in types}
    o = [f'<svg class="zs" viewBox="0 0 {W} {H}" role="img" aria-labelledby="zs-t"><title id="zs-t">Схема: места за городом по направлениям от Москвы</title>'
         '<g class="zs-world">']
    o.append('<g class="zs-rings">')
    for r_km in (50, 100, 150, 200):
        r = rad(r_km)
        o.append(f'<circle cx="{CX:.0f}" cy="{CY:.0f}" r="{r:.1f}"/>')
    o.append('</g><g class="zs-rays">')
    rays = []
    for name, slug in RAYS:
        b = bearing(hubpt[slug])
        x0, y0 = xy(b, rad(MKAD_KM) + 2)
        x1, y1 = xy(b, RMAX + 4)
        o.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}"/>')
        lx, ly = xy(b, RMAX + 16)
        rays.append(dict(n=name.split(':')[0], x=round(lx, 1), y=round(ly, 1), s=round(math.sin(b), 2)))
    rm = rad(MKAD_KM)
    o.append(f'</g><circle class="zs-msk" cx="{CX:.0f}" cy="{CY:.0f}" r="{rm:.1f}"/><g class="zs-dots">')
    for i, q in enumerate(pts):
        o.append(f'<circle class="zd" data-i="{i}" data-t="{q["t"]}" cx="{q["x"]}" cy="{q["y"]}" r="6" style="fill:{col[q["t"]]}"/>')
    o.append('</g></g><g class="zs-lab"></g></svg>')
    import json
    data = json.dumps(dict(p=[{k: q[k] for k in ('n', 'f', 'k', 'h', 't', 'd', 'x', 'y')} for q in pts], rays=rays,
                           rings=[dict(km=r_km, r=round(rad(r_km), 1)) for r_km in (50, 100, 150, 200)],
                           c=[CX, CY], rm=round(rm, 1), W=W, H=H), ensure_ascii=False)
    legend = ''.join(f'<button type="button" class="zs-f" data-t="{k}" aria-pressed="true"><i style="background:{c}"></i>{E(lbl)}</button>'
                     for k, lbl, c in types if any(q['t'] == k for q in pts))
    css = ('<style>'
           '.zs-wrap{position:relative;border:1px solid #3a4a80;outline:1px solid #27376B;outline-offset:5px;background:#0A1230;margin-top:6px;overflow:hidden;touch-action:none;user-select:none;-webkit-user-select:none}'
           '.zs{display:block;width:100%;height:auto;max-height:78vh;cursor:grab;font-family:var(--label,"Arial Narrow",sans-serif)}.zs.drag{cursor:grabbing}'
           '.zs-rings circle{fill:none;stroke:#1f2d5e;stroke-dasharray:2 6;vector-effect:non-scaling-stroke}'
           '.zs-rays line{stroke:#1c2a59;stroke-width:1;vector-effect:non-scaling-stroke}'
           '.zs-msk{fill:#13235A;stroke:#F2F5FF;stroke-width:1.2;vector-effect:non-scaling-stroke}'
           '.zd{stroke:#0A1230;stroke-width:2;vector-effect:non-scaling-stroke;cursor:pointer;transition:opacity .15s ease}.zd.off{display:none}.zd.on{stroke:#FFD86B;stroke-width:3}'
           '.zs-lab text{fill:#E6EBFA;font-size:1em;font-weight:500;letter-spacing:.02em;paint-order:stroke;stroke:#0A1230;stroke-width:inherit;pointer-events:none}'
           '.zs-lab text.on{fill:#FFD86B}.zs-lab .ring{fill:#55679e;font-size:.85em;letter-spacing:.08em;font-weight:500}'
           '.zs-lab .ray{fill:#7f8fc0;font-size:.85em;letter-spacing:.12em;text-transform:uppercase}.zs-lab .msk{fill:#F2F5FF;font-family:var(--display,Georgia,serif);font-size:1.3em;font-weight:400}'
           '.zs-ctl{position:absolute;right:10px;top:10px;display:flex;flex-direction:column;gap:6px;z-index:2}'
           '.zs-ctl button{width:38px!important;height:38px!important;padding:0!important;border:1px solid #3a4a80!important;border-radius:3px!important;background:#0F1A3C!important;color:#E6EBFA!important;font:500 20px/1 var(--label,sans-serif)!important;cursor:pointer;box-shadow:none!important}'
           '.zs-ctl button:hover{border-color:#FFD86B!important;color:#FFD86B!important}'
           '.zs-card{position:absolute;z-index:3;min-width:190px;max-width:260px;background:#0F1A3C;border:1px solid #3a4a80;border-radius:3px;padding:10px 12px;box-shadow:0 8px 24px rgba(0,0,0,.45);pointer-events:auto;opacity:0;transform:translateY(4px);transition:opacity .15s ease,transform .15s cubic-bezier(.23,1,.32,1)}'
           '.zs-card.show{opacity:1;transform:none}.zs-card b{display:block;font:500 16px/1.25 var(--display,Georgia,serif);color:#F2F5FF}'
           '.zs-card span{display:block;font-size:13.5px;color:#B4C1E4;margin:3px 0 8px}.zs-card a{font:600 13.5px var(--label,sans-serif);letter-spacing:.06em;text-transform:uppercase;color:#FFD86B;text-decoration:none}'
           '.zs-legend{display:flex;flex-wrap:wrap;gap:6px 8px;margin:0 0 10px}'
           '.zs-legend .zs-f{display:inline-flex!important;align-items:center;gap:8px;min-height:36px;padding:0 12px;border:1px solid #3a4a80!important;border-radius:3px!important;background:transparent!important;color:#E6EBFA!important;font:500 14px/1 var(--label,sans-serif)!important;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;box-shadow:none!important}'
           '.zs-f i{width:10px;height:10px;border-radius:50%;display:inline-block}.zs-f[aria-pressed=false]{opacity:.45}.zs-f[aria-pressed=false] i{background:transparent!important;outline:1px solid #6f80b3}'
           '.zs-note{font-size:13px;color:var(--muted,#B4C1E4);margin:8px 2px 0}'
           '@media (max-width:700px){.zs{max-height:none}.zs-ctl button{width:34px!important;height:34px!important}}'
           '</style>')
    js = r"""<script>(function(){var D=__DATA__;var w=document.querySelector('.zs-wrap'),sv=w.querySelector('svg'),wd=sv.querySelector('.zs-world'),lb=sv.querySelector('.zs-lab'),card=w.querySelector('.zs-card');
var NS='http://www.w3.org/2000/svg',k=1,tx=0,ty=0,off={},sel=-1,dots=sv.querySelectorAll('.zd');
function el(n,a,t){var e=document.createElementNS(NS,n);for(var q in a)e.setAttribute(q,a[q]);if(t!=null)e.textContent=t;return e}
function S(x,y){return[x*k+tx,y*k+ty]}
var meas=el('text',{x:-999,y:-999});lb.appendChild(meas);var wid={},u=1;function tw(s,c){var key=c+'|'+s;if(!(key in wid)){var fs=lb.style.fontSize;lb.style.fontSize='13.5px';meas.setAttribute('class',c||'');meas.textContent=s;wid[key]=meas.getComputedTextLength();lb.style.fontSize=fs}return wid[key]*u}
function draw(){var rw=sv.getBoundingClientRect().width||D.W;u=Math.max(1,D.W/rw);lb.setAttribute('transform','');lb.style.fontSize=(13.5*u)+'px';lb.style.strokeWidth=(4*u)+'px';wd.setAttribute('transform','translate('+tx+','+ty+') scale('+k+')');dots.forEach(function(d){d.setAttribute('r',(k>2?7:6)*u*(+d.dataset.i===sel?1.4:1)/k)});
while(lb.lastChild&&lb.lastChild!==meas)lb.removeChild(lb.lastChild);
var boxes=[],R=D.rm*k,c=S(D.c[0],D.c[1]);
function hit(b){if(b[0]<2||b[2]>D.W-2||b[1]<2||b[3]>D.H-2)return true;for(var i=0;i<boxes.length;i++){var o=boxes[i];if(b[0]<o[2]&&b[2]>o[0]&&b[1]<o[3]&&b[3]>o[1])return true}
var nx=Math.max(b[0],Math.min(c[0],b[2])),ny=Math.max(b[1],Math.min(c[1],b[3]));return (nx-c[0])*(nx-c[0])+(ny-c[1])*(ny-c[1])<R*R}
if(R>40*u){boxes.push([c[0]-R,c[1]-R,c[0]+R,c[1]+R]);lb.appendChild(el('text',{x:c[0],y:c[1]+6*u,'text-anchor':'middle','class':'msk'},'Москва'))}
D.p.forEach(function(p,i){if(off[p.t])return;var s=S(p.x,p.y);boxes.push([s[0]-7*u,s[1]-7*u,s[0]+7*u,s[1]+7*u])});
D.rays.forEach(function(r){var s=S(r.x,r.y),wv=tw(r.n,'ray'),a=r.s>.3?'start':r.s<-.3?'end':'middle',x0=a==='start'?s[0]:a==='end'?s[0]-wv:s[0]-wv/2,b=[x0,s[1]-10*u,x0+wv,s[1]+4*u];if(!hit(b)){boxes.push(b);lb.appendChild(el('text',{x:s[0],y:s[1],'text-anchor':a,'class':'ray'},r.n))}});
D.rings.forEach(function(g){var s=S(D.c[0],D.c[1]-g.r),t=g.km+' км',wv=tw(t,'ring'),b=[s[0]+3*u,s[1]-15*u,s[0]+5*u+wv,s[1]-3*u];if(!hit(b)){boxes.push(b);lb.appendChild(el('text',{x:s[0]+4*u,y:s[1]-5*u,'class':'ring'},t))}});
var order=D.p.map(function(p,i){return i});if(sel>=0){order.splice(order.indexOf(sel),1);order.unshift(sel)}
order.forEach(function(i){var p=D.p[i];if(off[p.t])return;var s=S(p.x,p.y),wv=tw(p.n,''),right=s[0]>=c[0];
var tries=[[right,0],[!right,0],[right,-14],[right,14],[!right,-14],[!right,14]];for(var j=0;j<tries.length;j++){var rt=tries[j][0],dy=tries[j][1]*u,x0=rt?s[0]+10*u:s[0]-10*u-wv,b=[x0,s[1]-9*u+dy,x0+wv,s[1]+6*u+dy];
if(i===sel||!hit(b)){boxes.push(b);lb.appendChild(el('text',{x:rt?s[0]+10*u:s[0]-10*u,y:s[1]+4*u+dy,'text-anchor':rt?'start':'end','class':i===sel?'on':''},p.n));return}}})}
function clamp(){var mx=D.W*.2,my=D.H*.2;tx=Math.min(mx,Math.max(D.W-D.W*k-mx,tx));ty=Math.min(my,Math.max(D.H-D.H*k-my,ty))}
function zoomAt(f,px,py){var nk=Math.max(1,Math.min(8,k*f));f=nk/k;tx=px-(px-tx)*f;ty=py-(py-ty)*f;k=nk;if(k===1){tx=0;ty=0}clamp();draw();place()}
function pt(e){var r=sv.getBoundingClientRect();return[(e.clientX-r.left)*D.W/r.width,(e.clientY-r.top)*D.H/r.height]}
sv.addEventListener('wheel',function(e){e.preventDefault();var p=pt(e);zoomAt(Math.exp(-e.deltaY*.0018),p[0],p[1])},{passive:false});
var ps={},drag=null,moved=0;
sv.addEventListener('pointerdown',function(e){sv.setPointerCapture(e.pointerId);ps[e.pointerId]=pt(e);moved=0;var ids=Object.keys(ps);if(ids.length===1)drag={p:pt(e),tx:tx,ty:ty};else{var a=ps[ids[0]],b=ps[ids[1]];drag={pinch:Math.hypot(a[0]-b[0],a[1]-b[1]),k:k}}});
sv.addEventListener('pointermove',function(e){if(!(e.pointerId in ps)||!drag)return;var p=pt(e);ps[e.pointerId]=p;var ids=Object.keys(ps);
if(ids.length>1&&drag.pinch){var a=ps[ids[0]],b=ps[ids[1]],d=Math.hypot(a[0]-b[0],a[1]-b[1]);moved=9;zoomAt(drag.k*d/drag.pinch/k,(a[0]+b[0])/2,(a[1]+b[1])/2)}
else if(drag.p){var dx=p[0]-drag.p[0],dy=p[1]-drag.p[1];if(Math.abs(dx)+Math.abs(dy)>4)moved=9;if(moved&&k>1){sv.classList.add('drag');tx=drag.tx+dx;ty=drag.ty+dy;clamp();draw();place()}}});
function up(e){delete ps[e.pointerId];if(!Object.keys(ps).length){sv.classList.remove('drag');drag=null}}sv.addEventListener('pointerup',up);sv.addEventListener('pointercancel',up);
sv.addEventListener('dblclick',function(e){var p=pt(e);zoomAt(2,p[0],p[1])});
function place(){if(sel<0){card.classList.remove('show');return}var p=D.p[sel],s=S(p.x,p.y),r=sv.getBoundingClientRect(),f=r.width/D.W,x=s[0]*f,y=s[1]*f,cw=card.offsetWidth,ch=card.offsetHeight;
if(x<-5||y<-5||x>r.width+5||y>r.height+5){card.classList.remove('show');return}var L=x+16+cw>r.width?x-16-cw:x+16,T=Math.max(6,Math.min(r.height-ch-6,y-ch/2));card.style.left=Math.max(6,L)+'px';card.style.top=T+'px';card.classList.add('show')}
function pick(i){sel=i;dots.forEach(function(d){d.classList.toggle('on',+d.dataset.i===i)});if(i>=0){var p=D.p[i];card.innerHTML='<b></b><span></span><a>Открыть место →</a>';card.querySelector('b').textContent=p.f;card.querySelector('span').textContent=(p.k?p.k+' · ':'')+'около '+p.d+' км по прямой';card.querySelector('a').href=p.h}draw();place()}
dots.forEach(function(d){d.addEventListener('mouseenter',function(){if(!drag)pick(+d.dataset.i)});d.addEventListener('click',function(e){if(moved)return;e.stopPropagation();var i=+d.dataset.i;if(sel===i&&e.pointerType!=='touch'){location.href=D.p[i].h}else pick(i)})});
sv.addEventListener('click',function(e){if(moved||e.target.classList.contains('zd'))return;var q=pt(e),bi=-1,bd=22*u;D.p.forEach(function(p,i){if(off[p.t])return;var s=S(p.x,p.y),dd=Math.hypot(s[0]-q[0],s[1]-q[1]);if(dd<bd){bd=dd;bi=i}});pick(bi)});
w.querySelector('.zs-in').addEventListener('click',function(){zoomAt(1.6,D.W/2,D.H/2)});w.querySelector('.zs-out').addEventListener('click',function(){zoomAt(1/1.6,D.W/2,D.H/2)});w.querySelector('.zs-home').addEventListener('click',function(){k=1;tx=0;ty=0;pick(-1)});
document.querySelectorAll('.zs-f').forEach(function(x){x.addEventListener('click',function(){var on=x.getAttribute('aria-pressed')!=='true';x.setAttribute('aria-pressed',on);off[x.dataset.t]=!on;
dots.forEach(function(d){if(d.dataset.t===x.dataset.t)d.classList.toggle('off',!on)});if(sel>=0&&off[D.p[sel].t])pick(-1);else draw()})});
window.addEventListener('resize',function(){wid={};draw();place()});draw()})();</script>""".replace('__DATA__', data)
    return (css + f'<div class="zs-legend" role="group" aria-label="Что показать">{legend}</div>'
            f'<div class="zs-wrap">{"".join(o)}<div class="zs-ctl"><button type="button" class="zs-in" aria-label="Приблизить">+</button>'
            f'<button type="button" class="zs-out" aria-label="Отдалить">−</button><button type="button" class="zs-home" aria-label="Показать всю схему" title="Показать всю схему"><svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg></button></div>'
            f'<div class="zs-card" role="status"></div></div>'
            f'<p class="zs-note">{E(note)}</p>' + js)
