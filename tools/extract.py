import osmium, json, sys
FOOD={"cafe","restaurant","fast_food","bar","pub","food_court"}
SPORT={"sports_centre","fitness_centre","stadium","ice_rink","swimming_pool","pitch","fitness_station","track","sports_hall"}
out=[]
class H(osmium.SimpleHandler):
    def rec(self,o,lat,lon,area=None):
        t=o.tags; le=t.get("leisure"); am=t.get("amenity"); sh=t.get("shop")
        d={k:t.get(k) for k in ("name","sport","access","building","indoor","covered","surface","operator","fee","website") if t.get(k)}
        if le in SPORT: out.append(["S",le,lat,lon,area,d])
        if am in FOOD: out.append(["F",am,lat,lon,None,{"name":t.get("name")} if t.get("name") else {}])
        if sh and sh not in ("vacant","no"): out.append(["H",sh,lat,lon,None,{}])
    def node(self,n):
        if n.location.valid(): self.rec(n,n.location.lat,n.location.lon)
    def way(self,w):
        t=w.tags
        if not (t.get("leisure") in SPORT or t.get("amenity") in FOOD or t.get("shop")): return
        try:
            pts=[(n.lat,n.lon) for n in w.nodes if n.location.valid()]
        except Exception: return
        if not pts: return
        la=sum(p[0] for p in pts)/len(pts); lo=sum(p[1] for p in pts)/len(pts)
        # approx area m2 (closed)
        a=None
        if len(pts)>3 and w.is_closed():
            import math
            k=111320*math.cos(math.radians(la)); s=0
            for i in range(len(pts)-1):
                x1,y1=pts[i][1]*k,pts[i][0]*110540; x2,y2=pts[i+1][1]*k,pts[i+1][0]*110540; s+=x1*y2-x2*y1
            a=round(abs(s)/2)
        self.rec(w,la,lo,a)
h=H(); h.apply_file(sys.argv[1],locations=True,idx="flex_mem")
json.dump(out,open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)),"data","osm_points.json"),"w"),ensure_ascii=False)
import collections
print(len(out), collections.Counter((r[0],r[1]) for r in out if r[0]!="H").most_common(20), sum(r[0]=="H" for r in out))
