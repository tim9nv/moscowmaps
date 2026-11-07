import json, math, collections
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
import os as _os
TOOLS=_os.path.dirname(_os.path.abspath(__file__)); DATA=_os.path.join(TOOLS,'data'); ROOT=_os.path.dirname(TOOLS)
D=json.load(open(_os.path.join(DATA,'districts.json')))['features']
geoms=[shape(f['geometry']) for f in D]; tree=STRtree(geoms)
pts=json.load(open(_os.path.join(DATA,'osm_points.json')))
def which(la,lo):
    p=Point(lo,la)
    for i in tree.query(p):
        if geoms[i].contains(p): return int(i)
    return None
n=len(D)
cnt=collections.defaultdict(lambda: collections.Counter())
fac=[]   # named facilities for map
seen=collections.defaultdict(list)
def dup(kind,la,lo,r=60):
    key=(kind,round(la,2),round(lo,2))
    for (a,b) in seen[key]:
        if abs(a-la)*111000<r and abs(b-lo)*63000<r: return True
    seen[key].append((la,lo)); return False
for typ,k,la,lo,area,t in pts:
    i=which(la,lo)
    if i is None: continue
    c=cnt[i]
    if typ=="F": c["food"]+=1; continue
    if typ=="H": c["shop"]+=1; continue
    acc=t.get("access","")
    priv=acc in ("private","no")
    sport=t.get("sport","")
    swim=("swimming" in sport) or k=="swimming_pool"
    if k in ("pitch","fitness_station","track"):
        if priv: continue
        if k=="track": continue
        c["ground" if k=="pitch" else "workout"]+=1; continue
    if k=="swimming_pool":
        if priv or acc=="customers": continue
        if (t.get("indoor")!="yes" and t.get("building")!="yes") and not t.get("name"): continue  # outdoor unnamed pools (dachas)
    kind="pool" if swim else ("ice" if k=="ice_rink" else ("stad" if k=="stadium" else ("fit" if k=="fitness_centre" else "club")))
    if dup(kind,la,lo): continue
    c[kind]+=1
    fac.append([kind,round(lo,4),round(la,4),t.get("name",""),i])
P=[f['properties'] for f in D]
rows=[]
for i,p in enumerate(P):
    c=cnt[i]; pop=p.get('pop') or 0; area=p.get('area') or 0
    rows.append(dict(n=p['n'],o=p['o'],pop=pop,area=area,**{k:c[k] for k in ("pool","club","fit","ice","stad","ground","workout","food","shop")}))
import statistics
for r in rows:
    pop=r['pop']; a=r['area']
    r['halls']=r['club']+r['fit']+r['ice']+r['stad']
    r['grounds']=r['ground']+r['workout']
    if pop:
        r['pool10']=r['pool']/pop*1e4; r['halls10']=r['halls']/pop*1e4; r['grounds10']=r['grounds']/pop*1e4
    r['lv']=(r['food']+r['shop'])/a if a else None
# score: percentile within districts with pop>=5000
ok=[r for r in rows if r['pop']>=5000]
def pct(key):
    vals=sorted(r[key] for r in ok)
    for r in ok:
        v=r[key]; below=sum(x<v for x in vals); eq=sum(x==v for x in vals)
        r[key+'_s']=1+9*((below+ (eq-1)/2)/(len(vals)-1))
for k in ("pool10","halls10","grounds10"): pct(k)
for r in ok: r['sp']=round(0.3*r['pool10_s']+0.4*r['halls10_s']+0.3*r['grounds10_s'],1)
# liveliness levels by quintile of density
lvs=sorted(r['lv'] for r in rows if r['lv'] is not None)
q=[lvs[int(len(lvs)*k/5)] for k in (1,2,3,4)]
print("lv quintile cuts",[round(x) for x in q])
json.dump({"rows":rows,"fac":fac,"lvcuts":q},open(_os.path.join(DATA,'sport_data.json'),'w'),ensure_ascii=False)
tot=collections.Counter(f[0] for f in fac); print(tot, sum(r['grounds'] for r in rows))
S=sorted(ok,key=lambda r:-r['sp'])
for r in S[:8]+S[-8:]: print(r['n'],r['sp'],r['pool'],r['halls'],r['grounds'],r['pop'])
L=sorted([r for r in rows if r['lv']],key=lambda r:-r['lv'])
for r in L[:6]+L[-6:]: print('LV',r['n'],round(r['lv']),r['food'],r['shop'])
print('nopop',[r['n'] for r in rows if r['pop']<5000])
