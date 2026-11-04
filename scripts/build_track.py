#!/usr/bin/env python3
"""Build a 3D track file from one real lap in OpenF1.

Run from the repo root:
  python3 scripts/build_track.py --session 11230 --slug albert-park            # fastest lap of the session
  python3 scripts/build_track.py --session 11230 --driver 63 --lap 21 --slug albert-park

Writes data/tracks/<slug>.json with the circuit outline, elevation and the lap's telemetry
(speed, gear, throttle, brake) every few metres, plus detected corners and a few lap stats.
OpenF1 coordinates are in decimetres; everything written here is in metres.
"""
import argparse, bisect, json, math, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone

API = "https://api.openf1.org/v1/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEP = 5.0  # metres between samples in the output


def get(path, **q):
    url = API + path + "?" + "&".join(f"{k}={urllib.parse.quote(str(v), safe='<>:-.T+')}" for k, v in q.items())
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pitwall-track-builder"}), timeout=90) as r:
                return json.load(r)
        except Exception as e:  # rate limits and the occasional timeout
            if attempt == 3: raise
            time.sleep(3 * (attempt + 1))


def ts(s): return datetime.fromisoformat(s).timestamp()


def catmull(p0, p1, p2, p3, u):
    return tuple(0.5 * ((2 * b) + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u * u + (-a + 3 * b - 3 * c + d) * u ** 3)
                 for a, b, c, d in zip(p0, p1, p2, p3))


def smooth(vals, win):
    n, out = len(vals), []
    for i in range(n):  # the lap is a loop, so wrap around
        s = [vals[(i + k) % n] for k in range(-win, win + 1)]
        out.append(sum(s) / len(s))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", type=int, required=True)
    ap.add_argument("--driver", type=int)
    ap.add_argument("--lap", type=int)
    ap.add_argument("--slug", required=True)
    a = ap.parse_args()

    laps = [l for l in get("laps", session_key=a.session) if l.get("lap_duration")]
    if a.driver: laps = [l for l in laps if l["driver_number"] == a.driver]
    if a.lap: laps = [l for l in laps if l["lap_number"] == a.lap]
    lap = min(laps, key=lambda l: l["lap_duration"])
    drv = get("drivers", session_key=a.session, driver_number=lap["driver_number"])[0]
    meta = get("sessions", session_key=a.session)[0]
    t0, T = ts(lap["date_start"]), lap["lap_duration"]
    lo = datetime.fromtimestamp(t0 - 3, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    hi = datetime.fromtimestamp(t0 + T + 3, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    loc = get("location", session_key=a.session, driver_number=lap["driver_number"], **{"date>": lo, "date<": hi})
    car = get("car_data", session_key=a.session, driver_number=lap["driver_number"], **{"date>": lo, "date<": hi})

    # position samples (time, x, y, z) in metres, smoothed with a Catmull-Rom spline every 0.05 s
    pts = [(ts(p["date"]) - t0, p["x"] / 10, p["y"] / 10, p["z"] / 10) for p in loc]
    dense = []
    for i in range(1, len(pts) - 2):
        for k in range(10):
            dense.append(catmull(pts[i - 1], pts[i], pts[i + 1], pts[i + 2], k / 10))
    dense = [q for q in dense if 0 <= q[0] <= T]
    dist = [0.0]
    for p, q in zip(dense, dense[1:]): dist.append(dist[-1] + math.dist(p[1:3], q[1:3]))
    length = dist[-1] + math.dist(dense[-1][1:3], dense[0][1:3])

    # resample every STEP metres
    out = []
    s = 0.0
    while s < dist[-1]:
        i = max(1, bisect.bisect_left(dist, s)); f = (s - dist[i - 1]) / max(1e-6, dist[i] - dist[i - 1])
        out.append([a_ + (b_ - a_) * f for a_, b_ in zip(dense[i - 1], dense[i])])
        s += STEP
    xs, ys = [p[1] for p in out], [p[2] for p in out]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    zs = smooth([p[3] for p in out], 10)  # elevation arrives in whole decimetres, so smooth over ~100 m
    zmin = min(zs)

    tel = sorted((ts(c["date"]) - t0, c) for c in car)
    tt = [x[0] for x in tel]
    def at(t):
        i = min(len(tel) - 1, bisect.bisect_left(tt, t))
        if i and abs(tt[i - 1] - t) < abs(tt[i] - t): i -= 1
        return tel[i][1]

    rows = []
    for p, z in zip(out, zs):
        c = at(p[0])
        rows.append([round(p[1] - cx, 1), round(p[2] - cy, 1), round(z - zmin, 2), round(p[0], 3),
                     c["speed"], c["n_gear"], c["throttle"], 1 if c["brake"] else 0])

    # corners: peaks of heading change over +-15 m, at least ~60 m apart
    n = len(rows)
    def head(i, j): return math.atan2(rows[j % n][1] - rows[i % n][1], rows[j % n][0] - rows[i % n][0])
    turn = []
    for i in range(n):
        dh = (head(i, i + 3) - head(i - 3, i) + math.pi) % (2 * math.pi) - math.pi
        turn.append(dh)
    corners = []
    for i in range(n):
        w = [abs(turn[(i + k) % n]) for k in range(-12, 13)]
        if abs(turn[i]) > 0.1 and abs(turn[i]) == max(w) and 4 < i < n - 4:
            near = [rows[(i + k) % n] for k in range(-14, 15)]
            slow = min(near, key=lambda r: r[4])
            corners.append({"i": i, "dir": "L" if turn[i] > 0 else "R", "v": slow[4], "gear": slow[5]})

    lap_rows = [c for t, c in tel if 0 <= t <= T]
    gears = [c["n_gear"] for c in lap_rows]
    stats = {
        "vmax": max(c["speed"] for c in lap_rows), "vmin": min(c["speed"] for c in lap_rows),
        "fullThrottle": round(100 * sum(1 for c in lap_rows if c["throttle"] >= 98) / len(lap_rows)),
        "braking": round(100 * sum(1 for c in lap_rows if c["brake"]) / len(lap_rows)),
        "gearChanges": sum(1 for g1, g2 in zip(gears, gears[1:]) if g1 != g2 and g2 > 0),
        "elev": round(max(zs) - zmin, 1),
    }
    doc = {
        "slug": a.slug, "length": round(length), "lapTime": T,
        "source": {"session": a.session, "meeting": meta.get("meeting_key"), "year": int(meta["date_start"][:4]),
                   "sessionName": meta["session_name"], "driver": drv["name_acronym"],
                   "driverName": f'{drv["first_name"]} {drv["last_name"]}', "team": drv["team_name"],
                   "colour": "#" + (drv.get("team_colour") or "888888"), "lap": lap["lap_number"]},
        "stats": stats, "corners": corners,
        "cols": ["x", "y", "z", "t", "speed", "gear", "throttle", "brake"], "pts": rows,
    }
    os.makedirs(os.path.join(ROOT, "data", "tracks"), exist_ok=True)
    path = os.path.join(ROOT, "data", "tracks", f"{a.slug}.json")
    json.dump(doc, open(path, "w"), separators=(",", ":"))
    print(f"{path}: {len(rows)} points, {round(length)} m, {len(corners)} corners, lap {T}s by {drv['name_acronym']}, stats {stats}")


if __name__ == "__main__":
    main()
