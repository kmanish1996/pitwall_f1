#!/usr/bin/env python3
"""Recalculate the championship from the race and sprint results in data/, and write it into the page.

Run from the repo root:  python3 scripts/update_standings.py [file.html ...]   (default: index.html)

Updates, inside each HTML file: driver points and order, constructors' points, points per round,
race winners with race time and fastest lap, sprint winners, and the number of completed rounds.
Everything else in the page (schedule, lap records, text) is left alone.
Needs Node.js (it reads the page's own data with build_pages.app_data).
"""
import json, os, re, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_pages import ROOT, app_data, fmt_race  # noqa: E402


def round_of(date_iso, races):
    dt = datetime.fromisoformat(date_iso).timestamp(); best = None
    for r in races:
        diff = datetime.fromisoformat(r["race"].replace("Z", "+00:00")).timestamp() - dt
        if -6 * 3600 < diff < 4 * 86400 and (best is None or diff < best[0]): best = (diff, r["rd"])
    return best[1] if best else None


def fastest_lap(d):
    code = {x["n"]: x["c"] for x in d["drivers"]}; best = None
    for n, rows in d["laps"].items():
        for r in rows:  # [lap, start, dur, s1, s2, s3, speed, pitOut, (estimated)]
            if len(r) > 8 or r[0] < 2 or not r[2] or not (r[3] and r[4] and r[5]): continue
            if abs(r[3] + r[4] + r[5] - r[2]) > 0.05: continue  # only laps whose sectors add up
            if best is None or r[2] < best[0]: best = (round(r[2], 3), code.get(int(n)))
    return best


def compute(A):
    races, drivers = A["RACES"], A["DRIVERS"]
    team_of = {d["code"]: d["team"] for d in drivers}
    idx = json.load(open(os.path.join(ROOT, "data", "index.json")))
    by_round = {}
    for s in idx:
        if s["type"] in ("Race", "Sprint"):
            rd = round_of(s["date"], races)
            if rd: by_round.setdefault(rd, {})[s["type"]] = s["sk"]
    completed = 0
    while completed + 1 in by_round and "Race" in by_round[completed + 1]: completed += 1
    pts = {d["code"]: [0] * completed for d in drivers}
    results, sprint = {}, {}
    for rd in range(1, completed + 1):
        for kind, sk in by_round[rd].items():
            d = json.load(open(os.path.join(ROOT, "data", f"{sk}.json")))
            code = {x["n"]: x["c"] for x in d["drivers"]}
            for r in d["result"]:
                c = code.get(r[1])
                if c not in pts:
                    if c and r[5]: print(f"  note: {c} scored {r[5]} in round {rd} but isn't in DRIVERS; add them to the page to count it")
                    continue
                pts[c][rd - 1] += int(r[5] or 0)
            win = code.get(d["result"][0][1]) if d["result"] else None
            if kind == "Race" and win:
                fl = fastest_lap(d)
                results[rd] = [win, team_of.get(win, ""), fmt_race(d["result"][0][6]), fl[0] if fl else None, fl[1] if fl else None]
            elif kind == "Sprint" and win:
                sprint[rd] = [win, team_of.get(win, ""), d["loc"]]
    wins = {}
    for v in results.values(): wins[v[0]] = wins.get(v[0], 0) + 1
    total = {c: sum(v) for c, v in pts.items()}
    order = sorted(drivers, key=lambda d: (-total[d["code"]], -wins.get(d["code"], 0)))
    teams = {}
    for d in drivers: teams[d["team"]] = teams.get(d["team"], 0) + total[d["code"]]
    cons = sorted(teams.items(), key=lambda x: -x[1])
    return completed, order, total, pts, cons, results, sprint


def write(path, A, completed, order, total, pts, cons, results, sprint):
    s = open(path).read()
    rows = ",\n".join(f' [{json.dumps(d["code"])},{json.dumps(d["first"], ensure_ascii=False)},{json.dumps(d["last"], ensure_ascii=False)},{d["no"]},{json.dumps(d["nat"])},{json.dumps(d["team"])},{total[d["code"]]}]' for d in order)
    s, n1 = re.subn(r"const DRIVERS=\[\n.*?\n\]\.map\(", lambda m: f"const DRIVERS=[\n{rows}\n].map(", s, count=1, flags=re.S)
    s, n2 = re.subn(r"const CONSTRUCTORS=\[.*?\];", lambda m: "const CONSTRUCTORS=" + json.dumps([[t, p] for t, p in cons], ensure_ascii=False) + ";", s, count=1)
    per = ",\n".join(f' {d["code"]}:{json.dumps(pts[d["code"]])}' for d in order)
    s, n3 = re.subn(r"const PER_RACE=\{\n.*?\n\};", lambda m: f"const PER_RACE={{\n{per}\n}};", s, count=1, flags=re.S)
    s, n4 = re.subn(r"const SPRINT_WIN=\{.*?\};", lambda m: "const SPRINT_WIN=" + json.dumps({int(k): v for k, v in sprint.items()}, ensure_ascii=False).replace('"', '"') + ";", s, count=1)
    s, n5 = re.subn(r"const COMPLETED=\d+, TOTAL=(\d+);", lambda m: f"const COMPLETED={completed}, TOTAL={m.group(1)};", s, count=1)
    s, n6 = re.subn(r"const RACE_RESULTS=\{.*?\};", lambda m: "const RACE_RESULTS=" + json.dumps(results, ensure_ascii=False) + ";", s, count=1)
    if not all((n1, n2, n3, n4, n5, n6)):
        raise SystemExit(f"{path}: couldn't find every data block to update ({n1},{n2},{n3},{n4},{n5},{n6})")
    open(path, "w").write(s)


def main():
    files = sys.argv[1:] or [os.path.join(ROOT, "index.html")]
    A = app_data()
    completed, order, total, pts, cons, results, sprint = compute(A)
    for f in files: write(f, A, completed, order, total, pts, cons, results, sprint)
    leader = order[0]
    print(f"Standings after round {completed}: {leader['first']} {leader['last']} {total[leader['code']]} pts; "
          f"{len(results)} race winners, {len(sprint)} sprint winners")


if __name__ == "__main__":
    main()
