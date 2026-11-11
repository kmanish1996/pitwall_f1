#!/usr/bin/env python3
"""Career stats for the current drivers and teams, from F1DB (https://github.com/f1db/f1db, CC BY 4.0).

Reads F1DB's source data (YAML under src/data) and writes data/history.json, which build_pages.py
uses for the career sections of /drivers/* and /teams/*:

  drivers: every driver on the current grid -> career starts, wins, podiums, poles, fastest laps,
           points, titles, first race/win, best finish, season-by-season record, every team, and the
           head-to-head record against every team-mate they have had (qualifying and race).
  teams:   every current team -> its record under the current name, and the whole lineage
           (for example Audi = Sauber, BMW Sauber, Alfa Romeo, Kick Sauber, Audi).

Usage: python3 scripts/update_history.py [path/to/f1db]   (default: clones F1DB into a temp folder)
F1DB publishes a release a day or two after each race; the weekly workflow picks it up.
"""
import json, os, subprocess, sys, tempfile
from collections import defaultdict

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
Loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def load(p):
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return yaml.load(f, Loader=Loader)


def num(v):
    return v if isinstance(v, int) else None


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if not src:
        src = os.path.join(tempfile.mkdtemp(), "f1db")
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", "https://github.com/f1db/f1db", src], check=True)
        subprocess.run(["git", "-C", src, "sparse-checkout", "set", "src/data/drivers", "src/data/constructors", "src/data/seasons", "src/data/countries", "src/data/grands-prix"], check=True)
    D = os.path.join(src, "src", "data")
    version = subprocess.run(["git", "-C", src, "log", "-1", "--format=%s"], capture_output=True, text=True).stdout.strip()

    country = {f[:-4]: (load(os.path.join(D, "countries", f)) or {}).get("demonym") or (load(os.path.join(D, "countries", f)) or {}).get("name")
               for f in os.listdir(os.path.join(D, "countries"))}
    gp_name = {}
    for f in os.listdir(os.path.join(D, "grands-prix")):
        g = load(os.path.join(D, "grands-prix", f)) or {}
        gp_name[f[:-4]] = g.get("fullName") or g.get("name")
    cons = {f[:-4]: load(os.path.join(D, "constructors", f)) for f in os.listdir(os.path.join(D, "constructors"))}

    years = sorted(int(y) for y in os.listdir(os.path.join(D, "seasons")) if y.isdigit())
    cur = years[-1]
    # every race, in order
    races = []
    for y in years:
        rdir = os.path.join(D, "seasons", str(y), "races")
        if not os.path.isdir(rdir):
            continue
        for r in sorted(os.listdir(rdir)):
            meta = load(os.path.join(rdir, r, "race.yml")) or {}
            res = load(os.path.join(rdir, r, "race-results.yml"))
            if not res:
                continue  # not run yet
            races.append({"y": y, "rd": meta.get("round"), "gp": gp_name.get(meta.get("grandPrixId"), meta.get("grandPrixId")), "date": str(meta.get("date")),
                          "res": res, "q": load(os.path.join(rdir, r, "qualifying-results.yml")) or [],
                          "fl": load(os.path.join(rdir, r, "fastest-laps.yml")) or [],
                          "spr": load(os.path.join(rdir, r, "sprint-race-results.yml")) or [], "n_rounds": None})
    last = races[-1]
    season_rounds = defaultdict(int)
    for y in years:
        rdir = os.path.join(D, "seasons", str(y), "races")
        season_rounds[y] = len(os.listdir(rdir)) if os.path.isdir(rdir) else 0
    done_rounds = defaultdict(int)
    for r in races:
        done_rounds[r["y"]] += 1
    complete = {y for y in years if season_rounds[y] and done_rounds[y] == season_rounds[y]}

    # the current grid: drivers and teams entered this season
    ent = load(os.path.join(D, "seasons", str(cur), "entrants.yml")) or []
    grid_drivers, grid_teams = {}, {}
    for e in ent:
        grid_teams[e["constructorId"]] = e
        for dv in e.get("drivers") or []:
            if not dv.get("testDriver"):
                grid_drivers[dv["driverId"]] = e["constructorId"]

    champ_d, champ_c = {}, {}
    for y in complete:
        ds = load(os.path.join(D, "seasons", str(y), "driver-standings.yml")) or []
        cs = load(os.path.join(D, "seasons", str(y), "constructor-standings.yml")) or []
        if ds: champ_d[y] = ds[0]["driverId"]
        if cs: champ_c[y] = cs[0]["constructorId"]
    season_pos = {}
    for y in years:
        for row in load(os.path.join(D, "seasons", str(y), "driver-standings.yml")) or []:
            season_pos[(y, row["driverId"])] = (row.get("position"), row.get("points"))
        for row in load(os.path.join(D, "seasons", str(y), "constructor-standings.yml")) or []:
            season_pos[(y, "c:" + row["constructorId"])] = (row.get("position"), row.get("points"))

    # ---------- drivers ----------
    out_d = {}
    blank = lambda: {"starts": 0, "wins": 0, "podiums": 0, "poles": 0, "fl": 0, "points": 0.0, "sprintWins": 0, "dnfs": 0,
                     "best": None, "bestN": 0, "first": None, "firstWin": None, "lastWin": None, "teams": [], "seasons": {}, "h2h": {}}
    S = {d: blank() for d in grid_drivers}
    for r in races:
        pole = next((x["driverId"] for x in r["q"] if x.get("position") == 1), None)
        flid = next((x["driverId"] for x in r["fl"] if x.get("position") == 1), None)
        qpos = {x["driverId"]: num(x.get("position")) for x in r["q"]}
        team_of = {}
        for x in r["res"]:
            d = x["driverId"]; team_of[d] = x["constructorId"]
            if d not in S or x.get("position") in ("DNQ", "DNPQ", "EX", "DNP"):
                continue
            s = S[d]; p = num(x.get("position"))
            started = x.get("position") != "DNS"
            if started:
                s["starts"] += 1
                if s["first"] is None: s["first"] = {"y": r["y"], "gp": r["gp"], "pos": p}
            s["points"] += float(x.get("points") or 0)
            if p == 1:
                s["wins"] += 1; w = {"y": r["y"], "gp": r["gp"]}
                if s["firstWin"] is None: s["firstWin"] = w
                s["lastWin"] = w
            if p and p <= 3: s["podiums"] += 1
            if x.get("position") == "DNF": s["dnfs"] += 1
            if p and (s["best"] is None or p < s["best"]): s["best"], s["bestN"] = p, 0
            if p and p == s["best"]: s["bestN"] += 1
            if pole == d: s["poles"] += 1
            if flid == d: s["fl"] += 1
            sy = s["seasons"].setdefault(r["y"], {"team": x["constructorId"], "starts": 0, "wins": 0, "podiums": 0})
            sy["starts"] += 1 if started else 0
            sy["wins"] += 1 if p == 1 else 0
            sy["podiums"] += 1 if p and p <= 3 else 0
            if not s["teams"] or s["teams"][-1][0] != x["constructorId"]:
                s["teams"].append([x["constructorId"], r["y"], r["y"]])
            else:
                s["teams"][-1][2] = r["y"]
        for x in r["spr"]:
            if x["driverId"] in S:
                S[x["driverId"]]["points"] += float(x.get("points") or 0)
                if x.get("position") == 1: S[x["driverId"]]["sprintWins"] += 1
        # team-mate head-to-heads: drivers of the same team in this race
        by_team = defaultdict(list)
        for x in r["res"]:
            if x.get("position") not in ("DNQ", "DNPQ", "EX", "DNP", "DNS"):
                by_team[x["constructorId"]].append(x)
        for rows in by_team.values():
            for a in rows:
                if a["driverId"] not in S:
                    continue
                for b in rows:
                    if b is a:
                        continue
                    h = S[a["driverId"]]["h2h"].setdefault(b["driverId"], {"races": 0, "qa": 0, "qb": 0, "ra": 0, "rb": 0, "pa": 0.0, "pb": 0.0, "from": r["y"], "to": r["y"], "team": a["constructorId"]})
                    h["races"] += 1; h["to"] = r["y"]
                    qa, qb = qpos.get(a["driverId"]), qpos.get(b["driverId"])
                    if qa and qb:
                        h["qa" if qa < qb else "qb"] += 1
                    pa, pb = num(a.get("position")), num(b.get("position"))
                    if pa or pb:
                        if pa and (not pb or pa < pb): h["ra"] += 1
                        elif pb: h["rb"] += 1
                    h["pa"] += float(a.get("points") or 0); h["pb"] += float(b.get("points") or 0)

    dnames = {}
    for d, s in S.items():
        info = load(os.path.join(D, "drivers", f"{d}.yml")) or {}
        mates = {}
        for m, h in s["h2h"].items():
            mi = dnames.get(m) or load(os.path.join(D, "drivers", f"{m}.yml")) or {}
            dnames[m] = mi
            mates[m] = {**h, "name": mi.get("name", m), "code": mi.get("abbreviation"), "pa": round(h["pa"], 1), "pb": round(h["pb"], 1)}
        titles = sorted(y for y, w in champ_d.items() if w == d)
        out_d[info.get("abbreviation") or d] = {
            "id": d, "name": info.get("name"), "full": info.get("fullName"), "dob": str(info.get("dateOfBirth") or ""),
            "born": info.get("placeOfBirth"), "nat": country.get(info.get("nationalityCountryId")),
            **{k: s[k] for k in ("starts", "wins", "podiums", "poles", "fl", "sprintWins", "dnfs", "best", "bestN", "first", "firstWin", "lastWin")},
            "points": round(s["points"], 1), "titles": titles,
            "teams": [[(cons.get(t) or {}).get("name", t), a, b] for t, a, b in s["teams"]],
            "seasons": [[y, (cons.get(v["team"]) or {}).get("name", v["team"]), *(season_pos.get((y, d)) or (None, None)), v["starts"], v["wins"], v["podiums"]]
                        for y, v in sorted(s["seasons"].items())],
            "h2h": sorted(mates.values(), key=lambda h: (-h["to"], -h["races"])),
        }

    # ---------- teams ----------
    out_t = {}
    for cid in grid_teams:
        c = cons.get(cid) or {}
        # the lineage, with the years each name was used (the same id can return later, e.g. Alfa Romeo 1950-51 vs 2019-23)
        spans = [(x["constructorId"], x.get("yearFrom") or 0, x.get("yearTo") or 9999) for x in c.get("chronology") or []] or [(cid, 0, 9999)]
        def record(spans):
            ok = lambda cid_, y: any(cid_ == i and a <= y <= b for i, a, b in spans)
            t = {"entries": 0, "wins": 0, "podiums": 0, "poles": 0, "oneTwos": 0, "fl": 0, "first": None, "titles": [], "driverTitles": []}
            for r in races:
                rows = [x for x in r["res"] if ok(x["constructorId"], r["y"])]
                if not rows:
                    continue
                t["entries"] += 1
                if t["first"] is None: t["first"] = {"y": r["y"], "gp": r["gp"]}
                ps = sorted(p for p in (num(x.get("position")) for x in rows) if p)
                if ps and ps[0] == 1: t["wins"] += 1
                if ps[:2] == [1, 2]: t["oneTwos"] += 1
                t["podiums"] += sum(1 for p in ps if p <= 3)
                if any(x.get("position") == 1 and ok(x["constructorId"], r["y"]) for x in r["q"]): t["poles"] += 1
                if any(x.get("position") == 1 and ok(x["constructorId"], r["y"]) for x in r["fl"]): t["fl"] += 1
            t["titles"] = sorted(y for y, w in champ_c.items() if ok(w, y))
            # drivers' titles won in this team's car
            for y, w in champ_d.items():
                if any(x["driverId"] == w and ok(x["constructorId"], y) for r in races if r["y"] == y for x in r["res"]):
                    t["driverTitles"].append([y, (dnames.get(w) or load(os.path.join(D, "drivers", f"{w}.yml")) or {}).get("name", w)])
            t["driverTitles"].sort()
            return t
        own = record([(cid, 0, 9999)])
        whole = record(spans) if len(spans) > 1 else None
        out_t[cid] = {"name": c.get("name"), "id": cid, "full": c.get("fullName"), "country": country.get(c.get("countryId")),
                      "own": own, "lineage": [[(cons.get(x["constructorId"]) or {}).get("name", x["constructorId"]), x.get("yearFrom"), x.get("yearTo")] for x in c.get("chronology") or []],
                      "all": whole,
                      "seasons": [[y, *season_pos.get((y, "c:" + cid), (None, None))] for y in years if (y, "c:" + cid) in season_pos]}

    data = {"source": "F1DB", "license": "CC BY 4.0", "url": "https://github.com/f1db/f1db", "version": version,
            "through": {"y": last["y"], "rd": last["rd"], "gp": last["gp"], "date": last["date"]},
            "drivers": out_d, "teams": out_t}
    p = os.path.join(ROOT, "data", "history.json")
    txt = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    old = open(p, encoding="utf-8").read() if os.path.exists(p) else None
    if old != txt:
        open(p, "w", encoding="utf-8").write(txt)
    print(f"history.json: {len(out_d)} drivers, {len(out_t)} teams, through {last['y']} round {last['rd']} ({last['gp']}); {version}")


if __name__ == "__main__":
    main()
