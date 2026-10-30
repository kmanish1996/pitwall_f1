#!/usr/bin/env python3
"""Add every finished 2026 session (practice, qualifying, sprint, race) to the Race Centre.

Run from the repo root:  python3 scripts/update_sessions.py [--year 2026] [--only SESSION_KEY ...]

For each session that ended a while ago and isn't in data/index.json yet, it pulls the data
from the free OpenF1 API, packs it into data/<session_key>.json and adds it to the index.
It exits quietly (status 0) when OpenF1 is blocking free access because a session is live,
and it waits for OpenF1 to finish backfilling incomplete lap data, so it is safe to run on a schedule.
"""
import argparse, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.openf1.org/v1/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(ROOT, ".cache", "openf1")
SETTLE_MIN = 40          # wait this long after a session ends before importing it
BACKFILL_HOURS = 12      # if laps look incomplete, keep waiting this long for OpenF1 to fill gaps
RACE_KINDS = ("Race", "Sprint")
ENDPOINTS = ["drivers", "laps", "position", "stints", "pit", "race_control", "team_radio", "weather", "session_result", "overtakes"]


class LiveBlock(Exception):
    """OpenF1 restricts free access while a session is live."""


def get(path):
    url = API + path
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pitwall-session-updater"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []
            if e.code == 401:
                raise LiveBlock(e.read().decode("utf-8", "replace")[:200])
            if e.code == 429:
                time.sleep(5 + attempt * 5); continue
            print(f"  retry {path[:70]}: HTTP {e.code}", file=sys.stderr); time.sleep(2 + attempt * 3)
        except Exception as e:
            print(f"  retry {path[:70]}: {e}", file=sys.stderr); time.sleep(2 + attempt * 3)
    raise RuntimeError(f"OpenF1 request kept failing: {path}")


def ts(s): return datetime.fromisoformat(s).timestamp()
def r1(x): return None if x is None else round(x, 1)
def r3(x): return None if x is None else round(x, 3)
def num(x): return x if isinstance(x, (int, float)) else None


def fetch_session(sk):
    d = os.path.join(CACHE, str(sk)); os.makedirs(d, exist_ok=True)
    raw = {}
    for ep in ENDPOINTS:
        f = os.path.join(d, ep + ".json")
        if os.path.exists(f):
            raw[ep] = json.load(open(f)); continue
        raw[ep] = get(f"{ep}?session_key={sk}") or []
        json.dump(raw[ep], open(f, "w")); time.sleep(0.4)
    return raw


def ref_lap_points(sk, laps, pits):
    """Car positions for one clean, fast lap, used to draw the track map."""
    pitset = {(p["driver_number"], p.get("lap_number")) for p in pits}
    cand = [l for l in laps if l.get("lap_duration") and l.get("date_start") and l["lap_number"] > 1
            and not l.get("is_pit_out_lap") and (l["driver_number"], l["lap_number"]) not in pitset
            and (l["driver_number"], l["lap_number"] - 1) not in pitset]
    cand.sort(key=lambda l: l["lap_duration"])
    for l in cand[:6]:
        t0 = datetime.fromisoformat(l["date_start"]).astimezone(timezone.utc).replace(tzinfo=None)
        t1 = t0 + timedelta(seconds=l["lap_duration"] + 0.5)
        q = (f"location?session_key={sk}&driver_number={l['driver_number']}"
             f"&date>={urllib.parse.quote(t0.isoformat())}&date<={urllib.parse.quote(t1.isoformat())}")
        pts = get(q)
        if pts and len(pts) > 100:
            return {"lap": l, "pts": pts}
        time.sleep(0.4)
    return None


def track_from_ref(ref):
    pts, lap = ref["pts"], ref["lap"]
    t0 = ts(lap["date_start"]); dur = lap["lap_duration"]
    raw = [(ts(p["date"]) - t0, p["x"], p["y"]) for p in pts]
    raw = [p for p in raw if -0.3 <= p[0] <= dur + 0.3]
    clean = []
    for p in raw:
        if clean and p[1] == clean[-1][1] and p[2] == clean[-1][2]: continue
        clean.append(p)
    xs = [p[1] for p in clean]; ys = [p[2] for p in clean]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    sc = 1000 / max(maxx - minx, maxy - miny)
    path = [[round((p[1] - minx) * sc, 1), round((maxy - p[2]) * sc, 1), round(max(0, min(1, p[0] / dur)), 4)] for p in clean]
    for i in range(1, len(path)):
        if path[i][2] < path[i - 1][2]: path[i][2] = path[i - 1][2]
    s1, s2 = lap.get("duration_sector_1"), lap.get("duration_sector_2")
    sec = [round(s1 / dur, 4), round((s1 + s2) / dur, 4)] if s1 and s2 else [0.33, 0.66]
    return {"w": round((maxx - minx) * sc, 1), "h": round((maxy - miny) * sc, 1), "path": path, "sec": sec}


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


def quali_phases(rc, T0, session_end):
    """[[phase, start, end]] for Q1/Q2/Q3 (or SQ1-3), from race control's qualifying_phase tags."""
    by = {}
    for m in rc:
        q = m.get("qualifying_phase")
        if not q: continue
        t = ts(m["date"]) - T0
        e = by.setdefault(q, {"start": t, "end": t, "chq": None})
        e["start"] = min(e["start"], t); e["end"] = max(e["end"], t)
        if (m.get("flag") or "").upper() == "CHEQUERED": e["chq"] = t
    out = []; keys = sorted(by)
    for i, q in enumerate(keys):
        e = by[q]
        end = e["chq"] if e["chq"] is not None else (by[keys[i + 1]]["start"] if i + 1 < len(keys) else session_end)
        out.append([q, r1(e["start"]), r1(end)])
    return out


def pack(sk, meta, raw, track):
    kind = "race" if meta["session_name"] in RACE_KINDS else "timed"
    laps = [l for l in raw["laps"] if l.get("date_start")]
    if kind == "race":
        lap1 = [ts(l["date_start"]) for l in laps if l["lap_number"] == 1]
        T0 = min(lap1)
    else:
        T0 = ts(meta["date_start"])
    rel = lambda s: r1(ts(s) - T0)

    D = [{"n": d["driver_number"], "c": d["name_acronym"], "f": d.get("first_name") or "", "l": (d.get("last_name") or "").title(),
          "t": d.get("team_name") or "", "col": "#" + (d.get("team_colour") or "888888")} for d in raw["drivers"]]

    by = {}
    for l in laps: by.setdefault(l["driver_number"], []).append(l)
    L = {}
    for n, ls in by.items():
        ls.sort(key=lambda l: l["lap_number"])
        known = sorted(l["lap_duration"] for l in ls if l.get("lap_duration"))
        med = known[len(known) // 2] if known else 100.0
        rows = []
        for i, l in enumerate(ls):
            st = ts(l["date_start"]) - T0; dur = l.get("lap_duration"); est = 0
            if dur is None:
                gap = ts(ls[i + 1]["date_start"]) - ts(l["date_start"]) if i + 1 < len(ls) else None
                if kind == "race":
                    dur = gap
                else:  # practice/quali: a lap without a time is an out- or in-lap; don't stretch it over garage time
                    dur = min(gap, med * 1.35) if gap else med * 1.35
                est = 1
            rows.append([l["lap_number"], r3(st), r3(dur), r3(l.get("duration_sector_1")), r3(l.get("duration_sector_2")),
                         r3(l.get("duration_sector_3")), l.get("st_speed"), 1 if l.get("is_pit_out_lap") else 0] + ([1] if est else []))
        if kind == "race":  # interpolate laps missing from the feed between known lap starts
            filled = []
            for i, r in enumerate(rows):
                filled.append(r)
                if i + 1 < len(rows):
                    nx = rows[i + 1]; gap = nx[0] - r[0]
                    if gap > 1 and r[1] is not None and nx[1] is not None:
                        step = (nx[1] - r[1]) / gap; r[2] = r3(step)
                        for k in range(1, gap):
                            filled.append([r[0] + k, r3(r[1] + step * k), r3(step), None, None, None, None, 0, 1])
            rows = filled
        L[n] = rows

    res = raw["session_result"]
    R = []
    for r in sorted(res, key=lambda r: (r.get("position") or 99)):
        st = "DNF" if r.get("dnf") else "DNS" if r.get("dns") else "DSQ" if r.get("dsq") else None
        dur = r.get("duration"); gap = r.get("gap_to_leader")
        dur = [r3(num(x)) for x in dur] if isinstance(dur, list) else r3(num(dur))
        gap = [r3(num(x)) if num(x) is not None else x for x in gap] if isinstance(gap, list) else (r3(gap) if num(gap) is not None else gap)
        R.append([r.get("position"), r["driver_number"], r.get("number_of_laps"), gap, st, r.get("points") or 0, dur])
    if kind == "race":
        for n, rows in L.items():
            if rows and rows[-1][2] is None:
                prev = [x[2] for x in rows[:-1] if x[2]]
                rows[-1][2] = r3(sum(prev[-3:]) / len(prev[-3:])) if prev else 100.0
                if len(rows[-1]) < 9: rows[-1].append(1)

    rc = sorted(raw["race_control"], key=lambda m: m["date"])
    W = []; last = -1e9
    for w in sorted(raw["weather"], key=lambda w: w["date"]):
        t = ts(w["date"]) - T0
        if t - last >= 120 or not W:
            W.append([r1(t), w.get("air_temperature"), w.get("track_temperature"), w.get("rainfall"), w.get("wind_speed"), w.get("humidity")]); last = t

    start = ts(meta["date_start"]) - T0; end = ts(meta["date_end"]) - T0
    starts = sorted(r[1] for v in L.values() for r in v if r[1] is not None)
    out = {
        "sk": sk, "mk": meta["meeting_key"], "type": meta["session_name"], "kind": kind,
        "loc": meta["location"], "cc": meta["country_code"], "date": meta["date_start"],
        "start": r1(start), "end": r1(end), "track": track,
        "status": status_segments(rc, T0, starts),
        "phases": quali_phases(rc, T0, end) if "Qualifying" in meta["session_name"] else [],
        "drivers": D, "laps": L,
        "pos": sorted([[rel(p["date"]), p["driver_number"], p["position"]] for p in raw["position"]], key=lambda x: x[0]),
        "stints": {},
        "pits": [[rel(p["date"]), p["driver_number"], p.get("lap_number"), p.get("lane_duration") or p.get("pit_duration"), p.get("stop_duration")]
                 for p in raw["pit"] if p.get("date")],
        "rc": [m for m in ([rel(m["date"]), m.get("lap_number"), m.get("category"), m.get("flag"), m.get("message"), m.get("driver_number")] for m in rc) if m[0] > start - 900],
        "weather": W,
        "ovt": [[rel(o["date"]), o["overtaking_driver_number"], o["overtaken_driver_number"], o.get("position")] for o in raw["overtakes"]] if kind == "race" else [],
        "radio": [[rel(r["date"]), r["driver_number"], r["recording_url"]] for r in sorted(raw["team_radio"], key=lambda r: r["date"])],
        "result": R,
    }
    for s in raw["stints"]:
        out["stints"].setdefault(str(s["driver_number"]), []).append([s.get("lap_start"), s.get("lap_end"), (s.get("compound") or "UNKNOWN")[:1], s.get("tyre_age_at_start") or 0])
    for v in out["stints"].values(): v.sort(key=lambda x: x[0] or 0)
    return out


def complete_enough(meta, raw):
    """True when lap data looks complete, or when we've waited long enough for OpenF1 to backfill it."""
    laps = len([l for l in raw["laps"] if l.get("date_start")])
    expected = sum((r.get("number_of_laps") or 0) for r in raw["session_result"])
    waited = datetime.now(timezone.utc) - datetime.fromisoformat(meta["date_end"])
    if laps == 0 or not raw["session_result"]:
        return False
    if expected and laps < 0.9 * expected and waited < timedelta(hours=BACKFILL_HOURS):
        print(f"  only {laps}/{expected} laps so far; waiting for OpenF1 to fill the gaps")
        return False
    return True


def track_for(meta, sk, raw, index):
    """Reuse the track map from another session at the same event when we have one."""
    for s in index:
        p = os.path.join(DATA, f"{s['sk']}.json")
        if os.path.exists(p):
            d = json.load(open(p))
            if d.get("mk") == meta["meeting_key"] or (not d.get("mk") and d.get("loc") == meta["location"]):
                return d["track"]
    ref = ref_lap_points(sk, raw["laps"], raw["pit"])
    return track_from_ref(ref) if ref else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    ap.add_argument("--only", type=int, nargs="*", help="only these session keys")
    ap.add_argument("--now", help="pretend the current UTC time is this (ISO), for testing")
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    idx_path = os.path.join(DATA, "index.json")
    index = json.load(open(idx_path)) if os.path.exists(idx_path) else []
    have = {s["sk"] for s in index}
    now = datetime.fromisoformat(a.now) if a.now else datetime.now(timezone.utc)

    try:
        sessions = get(f"sessions?year={a.year}")
    except LiveBlock as e:
        print("OpenF1 is limiting free access while a session is live. Nothing to do yet."); return 0

    todo = [s for s in sessions if not s.get("is_cancelled") and s["session_key"] not in have
            and datetime.fromisoformat(s["date_end"]) + timedelta(minutes=SETTLE_MIN) < now
            and (not a.only or s["session_key"] in a.only)]
    todo.sort(key=lambda s: s["date_start"])
    if not todo:
        print("No new finished sessions."); return 0

    added = 0
    for meta in todo:
        sk = meta["session_key"]
        print(f"{sk} {meta['location']} {meta['session_name']} ({meta['date_start'][:10]})")
        try:
            raw = fetch_session(sk)
            if not complete_enough(meta, raw):
                continue
            track = track_for(meta, sk, raw, index)
            if not track:
                print("  no usable car-position data for the track map yet; will retry"); continue
            out = pack(sk, meta, raw, track)
        except LiveBlock:
            print("OpenF1 started limiting free access (a session went live). Stopping for now."); break
        json.dump(out, open(os.path.join(DATA, f"{sk}.json"), "w"), separators=(",", ":"))
        laps_max = max([r[2] or 0 for r in out["result"]] or [0])
        index = [s for s in index if s["sk"] != sk] + [{"sk": sk, "type": out["type"], "kind": out["kind"], "date": out["date"],
                                                        "laps": laps_max, "radio": len(out["radio"])}]
        json.dump(index, open(idx_path, "w"), separators=(",", ":"))
        added += 1
        print(f"  added: {sum(len(v) for v in out['laps'].values())} laps, {len(out['radio'])} radio clips")
    print(f"Done. {added} session(s) added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
