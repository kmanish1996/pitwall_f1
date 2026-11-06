#!/usr/bin/env python3
"""Fill in the full weekend timetable (practice, sprint, qualifying, race) for upcoming rounds.

Run from the repo root:  python3 scripts/update_schedule.py [file.html ...]   (default: index.html)

Reads the 2026 session list from OpenF1 (free, no key) and rewrites the page's `const SESSIONS=[...]`
block from the last completed round onwards. If OpenF1 can't be reached, the page is left as it is.
Needs Node.js (it reads the page's own data with build_pages.app_data).
"""
import json, os, re, sys, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_pages import ROOT, app_data  # noqa: E402
from update_standings import round_of  # noqa: E402

YEAR = 2026
# OpenF1 session name -> (short code shown in the card, label)
NAMES = {
    "Practice 1": ("FP1", "Practice 1"), "Practice 2": ("FP2", "Practice 2"), "Practice 3": ("FP3", "Practice 3"),
    "Sprint Qualifying": ("SQ", "Sprint Qualifying"), "Sprint Shootout": ("SQ", "Sprint Qualifying"),
    "Sprint": ("SPR", "Sprint"), "Qualifying": ("Q", "Qualifying"), "Race": ("GP", "Grand Prix"),
}


def iso_z(s):
    return datetime.fromisoformat(s).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def fetch():
    req = urllib.request.Request(f"https://api.openf1.org/v1/sessions?year={YEAR}", headers={"User-Agent": "pitwall-schedule"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def build_rows(sessions, races, first_round):
    by_meeting = {}
    for s in sessions:
        if s.get("is_cancelled") or s["session_name"] not in NAMES: continue
        by_meeting.setdefault(s["meeting_key"], []).append(s)
    rows = []
    for ss in by_meeting.values():
        race = next((s for s in ss if s["session_name"] == "Race"), None)
        if not race: continue
        rd = round_of(race["date_start"], races)
        if rd is None or rd < first_round: continue
        for s in ss:
            k, n = NAMES[s["session_name"]]
            start = datetime.fromisoformat(s["date_start"]); end = datetime.fromisoformat(s["date_end"])
            mins = max(30, round((end - start).total_seconds() / 60)) if s["session_name"] != "Race" else 120
            rows.append((start.timestamp(), rd, k, n, iso_z(s["date_start"]), mins))
    rows.sort()
    return rows


def write(path, rows):
    s = open(path, encoding="utf-8").read()
    body = ",\n".join(f' {{rd:{rd},k:"{k}",n:"{n}",t:"{t}",m:{m}}}' for _, rd, k, n, t, m in rows)
    new, n = re.subn(r"(// Weekend sessions[^\n]*\n)?const SESSIONS=\[\n.*?\n\]\.map\(",
                     lambda _: "// Weekend sessions from OpenF1, written by scripts/update_schedule.py\n"
                               f"const SESSIONS=[\n{body}\n].map(", s, count=1, flags=re.S)
    if not n: raise SystemExit(f"SESSIONS block not found in {path}")
    if new != s:
        open(path, "w", encoding="utf-8").write(new)
    return new != s


def main():
    files = sys.argv[1:] or [os.path.join(ROOT, "index.html")]
    try:
        sessions = fetch()
    except Exception as e:  # keep the page as it is if OpenF1 is down
        print(f"OpenF1 not reachable ({e}); schedule left as it is"); return
    A = app_data()
    first = max(1, A["COMPLETED"])
    rows = build_rows(sessions, A["RACES"], first)
    if not rows:
        print("No sessions found; schedule left as it is"); return
    changed = [f for f in files if write(f, rows)]
    rounds = sorted({r[1] for r in rows})
    print(f"Schedule: {len(rows)} sessions for rounds {rounds[0]}-{rounds[-1]}" + (" (updated)" if changed else " (no change)"))


if __name__ == "__main__":
    main()
