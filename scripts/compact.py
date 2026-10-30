"""Pack raw OpenF1 session data into one compact replay JSON per session.
Times are seconds from race start (first lap-1 date_start), rounded to 0.1 s."""
import json, sys, os, math
from datetime import datetime

RAW = "raw"; OUT = "site/data"
os.makedirs(OUT, exist_ok=True)

def ts(s): return datetime.fromisoformat(s).timestamp()
def load(sk, ep):
    p = f"{RAW}/{sk}/{ep}.json"
    if not os.path.exists(p): return []
    v = json.load(open(p)); return v or []
def r1(x): return None if x is None else round(x, 1)
def r3(x): return None if x is None else round(x, 3)

def track_from_ref(ref):
    pts = ref["pts"]; lap = ref["lap"]
    t0 = ts(lap["date_start"]); dur = lap["lap_duration"]
    raw = [(ts(p["date"]) - t0, p["x"], p["y"]) for p in pts]
    raw = [p for p in raw if -0.3 <= p[0] <= dur + 0.3]
    # drop duplicate consecutive positions
    clean = []
    for p in raw:
        if clean and p[1] == clean[-1][1] and p[2] == clean[-1][2]: continue
        clean.append(p)
    xs = [p[1] for p in clean]; ys = [p[2] for p in clean]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    span = max(maxx - minx, maxy - miny)
    W = 1000
    sc = W / span
    w = (maxx - minx) * sc; h = (maxy - miny) * sc
    path = [[round((p[1] - minx) * sc, 1), round((maxy - p[2]) * sc, 1), round(max(0, min(1, p[0] / dur)), 4)] for p in clean]
    # force monotonic time fraction
    for i in range(1, len(path)):
        if path[i][2] < path[i - 1][2]: path[i][2] = path[i - 1][2]
    s1, s2 = lap.get("duration_sector_1"), lap.get("duration_sector_2")
    sec = [round(s1 / dur, 4), round((s1 + s2) / dur, 4)] if s1 and s2 else [0.33, 0.66]
    return {"w": round(w, 1), "h": round(h, 1), "path": path, "sec": sec}

def status_segments(rc, T0, starts=()):
    segs = []; cur = None
    def close(t):
        nonlocal cur
        if cur: cur[2] = t; segs.append(cur); cur = None
    for m in sorted(rc, key=lambda m: m["date"]):
        t = ts(m["date"]) - T0; msg = (m.get("message") or "").upper(); flag = m.get("flag"); scope = m.get("scope")
        if "VSC DEPLOYED" in msg or "VIRTUAL SAFETY CAR DEPLOYED" in msg: close(t); cur = ["VSC", t, None]
        elif "SAFETY CAR DEPLOYED" in msg: close(t); cur = ["SC", t, None]
        elif cur and cur[0] == "SC" and "IN THIS LAP" in msg:
            nxt = [s for s in starts if s > t + 5]; close(min(nxt) if nxt else t + 90)
        elif flag == "RED" and scope == "Track": close(t); cur = ["RED", t, None]
        elif cur and cur[0] == "VSC" and "ENDING" in msg: close(t + 10)
        elif cur and flag in ("GREEN", "CLEAR") and scope == "Track": close(t)
    close(None)
    return [[s[0], r1(s[1]), r1(s[2])] for s in segs]

def build(sk, meta):
    drivers = load(sk, "drivers"); laps = load(sk, "laps"); pos = load(sk, "position")
    stints = load(sk, "stints"); pits = load(sk, "pit"); rc = load(sk, "race_control")
    radio = load(sk, "team_radio"); weather = load(sk, "weather"); res = load(sk, "session_result")
    ovt = load(sk, "overtakes")
    lap1 = [ts(l["date_start"]) for l in laps if l["lap_number"] == 1 and l.get("date_start")]
    T0 = min(lap1)
    rel = lambda s: r1(ts(s) - T0)

    D = []
    for d in drivers:
        D.append({"n": d["driver_number"], "c": d["name_acronym"], "f": d.get("first_name") or "", "l": (d.get("last_name") or "").title(),
                  "t": d.get("team_name") or "", "col": "#" + (d.get("team_colour") or "888888")})

    # laps per driver: [lap, start, dur, s1, s2, s3, st, pitOut]
    by = {}
    for l in laps:
        if not l.get("date_start"): continue
        by.setdefault(l["driver_number"], []).append(l)
    L = {}; ends = {}
    for n, ls in by.items():
        ls.sort(key=lambda l: l["lap_number"]); rows = []
        for i, l in enumerate(ls):
            st = ts(l["date_start"]) - T0
            dur = l.get("lap_duration")
            if dur is None and i + 1 < len(ls): dur = ts(ls[i + 1]["date_start"]) - ts(l["date_start"])
            rows.append([l["lap_number"], r3(st), r3(dur), r3(l.get("duration_sector_1")), r3(l.get("duration_sector_2")),
                         r3(l.get("duration_sector_3")), l.get("st_speed"), 1 if l.get("is_pit_out_lap") else 0])
        # fill gaps where laps are missing from the feed (interpolate between known lap starts)
        filled = []
        for i, r in enumerate(rows):
            filled.append(r)
            if i + 1 < len(rows):
                nx = rows[i + 1]; gap = nx[0] - r[0]
                if gap > 1 and r[1] is not None and nx[1] is not None:
                    step = (nx[1] - r[1]) / gap; r[2] = r3(step)
                    for k in range(1, gap):
                        filled.append([r[0] + k, r3(r[1] + step * k), r3(step), None, None, None, None, 0, 1])
        L[n] = filled

    # results
    R = []
    for r in sorted(res, key=lambda r: (r.get("position") or 99)):
        st = "DNF" if r.get("dnf") else "DNS" if r.get("dns") else "DSQ" if r.get("dsq") else None
        R.append([r.get("position"), r["driver_number"], r.get("number_of_laps"), r.get("gap_to_leader") if not isinstance(r.get("gap_to_leader"), list) else None, st, r.get("points") or 0, r3(r.get("duration")) if not isinstance(r.get("duration"), list) else None])
    # final lap for finishers lacking duration: approximate from result duration
    for r in res:
        n = r["driver_number"]; d = r.get("duration")
        if n in L and L[n] and L[n][-1][2] is None and isinstance(d, (int, float)):
            L[n][-1][2] = r3(d - L[n][-1][1]) if d - L[n][-1][1] > 30 else None
    for n, rows in L.items():
        if rows and rows[-1][2] is None:
            prev = [r[2] for r in rows[:-1] if r[2]]
            rows[-1][2] = r3(sum(prev[-3:]) / len(prev[-3:])) if prev else 100.0
            rows[-1].append(1)  # flagged as estimated

    P = sorted([[rel(p["date"]), p["driver_number"], p["position"]] for p in pos], key=lambda x: x[0])
    S = {}
    for s in stints:
        S.setdefault(s["driver_number"], []).append([s.get("lap_start"), s.get("lap_end"), (s.get("compound") or "UNKNOWN")[:1], s.get("tyre_age_at_start") or 0])
    for v in S.values(): v.sort(key=lambda x: x[0] or 0)
    PIT = [[rel(p["date"]), p["driver_number"], p.get("lap_number"), p.get("lane_duration") or p.get("pit_duration"), p.get("stop_duration")] for p in pits if p.get("date")]
    RC = [[rel(m["date"]), m.get("lap_number"), m.get("category"), m.get("flag"), m.get("message"), m.get("driver_number")] for m in sorted(rc, key=lambda m: m["date"])]
    RC = [m for m in RC if m[0] > -900]
    W = []; last = -1e9
    for w in sorted(weather, key=lambda w: w["date"]):
        t = ts(w["date"]) - T0
        if t - last >= 120 or not W:
            W.append([r1(t), w.get("air_temperature"), w.get("track_temperature"), w.get("rainfall"), w.get("wind_speed"), w.get("humidity")]); last = t
    OV = [[rel(o["date"]), o["overtaking_driver_number"], o["overtaken_driver_number"], o.get("position")] for o in ovt]
    RAD = [[rel(r["date"]), r["driver_number"], r["recording_url"]] for r in sorted(radio, key=lambda r: r["date"])]

    ref = json.load(open(f"{RAW}/{sk}/location_ref.json"))
    out = {"sk": sk, "type": meta["session_name"], "loc": meta["location"], "cc": meta["country_code"], "date": meta["date_start"],
           "t0": datetime.fromtimestamp(T0).astimezone().isoformat(), "track": track_from_ref(ref), "status": status_segments(rc, T0, sorted(r[1] for v in L.values() for r in v if r[1] is not None)),
           "drivers": D, "laps": L, "pos": P, "stints": S, "pits": PIT, "rc": RC, "weather": W, "ovt": OV, "radio": RAD, "result": R}
    return out

if __name__ == "__main__":
    sess = {s["session_key"]: s for s in json.load(open("sessions.json"))}
    for sk in map(int, sys.argv[1:]):
        o = build(sk, sess[sk])
        p = f"{OUT}/{sk}.json"
        json.dump(o, open(p, "w"), separators=(",", ":"))
        print(sk, o["type"], o["loc"], "drivers", len(o["drivers"]), "laps", sum(len(v) for v in o["laps"].values()), "status", o["status"], "radio", len(o["radio"]), f"{os.path.getsize(p)//1024}KB")
