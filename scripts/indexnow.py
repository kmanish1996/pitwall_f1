#!/usr/bin/env python3
"""Tell Bing, Yandex and other IndexNow search engines about pages that changed.

Run from the repo root after a deploy:  python3 scripts/indexnow.py [--days 1]
Submits every sitemap URL whose lastmod is within the last N days (default 1).
The key file <key>.txt sits in the site root so the search engines can verify ownership.
"""
import glob, json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = "pitwallf1.in"


def main():
    days = int(sys.argv[sys.argv.index("--days") + 1]) if "--days" in sys.argv else 1
    keys = [os.path.basename(p)[:-4] for p in glob.glob(os.path.join(ROOT, "*.txt")) if re.fullmatch(r"[0-9a-f]{32}\.txt", os.path.basename(p))]
    if not keys: sys.exit("No IndexNow key file found in the site root")
    key = keys[0]
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    sm = open(os.path.join(ROOT, "sitemap.xml")).read()
    urls = [u for u, d in re.findall(r"<loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", sm) if d >= since]
    if not urls: print("Nothing changed recently"); return
    body = json.dumps({"host": HOST, "key": key, "keyLocation": f"https://{HOST}/{key}.txt", "urlList": urls[:10000]}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=body, headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r: print(f"IndexNow: submitted {len(urls)} URLs, HTTP {r.status}")
    except urllib.error.HTTPError as e:
        print(f"IndexNow: HTTP {e.code} {e.read()[:200]!r}")  # 202 means accepted, 403 means the key file isn't live yet


if __name__ == "__main__":
    main()
