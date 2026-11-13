"""«Мой рейтинг» на странице reyting/luchshie-rayony/: ползунки «что мне важно» и бюджет за метр,
рейтинг пересчитывается у посетителя в браузере по тем же шкалам 0–10, что и балл «для жизни».
Идемпотентно (блок <!--MY-RATING-->…<!--MY-RATING-END-->), запускать после life_block.py.
Данные: tools/data/life_parts.json (шкалы) и assets/atlas.js (название, округ, цена метра)."""
import json, os, re
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
L = json.load(open(f'{REPO}/tools/data/life_parts.json', encoding='utf-8'))
s = open(f'{REPO}/assets/atlas.js', encoding='utf-8').read()
D, _ = json.JSONDecoder().raw_decode(s[s.index('{', s.index('const DATA')):])
K = [('tr', 'Транспорт', 'метро, МЦК, МЦД рядом и время до центра'),
     ('eco', 'Экология', 'воздух, заводы, ТЭЦ, свалки'),
     ('soc', 'Школы и поликлиники', 'на число жителей'),
     ('green', 'Парки и зелень', 'доля зелени и парки рядом с домом'),
     ('quiet', 'Тишина', 'дома далеко от магистралей и станций'),
     ('height', 'Без высоток', 'мало домов от 18 этажей'),
     ('live', 'Кафе и магазины', 'сколько их рядом'),
     ('sport', 'Спорт', 'залы, площадки, бассейны')]
SLUG = {n: sl for sl, n, _ in json.load(open(f'{REPO}/tools/data/districts_list.json', encoding='utf-8'))}
rows = []
for f in D['features']:
    p = f['properties']; sl = p.get('slug') or SLUG.get(p['n'])
    d = L['d'].get(sl)
    if not d: continue
    rows.append([sl, p['n'], p['o'], round(p['hp'] / 1000) if p.get('hp') else 0, [d['p'].get(k, -1) for k, _, _ in K]])
DEF = {k: round(v / 5) for k, v in L['w'].items()}
CSS = ('<style>.myr{border:1px solid var(--border,#27376B);padding:18px 20px;margin:18px 0 26px}.myr h2{margin:0 0 4px!important}.myr .sub{color:var(--muted);margin:0 0 14px;max-width:72ch}'
       '.myr .sl{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px 28px}.myr label.r{display:grid;grid-template-columns:minmax(0,1fr) 92px;gap:2px 12px;align-items:center}'
       '.myr label.r b{font-weight:600}.myr label.r small{grid-column:1/-1;grid-row:2;color:var(--muted);font-size:13px}.myr label.r span.v{grid-column:2;grid-row:1;text-align:right;color:#FFD86B;font-size:14px;white-space:nowrap}'
       '.myr input[type=range]{grid-column:1/-1;width:100%;accent-color:#FFD86B;min-height:28px}'
       '.myr .bud{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;margin:16px 0 4px}.myr select{background:#0F1A3C;color:var(--fg,#E6EBFA);border:1px solid #3a4a80;border-radius:3px;padding:7px 9px;font:inherit}'
       '.myr button.rs{min-height:38px;padding:0 14px;border:1px solid #3a4a80;border-radius:3px;background:transparent;color:var(--fg,#E6EBFA);font:inherit;cursor:pointer}.myr button.rs:focus-visible,.myr select:focus-visible{outline:2px solid #FFD86B;outline-offset:2px}'
       '.myr ol{margin:14px 0 0;padding:0;list-style:none;counter-reset:m}.myr li{counter-increment:m;display:grid;grid-template-columns:34px minmax(0,1fr) auto auto;gap:4px 14px;align-items:baseline;padding:7px 0;border-top:1px solid #1d2a57}'
       '.myr li:before{content:counter(m);color:var(--muted);font-variant-numeric:tabular-nums}.myr li a{font-weight:600}.myr li .o{color:var(--muted);font-size:13px;margin-left:6px;font-weight:400}'
       '.myr li .pr{color:var(--muted);font-size:14px;font-variant-numeric:tabular-nums;white-space:nowrap}.myr li .sc{color:#FFD86B;font-weight:600;font-variant-numeric:tabular-nums;min-width:34px;text-align:right}'
       '.myr .more{margin-top:10px}.myr .nt{color:var(--muted);font-size:13.5px;margin:12px 0 0;max-width:80ch}'
       '@media (max-width:700px){.myr{padding:14px}.myr .sl{grid-template-columns:1fr}.myr li{grid-template-columns:28px minmax(0,1fr) auto}.myr li .pr{grid-column:2;grid-row:2}}</style>')
LV = ['не важно', 'чуть-чуть', 'немного', 'важно', 'очень важно', 'главное']
sliders = ''.join(f'<label class="r"><b>{n}</b><span class="v" id="v-{k}">{LV[DEF.get(k, 0)]}</span><input type="range" min="0" max="5" step="1" value="{DEF.get(k, 0)}" data-k="{k}" aria-label="{n}: насколько важно"><small>{d}</small></label>' for k, n, d in K)
bud = ''.join(f'<option value="{v}">{t}</option>' for v, t in ((0, 'любая'), (350, 'до 350 тыс. ₽'), (400, 'до 400 тыс. ₽'), (450, 'до 450 тыс. ₽'), (500, 'до 500 тыс. ₽'), (600, 'до 600 тыс. ₽'), (800, 'до 800 тыс. ₽')))
JS = ('<script>(function(){var K=' + json.dumps([k for k, _, _ in K]) + ',R=' + json.dumps(rows, ensure_ascii=False, separators=(',', ':')) + ',CAP=' + str(L['cap_plus']) + ',LV=' + json.dumps(LV, ensure_ascii=False) + ',DEF=' + json.dumps(DEF) + ';'
      'var root=document.getElementById("myr"),ol=root.querySelector("ol"),sel=root.querySelector("select"),all=false;'
      'function w(){var o={};root.querySelectorAll("input[type=range]").forEach(function(i){o[i.dataset.k]=+i.value});return o}'
      'function score(r,W){var s=0,t=0;K.forEach(function(k,i){var v=r[4][i];if(v>=0&&W[k]){s+=v*W[k];t+=W[k]}});if(!t)return null;var v=s/t;'
      '["eco","tr"].forEach(function(k){var i=K.indexOf(k),x=r[4][i];if(W[k]&&x>=0&&x+CAP<v)v=x+CAP});return v}'
      'function f1(v){return v.toFixed(1).replace(".",",")}'
      'function upd(){var W=w(),b=+sel.value;K.forEach(function(k){document.getElementById("v-"+k).textContent=LV[W[k]]});'
      'var L=R.filter(function(r){return !b||(r[3]&&r[3]<=b)}).map(function(r){return [score(r,W),r]}).filter(function(x){return x[0]!=null}).sort(function(a,c){return c[0]-a[0]});'
      'var n=all?L.length:15;ol.innerHTML=L.slice(0,n).map(function(x){var r=x[1];return \'<li><span><a href="../../rayon/\'+r[0]+\'/">\'+r[1]+\'</a><span class="o">\'+r[2]+\'</span></span><span class="pr">\'+(r[3]?r[3]+" тыс. ₽/м²":"цены нет")+\'</span><span class="sc">\'+f1(x[0])+"</span></li>"}).join("");'
      'root.querySelector(".cnt").textContent=L.length?("Подходит районов: "+L.length+"."):"Под такой бюджет районов нет — поднимите сумму.";'
      'var m=root.querySelector(".more");m.hidden=L.length<=15;m.textContent=all?"Показать первые 15":"Показать все ("+L.length+")";'
      'try{localStorage.setItem("myr",JSON.stringify({w:W,b:b}))}catch(e){}}'
      'try{var S=JSON.parse(localStorage.getItem("myr")||"null");if(S){root.querySelectorAll("input[type=range]").forEach(function(i){if(S.w&&S.w[i.dataset.k]!=null)i.value=S.w[i.dataset.k]});sel.value=S.b||0}}catch(e){}'
      'root.addEventListener("input",upd);sel.addEventListener("change",upd);'
      'root.querySelector(".more").addEventListener("click",function(){all=!all;upd()});'
      'root.querySelector(".rs").addEventListener("click",function(){root.querySelectorAll("input[type=range]").forEach(function(i){i.value=DEF[i.dataset.k]||0});sel.value=0;upd()});upd()})();</script>')
BLOCK = ('<!--MY-RATING--><section class="myr" id="myr" aria-labelledby="myr-h">' + CSS +
         '<h2 id="myr-h">Свой рейтинг: что важно вам</h2><p class="sub">Подвиньте ползунки — рейтинг пересчитается под вас. Показатели те же, что в общем балле, по шкале от 0 до 10; '
         'правило слабого звена тоже действует: если экология или транспорт вам важны, район с провалом по ним наверх не поднимется. Ваши настройки запоминаются в этом браузере.</p>'
         f'<div class="sl">{sliders}</div><div class="bud"><label>Цена метра (вторичка) <select>{bud}</select></label><button type="button" class="rs">Как в общем рейтинге</button>'
         '<span class="cnt" aria-live="polite"></span></div><ol></ol><button type="button" class="rs more" hidden></button>'
         '<p class="nt">Цена — медианная цена метра в объявлениях о продаже квартир на вторичном рынке (Циан, ноябрь 2026), как во вкладке «Цены». Тишина, высотность и парки рядом — по домам из OpenStreetMap.</p>'
         + JS + '</section><!--MY-RATING-END-->')
p = f'{REPO}/reyting/luchshie-rayony/index.html'
h = open(p, encoding='utf-8').read()
h = re.sub(r'<!--MY-RATING-->.*?<!--MY-RATING-END-->', '', h, flags=re.S)
i = h.index('</header>', h.index('<main')) + len('</header>')
h = h[:i] + BLOCK + h[i:]
open(p, 'w', encoding='utf-8').write(h)
print('мой рейтинг: районов', len(rows))
