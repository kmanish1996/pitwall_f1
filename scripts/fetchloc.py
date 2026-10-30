import json,urllib.request,urllib.error,urllib.parse,time,sys,os
from datetime import datetime,timedelta
def get(path):
    for a in range(5):
        try:
            with urllib.request.urlopen("https://api.openf1.org/v1/"+path,timeout=90) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code==404: return None
            print("retry",path[:80],e,file=sys.stderr); time.sleep(2+a*3)
        except Exception as e:
            print("retry",path[:80],e,file=sys.stderr); time.sleep(2+a*3)
    return None
sk=int(sys.argv[1]); d=f"raw/{sk}"
f=f"{d}/location_ref.json"
if os.path.exists(f): sys.exit()
laps=json.load(open(f"{d}/laps.json")); res=json.load(open(f"{d}/session_result.json")) or []
pits={(p["driver_number"],p["lap_number"]) for p in (json.load(open(f"{d}/pit.json")) or [])}
cand=[l for l in laps if l.get("lap_duration") and l.get("date_start") and l["lap_number"]>2 and not l.get("is_pit_out_lap") and (l["driver_number"],l["lap_number"]) not in pits and (l["driver_number"],l["lap_number"]-1) not in pits]
cand.sort(key=lambda l:l["lap_duration"])
for l in cand[:3]:
    t0=datetime.fromisoformat(l["date_start"]); t1=t0+timedelta(seconds=l["lap_duration"]+0.5)
    q=f"location?session_key={sk}&driver_number={l['driver_number']}&date>={urllib.parse.quote(t0.isoformat())}&date<={urllib.parse.quote(t1.isoformat())}"
    r=get(q)
    if r and len(r)>100:
        json.dump({"lap":l,"pts":r},open(f,"w")); print(sk,"ref lap",l["driver_number"],l["lap_number"],len(r)); break
    time.sleep(.5)
# fallback: full location trace for one driver, pick a clean lap inside its coverage
if not os.path.exists(f):
    for drv in [c["driver_number"] for c in cand[:1]]+[r["driver_number"] for r in res[:3]]:
        full=get(f"location?session_key={sk}&driver_number={drv}")
        if not full: continue
        a=datetime.fromisoformat(full[0]["date"]); b=datetime.fromisoformat(full[-1]["date"])
        mine=[l for l in cand if l["driver_number"]==drv and a<=datetime.fromisoformat(l["date_start"]) and datetime.fromisoformat(l["date_start"])+timedelta(seconds=l["lap_duration"])<=b]
        if not mine: continue
        l=mine[0]; t0=datetime.fromisoformat(l["date_start"]); t1=t0+timedelta(seconds=l["lap_duration"]+0.5)
        pts=[p for p in full if t0<=datetime.fromisoformat(p["date"])<=t1]
        if len(pts)>100:
            json.dump({"lap":l,"pts":pts},open(f,"w")); print(sk,"ref lap (fallback)",drv,l["lap_number"],len(pts)); break
