#!/usr/bin/env python3
"""Pre-season testing tracker: laps and best times for every driver and team, day by day (OpenF1).

Writes data/testing-<year>.json, which build_pages.py turns into /f1-<year>-testing/.
Only finished test days are read (OpenF1 blocks free access while a session is live), and a day
already stored is not fetched again unless --force is given.

Usage: python3 scripts/update_testing.py [year ...] [--force]     (default: this year and next)
"""
import json, os, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.openf1.org/v1"
SETTLE = timedelta(minutes=20)


def get(path):
    for attempt in range(4):
        try:
            req = urllib.request.Request(API + path, headers={"User-Agent": "pitwall-testing"})
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def day(sk):
    drivers = {d["driver_number"]: d for d in get(f"/drivers?session_key={sk}")}
    laps = get(f"/laps?session_key={sk}")
    stints = get(f"/stints?session_key={sk}")
    def compound(n, lap):
        for s in stints:
            if s["driver_number"] == n and (s.get("lap_start") or 0) <= lap <= (s.get("lap_end") or 10 ** 6):
                return (s.get("compound") or "")[:1] or None
        return None
    per = {}
    for l in laps:
        n = l["driver_number"]
        p = per.setdefault(n, {"laps": 0, "best": None, "bestLap": None})
        p["laps"] += 1
        t = l.get("lap_duration")
        if t and not l.get("is_pit_out_lap") and (p["best"] is None or t < p["best"]):
            p["best"], p["bestLap"] = round(t, 3), l["lap_number"]
    rows = []
    for n, p in per.items():
        d = drivers.get(n, {})
        rows.append({"n": n, "code": d.get("name_acronym") or str(n), "name": d.get("full_name", "").title() if d.get("full_name") else str(n),
                     "team": d.get("team_name") or "", "col": "#" + (d.get("team_colour") or "888888"), "laps": p["laps"], "best": p["best"],
                     "tyre": compound(n, p["bestLap"]) if p["bestLap"] else None})
    rows.sort(key=lambda r: (r["best"] is None, r["best"] or 0))
    return rows


def update(year, force=False):
    p = os.path.join(ROOT, "data", f"testing-{year}.json")
    old = json.load(open(p)) if os.path.exists(p) else {"year": year, "days": []}
    meetings = [m for m in get(f"/meetings?year={year}") if "test" in (m.get("meeting_name") or "").lower()]
    if not meetings:
        print(f"testing {year}: no test meetings in OpenF1 yet"); return False
    now = datetime.now(timezone.utc)
    have = {d["sk"]: d for d in old["days"]}
    days, changed = [], False
    for m in sorted(meetings, key=lambda m: m["date_start"]):
        for s in sorted(get(f"/sessions?meeting_key={m['meeting_key']}"), key=lambda s: s["date_start"]):
            if s.get("is_cancelled"):
                continue
            end = datetime.fromisoformat(s["date_end"])
            entry = {"sk": s["session_key"], "test": m["meeting_name"], "mk": m["meeting_key"], "name": s["session_name"],
                     "date": s["date_start"], "end": s["date_end"], "circuit": s.get("circuit_short_name"), "loc": s.get("location")}
            if s["session_key"] in have and have[s["session_key"]].get("rows") and not force:
                days.append(have[s["session_key"]]); continue
            if end + SETTLE > now:
                days.append(entry); continue  # not run yet (or still running): listed without times
            try:
                entry["rows"] = day(s["session_key"])
                changed = True
                print(f"testing {year}: {m['meeting_name']} {s['session_name']}: {len(entry['rows'])} drivers")
            except Exception as e:
                print(f"testing {year}: {s['session_name']} not available yet ({str(e)[:80]})")
            days.append(entry)
    out = {"year": year, "source": "OpenF1", "days": days}
    if out != old:
        json.dump(out, open(p, "w"), ensure_ascii=False, separators=(",", ":"))
        changed = True
    return changed


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    yr = datetime.now(timezone.utc).year
    for y in [int(a) for a in args] or [yr, yr + 1]:
        update(y, "--force" in sys.argv)
