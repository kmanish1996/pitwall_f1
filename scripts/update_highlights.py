#!/usr/bin/env python3
"""Find the official highlights video for every session on the FORMULA 1 YouTube channel.

Writes data/highlights.json:  {"year": 2026, "rounds": {"21": {"Practice 1": {"id": "...", "t": "title", "p": "2026-11-20T..."}}}}

Where the videos come from:
  1. data/highlights-manual.json: links added by hand ({"21": {"Practice 1": "https://youtu.be/..."}}); these always win.
  2. The channel's public RSS feed: its 15 newest uploads, no key needed. Run on every watcher pass during
     race weekends, this picks up each highlights video soon after F1 posts it.
  3. If a YOUTUBE_API_KEY is set (a free YouTube Data API v3 key, stored as a GitHub secret), the whole
     season of uploads is read once, so earlier rounds get their highlights too. Costs ~1 quota unit per 50 videos.

A video is matched to a session only when its title says "Highlights", names this season's year and the
Grand Prix, and names the session (FP1, Qualifying, Sprint, Race ...). Extended cuts and other videos
(onboards, interviews, analysis) are ignored, so nothing unrelated gets attached.

Usage: python3 scripts/update_highlights.py [--year 2026]
"""
import argparse, html, json, os, re, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
CHANNEL = "UCB_qr75-ydFVKSF9Dmo6izg"     # FORMULA 1 (youtube.com/@Formula1)
UA = {"User-Agent": "Mozilla/5.0 (pitwallf1.in highlights finder)", "Accept-Language": "en"}

# title words -> our session names (longest first, so "Sprint Qualifying" wins over "Sprint" and "Qualifying")
SESSIONS = [
    (r"sprint\s+(qualifying|shootout)|\bsq\b", "Sprint Qualifying"),
    (r"\bfp\s*1\b|practice\s*1|first\s+practice", "Practice 1"),
    (r"\bfp\s*2\b|practice\s*2|second\s+practice", "Practice 2"),
    (r"\bfp\s*3\b|practice\s*3|third\s+practice", "Practice 3"),
    (r"\bsprint\b", "Sprint"),
    (r"\bqualifying\b|\bquali\b", "Qualifying"),
    (r"\brace\b|grand\s+prix\s+highlights", "Race"),
]
SKIP = re.compile(r"extended|onboard|team\s+radio|reaction|analysis|interview|press|preview|best\s+of|top\s+10|recap|shorts|#shorts|f1\s*academy|\bf[23]\b|esports|kids", re.I)


def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def vid_id(v):
    m = re.search(r"(?:v=|youtu\.be/|/embed/|/shorts/|/live/)([\w-]{11})", v or "") or re.fullmatch(r"([\w-]{11})", v or "")
    return m.group(1) if m else None


def races():
    import build_pages as B
    A = B.app_data()
    long = lambda r: A["LONG_NAMES"].get(str(r["rd"])) or r["name"].replace(" GP", " Grand Prix")
    return [{"rd": r["rd"], "names": {long(r).lower(), r["name"].lower().replace(" gp", " grand prix")}} for r in A["RACES"]], A


def match(title, year, R):
    t = html.unescape(title)
    tl = t.lower()
    if "highlight" not in tl or str(year) not in tl or SKIP.search(t):
        return None
    rd = next((r["rd"] for r in R if any(n in tl for n in r["names"])), None)
    if rd is None:
        return None
    head = tl.split("|")[0] if "|" in tl else tl   # "FP1 Highlights | 2026 Las Vegas Grand Prix"
    sess = next((name for rx, name in SESSIONS if re.search(rx, head)), None)
    if sess is None and "|" in tl:
        sess = next((name for rx, name in SESSIONS if re.search(rx, tl)), None)
    return (rd, sess) if sess else None


def from_rss():
    xml = get(f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}")
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    out = []
    for e in ET.fromstring(xml).findall("a:entry", ns):
        out.append({"id": e.find("yt:videoId", ns).text, "t": e.find("a:title", ns).text or "", "p": e.find("a:published", ns).text or ""})
    return out


def from_api(key, since):
    """Every upload since the start of the season, via the channel's uploads playlist."""
    pl = "UU" + CHANNEL[2:]
    out, token = [], ""
    for _ in range(80):
        q = {"part": "snippet", "playlistId": pl, "maxResults": 50, "key": key}
        if token: q["pageToken"] = token
        d = json.loads(get("https://www.googleapis.com/youtube/v3/playlistItems?" + urllib.parse.urlencode(q)))
        for it in d.get("items", []):
            sn = it["snippet"]
            out.append({"id": sn["resourceId"]["videoId"], "t": sn["title"], "p": sn["publishedAt"]})
        token = d.get("nextPageToken")
        if not token or (out and out[-1]["p"] < since):
            break
    return [v for v in out if v["p"] >= since]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2026)
    a = ap.parse_args()
    R, A = races()
    p = os.path.join(ROOT, "data", "highlights.json")
    old = json.load(open(p)) if os.path.exists(p) else {"year": a.year, "rounds": {}}
    rounds = {k: dict(v) for k, v in old.get("rounds", {}).items()}
    found = []
    try:
        found += from_rss()
    except Exception as e:
        print("highlights: RSS feed not available:", str(e)[:120])
    key = os.environ.get("YOUTUBE_API_KEY")
    if key and not old.get("backfilled"):
        try:
            found += from_api(key, f"{a.year}-01-01")
            old["backfilled"] = True
            print(f"highlights: read {len(found)} uploads with the API")
        except Exception as e:
            print("highlights: API not available:", str(e)[:160])
    added = 0
    for v in sorted(found, key=lambda v: v["p"]):   # oldest first, so a later re-upload doesn't replace the original
        m = match(v["t"], a.year, R)
        if not m:
            continue
        rd, sess = str(m[0]), m[1]
        if sess not in rounds.get(rd, {}):
            rounds.setdefault(rd, {})[sess] = {"id": v["id"], "t": html.unescape(v["t"]), "p": v["p"]}
            added += 1
            print(f"highlights: round {rd} {sess}: {v['t']}")
    # hand-added links always win
    mp = os.path.join(ROOT, "data", "highlights-manual.json")
    if os.path.exists(mp):
        for rd, ss in json.load(open(mp)).items():
            if rd.startswith("_"):
                continue
            for sess, link in ss.items():
                i = vid_id(link)
                if i and rounds.get(rd, {}).get(sess, {}).get("id") != i:
                    rounds.setdefault(rd, {})[sess] = {"id": i, "t": f"{sess} highlights", "p": "", "manual": 1}
                    added += 1
    out = {"year": a.year, "channel": "FORMULA 1", "source": f"https://www.youtube.com/channel/{CHANNEL}",
           **({"backfilled": True} if old.get("backfilled") else {}),
           "rounds": {k: rounds[k] for k in sorted(rounds, key=int)}}
    if out != old:
        json.dump(out, open(p, "w"), ensure_ascii=False, indent=0, sort_keys=False)
    print(f"highlights: {sum(len(v) for v in rounds.values())} videos for {len(rounds)} rounds ({added} new)")


if __name__ == "__main__":
    main()
