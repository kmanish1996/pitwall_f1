#!/usr/bin/env python3
"""Keep watching OpenF1 through a race weekend so new sessions land within minutes, not hours.

GitHub runs scheduled workflows late (every 4-7 hours in practice), so a single check per run
leaves race results waiting for hours. This script is the whole update job:

  repeat until there is nothing left to wait for (or the run is nearly out of time):
    fetch finished sessions -> refresh timetables -> rebuild standings and pages -> commit and push -> ping IndexNow
    sleep a few minutes (longer while nothing is due)

Before the run's time limit it starts a fresh run of the same workflow (workflow_dispatch with the
job's own token) if a session is still pending or about to start, so coverage is continuous from
the first check of the weekend until the race data is in. The repo is public, so Actions minutes are free.

Run from the repo root in GitHub Actions. Locally: python3 scripts/watch_sessions.py --once  (one pass, no push)
"""
import argparse, json, os, subprocess, sys, time, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEEKEND = ("Practice 1", "Practice 2", "Practice 3", "Sprint Qualifying", "Qualifying", "Sprint", "Race")
SETTLE = timedelta(minutes=20)       # same as update_sessions.SETTLE_MIN
GIVE_UP = timedelta(hours=12)        # stop waiting for a session this long after it ended
BUSY_SLEEP = 5 * 60                  # while a session has ended but its data isn't in yet
MAX_RUN = timedelta(hours=5, minutes=30)   # the job's timeout is 6 h
PINGS = []                           # background IndexNow pings, finished before the run ends


def log(*a):
    print(datetime.now(timezone.utc).strftime("%H:%M:%S"), *a, flush=True)


def sh(cmd, check=True):
    log("$", cmd)
    return subprocess.run(cmd, shell=True, cwd=ROOT, check=check, text=True, capture_output=False)


def out(cmd):
    return subprocess.run(cmd, shell=True, cwd=ROOT, text=True, capture_output=True).stdout.strip()


def sessions(year):
    req = urllib.request.Request(f"https://api.openf1.org/v1/sessions?year={year}", headers={"User-Agent": "pitwall-watch"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return [s for s in json.load(r) if s.get("session_name") in WEEKEND and not s.get("is_cancelled")]
    except Exception as e:  # OpenF1 blocks free access while a session is live; try again next loop
        log("OpenF1 sessions not available:", str(e)[:120])
        return None


def imported():
    p = os.path.join(ROOT, "data", "index.json")
    return {x["sk"] for x in json.load(open(p))} if os.path.exists(p) else set()


def status(year, now):
    """(pending, next_start): sessions ended but not imported yet, and the next session's start."""
    S = sessions(year)
    if S is None:
        return None, None
    have = imported()
    pending, upcoming = [], []
    for s in S:
        st = datetime.fromisoformat(s["date_start"]); en = datetime.fromisoformat(s["date_end"])
        if st > now:
            upcoming.append(st)
        elif s["session_key"] not in have and now - en < GIVE_UP:
            pending.append(s)
    return pending, min(upcoming) if upcoming else None


def one_pass(push):
    """The old workflow's steps, once. Returns True if something was committed."""
    sh("python3 scripts/update_sessions.py", check=False)
    sh("python3 scripts/update_schedule.py", check=False)
    if out("git status --porcelain data"):
        sh("python3 scripts/update_standings.py")
        sh("python3 scripts/build_pages.py")
    elif out("git status --porcelain index.html"):
        sh("python3 scripts/build_pages.py")
    if not out("git status --porcelain data index.html"):
        log("no new sessions or timetable changes")
        return False
    if not push:
        log("changes made (not pushed: --once)")
        return True
    sh('git config user.name "pitwall-bot" && git config user.email "41898282+github-actions[bot]@users.noreply.github.com"')
    sh("git add -A && git commit -q -m 'Add newly finished sessions: replays, standings and pages'")
    for attempt in range(3):
        if subprocess.run("git push -q", shell=True, cwd=ROOT).returncode == 0:
            break
        log("push rejected; rebasing on the latest main")
        if subprocess.run("git pull -q --rebase", shell=True, cwd=ROOT).returncode != 0:
            # someone changed the same generated files: take theirs and rebuild on the next pass
            sh("git rebase --abort", check=False); sh("git reset -q --hard origin/main")
            return False
    else:
        return False
    # let Netlify deploy, then tell search engines (in the background so watching continues)
    PINGS.append(subprocess.Popen("sleep 90 && python3 scripts/indexnow.py", shell=True, cwd=ROOT))
    return True


def dispatch_again():
    tok, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    wf = os.environ.get("WATCH_WORKFLOW", "update-sessions.yml")
    if not tok or not repo:
        return
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/actions/workflows/{wf}/dispatches",
                                 data=json.dumps({"ref": os.environ.get("GITHUB_REF_NAME", "main")}).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"})
    try:
        urllib.request.urlopen(req, timeout=30); log("started a fresh watch run to carry on")
    except Exception as e:
        log("could not start a fresh run:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="one pass, no push, no waiting")
    ap.add_argument("--year", type=int, default=2026)
    a = ap.parse_args()
    if a.once:
        one_pass(push=False); return
    began = datetime.now(timezone.utc)
    while True:
        one_pass(push=True)
        now = datetime.now(timezone.utc)
        left = began + MAX_RUN - now
        pending, nxt = status(a.year, now)
        if pending is None:            # OpenF1 is blocking (a session is live): data will follow soon
            wait = BUSY_SLEEP
        elif pending:
            log("waiting for:", ", ".join(f'{s["location"]} {s["session_name"]}' for s in pending))
            due = min(datetime.fromisoformat(s["date_end"]) + SETTLE for s in pending)
            wait = max(BUSY_SLEEP, (due - now).total_seconds())
        elif nxt and nxt - now < timedelta(hours=30):
            # race weekend: stay on duty. Sleep until the next session should be importable,
            # or until this run is nearly out of time, then hand over to a fresh run.
            log("next session starts", nxt.isoformat())
            wait = max(BUSY_SLEEP, (nxt + timedelta(minutes=60) + SETTLE - now).total_seconds())
        else:
            log("no session in the next 30 hours; done (the schedule starts the next weekend's watch)")
            return
        if timedelta(seconds=wait) >= left - timedelta(minutes=3):
            if left > timedelta(minutes=10):
                log(f"sleeping {int((left - timedelta(minutes=4)).total_seconds() // 60)} min before handing over")
                time.sleep((left - timedelta(minutes=4)).total_seconds())
            dispatch_again(); log("handed over to a fresh run"); return
        log(f"sleeping {int(wait // 60)} min")
        time.sleep(wait)
        sh("git pull -q --rebase", check=False)


if __name__ == "__main__":
    try:
        main()
    finally:
        for p in PINGS: p.wait()
