import json, re
import os as _os
TOOLS=_os.path.dirname(_os.path.abspath(__file__)); DATA=_os.path.join(TOOLS,'data'); ROOT=_os.path.dirname(TOOLS)
SRC=_os.path.join(ROOT,'social.html'); DST=_os.path.join(ROOT,'sport.html')
s=open(SRC,encoding='utf-8').read()
sd=json.load(open(_os.path.join(DATA,'sport_data.json'))); R={r['n']:r for r in sd['rows']}
i=s.index('const DATA = ')+len('const DATA = '); d,e=json.JSONDecoder().raw_decode(s[i:])
per=lambda c,pop: round(pop/c) if c else None
for f in d['features']:
    p=f['properties']; r=R[p['n']]; pop=r['pop']
    f['properties']={"n":p['n'],"o":p['o'],"pop":p['pop'],"dens":p['dens'],"area":p['area'],"score":r.get('sp'),
      "pool":r['pool'],"halls":r['halls'],"club":r['club'],"fit":r['fit'],"ice":r['ice'],"stad":r['stad'],"grounds":r['grounds'],"ground":r['ground'],"workout":r['workout'],
      "pool_per":per(r['pool'],pop),"halls_per":per(r['halls'],pop),"grounds_per":per(r['grounds'],pop),
      "pool_10k":round(r.get('pool10',0),2),"halls_10k":round(r.get('halls10',0),2),"grounds_10k":round(r.get('grounds10',0),2)}
s=s[:i]+json.dumps(d,ensure_ascii=False,separators=(',',':'))+s[i+e:]
sc=sorted(f['properties']['score'] for f in d['features'] if f['properties']['score'] is not None)
q=[round(sc[int(len(sc)*k/5)],1) for k in (1,2,3,4)]
fa=lambda x:str(x).replace('.',',')
BINS=[[0,q[0],f"1–{fa(q[0])} мало"],[q[0],q[1],f"{fa(q[0])}–{fa(q[1])}"],[q[1],q[2],f"{fa(q[1])}–{fa(q[2])}"],[q[2],q[3],f"{fa(q[2])}–{fa(q[3])}"],[q[3],11,f"{fa(q[3])}–10 много"]]
FAC=[[k,lo,la,n] for k,lo,la,n,_ in sd['fac']]
def rep(a,b,cnt=1):
    global s
    assert s.count(a)>=1, a[:70]; s=s.replace(a,b,cnt)
rep('<title>Социальная инфраструктура Москвы</title>','<title>Спорт в районах Москвы</title>')
s=re.sub(r'<nav class="section-tabs" aria-label="Городская среда">.*?</nav>','<nav class="section-tabs" aria-label="Городская среда"><a href="social.html">Соцобъекты</a><a href="parks.html">Парки</a><a href="sport.html" aria-current="page">Спорт</a></nav>',s,count=1)
rep('<h1>Обеспеченность районов Москвы учреждениями образования и здравоохранения</h1>','<h1>Где в Москве удобно заниматься спортом</h1>')
s=re.sub(r'<p class="lede">Сколько школ.*?</p>','<p class="lede">Бассейны, спорткомплексы, фитнес-клубы, катки, футбольные и баскетбольные площадки и воркауты на жителей каждого района. Шкала от 1 (спорта рядом мало) до 10 (много). Точки на карте — бассейны и спортивные залы, наведите на точку, чтобы увидеть название; клик по району открывает его страницу.</p>',s,count=1,flags=re.S)
rep('aria-label="Карта районов Москвы, окрашенных по обеспеченности школами, садами и поликлиниками"','aria-label="Карта районов Москвы, окрашенных по обеспеченности спортивными объектами"')
rep('<h2>Наибольшая нагрузка</h2>','<h2>Меньше всего спорта</h2>'); rep('<h2>Наименьшая нагрузка</h2>','<h2>Больше всего спорта</h2>')
s=re.sub(r'(<section class="method">\s*<h2>Методика</h2>).*?(</section>)',r'''\1
    <p>Для каждого района посчитано на 10 тысяч жителей три вещи: бассейны, спортивные залы (спорткомплексы, фитнес-клубы, ледовые арены и стадионы) и открытые площадки (футбольные, баскетбольные, теннисные корты и воркауты). По каждому показателю район получает место среди 125 районов, места переводятся в шкалу от 1 до 10. Итог — взвешенное среднее: залы 40 %, бассейны 30 %, площадки 30 %.</p>
    <p>Все объекты — из OpenStreetMap, выгрузка 7 ноября 2026 года. Закрытые площадки (с пометкой «частный доступ») не учитываются, бассейны в жилых комплексах «только для жильцов» тоже. Если один объект отмечен дважды рядом, он считается один раз. OpenStreetMap неполон: бассейны в школах и маленькие студии часто не нанесены, поэтому сами числа примерные, а сравнивать районы между собой можно. Население — Росстат и Wikidata за 2025 год.</p>
  \2''',s,count=1,flags=re.S)
s=re.sub(r'(<section class="src">\s*<h2>Источники</h2>\s*)<p>.*?</p>',r'\1<p>Спортивные объекты и границы районов — <a href="https://www.openstreetmap.org/">OpenStreetMap</a> (выгрузка <a href="https://download.openstreetmap.fr/extracts/russia/central_federal_district/">openstreetmap.fr</a>, 7 ноября 2026) · Население — <a href="https://www.real-stats.ru/data/">real-stats.ru</a> (Росстат/Wikidata 2025).</p>',s,count=1,flags=re.S)
rep(re.search(r'const BINS=\[\[0,3,.*?\];',s).group(0),'const BINS='+json.dumps(BINS,ensure_ascii=False)+';')
rep('function stat(label,count,per,per10){','function stat(label,count,per,per10,sub){')
rep('${String(per10.toFixed(1)).replace(".",",")} на 10 тыс.</div></div>`}','${String(per10.toFixed(1)).replace(".",",")} на 10 тыс.</div>${sub?`<div class="s">${sub}</div>`:""}</div>`}')
# card
i0=s.index('  if(p.score==null){c.innerHTML='); i1=s.index('\n}\nconst has=')
s=s[:i0]+'''  const parts=[p.club&&`спорткомплексы ${p.club}`,p.fit&&`фитнес ${p.fit}`,p.ice&&`катки ${p.ice}`,p.stad&&`стадионы ${p.stad}`].filter(Boolean).join(" · ");
  c.innerHTML=`<div class="score" style="color:${p.score<BINS[0][1]?"var(--bad)":"var(--fg)"}">${fmt(p.score)}</div>
   <div class="cname">${p.n} <span class="csub">· ${p.o}</span></div>
   <div class="csub">${num(p.pop)} жителей · ${num(p.dens)} чел/км² · ${String(p.area).replace(".",",")} км²</div>
   <div class="stats">${stat("Бассейны",p.pool,p.pool_per,p.pool_10k)}${stat("Спортзалы и клубы",p.halls,p.halls_per,p.halls_10k,parts)}${stat("Площадки и воркауты",p.grounds,p.grounds_per,p.grounds_10k,`площадки ${p.ground} · воркауты ${p.workout}`)}</div>${distLink(p.n)}`;
'''+s[i1:]
rep('<span class="m">${num(p.pop)} жит. · школа на ${num(p.school_per)} · сад на ${num(p.kinder_per)} · поликлиника на ${num(p.clinic_per)}</span>','<span class="m">${num(p.pop)} жит. · бассейнов ${p.pool} · залов ${p.halls} · площадок ${p.grounds}</span>')
rep('label:"Балл соцобъектов",hint:"школы, детские сады и поликлиники на жителя: 1 не хватает, 10 хватает · выберите один или несколько диапазонов"','label:"Балл спорта",hint:"бассейны, залы и площадки на жителя: 1 мало, 10 много · выберите один или несколько диапазонов"')
rep('const sorted=[...has].sort((a,b)=>a.properties.score-b.properties.score);','const sorted=[...has].sort((a,b)=>a.properties.score-b.properties.score);')
# facilities layer
rep('cityOverlay(d3.select(sel.node().parentNode),d3.geoMercator().fitExtent([[10,10],[590,610]],inner),F);',
'''cityOverlay(d3.select(sel.node().parentNode),d3.geoMercator().fitExtent([[10,10],[590,610]],inner),F);
const FAC=__FAC__;
const FK={pool:["Бассейн","var(--fpool)"],club:["Спорткомплекс","var(--fhall)"],fit:["Фитнес-клуб","var(--fhall)"],ice:["Каток","var(--fhall)"],stad:["Стадион","var(--fhall)"]};
{const pj=d3.geoMercator().fitExtent([[10,10],[590,610]],inner);const fg=d3.select(sel.node().parentNode).append("g").attr("class","fac");
 [...FAC].sort((a,b)=>(a[0]==="pool")-(b[0]==="pool")).forEach(([k,lo,la,n])=>{const q=pj([lo,la]);if(q[0]<0||q[0]>600||q[1]<0||q[1]>620)return;
  const c=fg.append("circle").attr("cx",q[0].toFixed(1)).attr("cy",q[1].toFixed(1)).attr("r",k==="pool"?2.8:1.5).attr("class",k==="pool"?"fp":"fh");
  c.append("title").text(FK[k][0]+(n?" «"+n.replace(/^[«"]|[»"]$/g,"")+"»":""))});
 const lb=d3.select(sel.node().parentNode).append("g").attr("class","ovl").style("pointer-events","none");document.querySelectorAll("#main .ov-lbl").forEach(t=>lb.node().appendChild(t))}''')
s=s.replace('__FAC__',json.dumps(FAC,ensure_ascii=False,separators=(',',':')))
rep('document.getElementById("legend").innerHTML=BINS.map((b,k)=>`<span><i style="background:var(--c${k+1})"></i>${b[2]}</span>`).join("")+`<span><i style="background:var(--nodata)"></i>нет данных</span>`;',
 'document.getElementById("legend").innerHTML=BINS.map((b,k)=>`<span><i style="background:var(--c${k+1})"></i>${b[2]}</span>`).join("")+`<span><i style="background:var(--fpool);border-radius:50%;width:9px;height:9px;border:1.5px solid var(--surface)"></i>бассейн</span><span><i style="background:var(--fhall);border-radius:50%;width:7px;height:7px;border:1.5px solid var(--surface)"></i>спортзал, клуб, каток, стадион</span>`;')
rep('.wtr .wp{','.fac circle{stroke:var(--surface);stroke-width:.7;cursor:default}.fac .fp{fill:var(--fpool)}.fac .fh{fill:var(--fhall);fill-opacity:.55;stroke-width:.4}\n:root{--fpool:#1668b8;--fhall:#2a2d2b}\n@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--fpool:#5fb0f0;--fhall:#e9e8e2}}\n:root[data-theme="dark"]{--fpool:#5fb0f0;--fhall:#e9e8e2}\n.wtr .wp{')
open(DST,'w',encoding='utf-8').write(s)
print('ok',BINS,len(FAC))
