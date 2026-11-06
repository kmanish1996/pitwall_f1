#!/usr/bin/env python3
"""Make the 1200x630 share images (Open Graph) for each section of the site.

Run from the repo root when a section is added or renamed:  python3 scripts/make_og.py
Needs Python Playwright with Chromium. Writes assets/og/<key>.jpg; build_pages.py picks them up.
Images avoid numbers that change week to week, so they don't go stale.
"""
import os
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS = {
    "learn": ("Learn F1", "Formula 1 explained for beginners", "🏎️", "#E10600"),
    "learn-about": ("What is Formula 1?", "The fastest sport on Earth, explained", "🏁", "#E10600"),
    "learn-weekend": ("F1 race weekend explained", "Practice · Qualifying · Sprint · Race · Points", "🗓️", "#B54BE8"),
    "learn-trophies": ("F1 trophies & championships", "Drivers' and Constructors' titles explained", "🏆", "#E9C46A"),
    "learn-track": ("F1 terms explained", "Apex · Kerbs · Chicanes · VSC · Flags", "🚩", "#FFC93C"),
    "learn-tyres": ("F1 tyres explained", "Soft · Medium · Hard · Inters · Wets", "🛞", "#E10600"),
    "learn-wheel": ("F1 steering wheel buttons", "What every button, dial and paddle does", "🎮", "#3C8DFF"),
    "learn-tech": ("2026 F1 tech explained", "Active aero · Overtake mode · ERS", "⚙️", "#2FD480"),
    "learn-people": ("Who's who in F1", "Drivers · Engineers · Pit crews · Marshals", "👥", "#00D7B6"),
    "next-race": ("Next F1 race", "Date, start time and weekend schedule", "⏱️", "#E10600"),
    "stats": ("F1 2026 stats", "Wins · Podiums · Poles · Fastest laps", "📈", "#00D7B6"),
    "results": ("F1 2026 results", "Every winner, podium and pole", "🥇", "#E9C46A"),
    "speed": ("How fast is an F1 car?", "Top speeds at every 2026 track", "💨", "#3C8DFF"),
    "circuits": ("Every F1 circuit in 3D", "Maps, facts and pole-lap telemetry", "🗺️", "#2FD480"),
    "reaction": ("F1 reaction test", "Can you beat Bottas's 0.201s?", "🔴", "#E10600"),
    "quali": ("F1 qualifying game", "Three laps. 22 drivers to beat.", "🎮", "#B54BE8"),
    "standings": ("F1 2026 standings", "Drivers' and constructors' championship", "📊", "#00D7B6"),
    "calendar": ("F1 2026 calendar", "Every Grand Prix, date and result", "📅", "#FFC93C"),
    "champions": ("Every F1 world champion", "From 1950 to today", "🏆", "#E9C46A"),
    "drivers": ("F1 drivers 2026", "Every driver, number, team and points", "🧑‍🚀", "#3C8DFF"),
    "teams": ("F1 teams 2026", "Every team, its drivers and results", "🏭", "#F47600"),
}
TPL = """<html><head><style>
*{{box-sizing:border-box}}body{{margin:0;width:1200px;height:630px;background:#0A0C11;color:#F1F3F7;font-family:'TeX Gyre Heros Cn','Arial Narrow',sans-serif;position:relative;overflow:hidden}}
.bg{{position:absolute;inset:0;background:radial-gradient(circle at 82% 50%,{c}55,transparent 46%),repeating-linear-gradient(105deg,transparent 0 58px,rgba(255,255,255,.025) 58px 60px)}}
.bar{{position:absolute;left:0;top:0;bottom:0;width:14px;background:{c}}}
.brand{{position:absolute;left:70px;top:56px;display:flex;align-items:center;gap:16px;font-weight:700;font-style:italic;font-size:40px;text-transform:uppercase}}
.brand i{{width:36px;height:36px;background:conic-gradient(#F1F3F7 25%,#0A0C11 0 50%,#F1F3F7 0 75%,#0A0C11 0) 0 0/18px 18px;border:2px solid #F1F3F7;transform:skewX(-12deg)}}
.brand b{{color:#E10600}}
h1{{position:absolute;left:70px;top:180px;width:760px;margin:0;font-size:92px;line-height:.92;font-style:italic;font-weight:700;text-transform:uppercase}}
p{{position:absolute;left:72px;top:0;width:760px;margin:0;font-family:Inter,sans-serif;font-size:32px;color:#B9C0CF}}
.emo{{position:absolute;right:90px;top:150px;font-family:'Noto Color Emoji';font-size:230px;filter:drop-shadow(0 20px 40px rgba(0,0,0,.6))}}
.url{{position:absolute;left:72px;bottom:52px;font-family:'DejaVu Sans Mono';font-weight:700;font-size:30px}}.url span{{color:#E10600}}
.tag{{position:absolute;right:70px;bottom:52px;font-family:Inter,sans-serif;font-size:20px;color:#8C94A6}}
</style></head><body><div class="bg"></div><div class="bar"></div>
<div class="brand"><i></i>Pit Wall <b>26</b></div><h1>{t}</h1><p>{s}</p><div class="emo">{emo}</div>
<div class="url">pitwallf1<span>.in</span></div><div class="tag">The unofficial Formula 1 fan hub</div>
<script>var h=document.querySelector("h1");document.querySelector("p").style.top=(h.offsetTop+h.offsetHeight+22)+"px"</script></body></html>"""


def main():
    out = os.path.join(ROOT, "assets", "og"); os.makedirs(out, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch(); pg = b.new_page(viewport={"width": 1200, "height": 630})
        for key, (t, s, emo, c) in CARDS.items():
            pg.set_content(TPL.format(t=t, s=s, emo=emo, c=c))
            pg.wait_for_timeout(150)
            pg.screenshot(path=os.path.join(out, f"{key}.jpg"), type="jpeg", quality=84)
        b.close()
    print(f"{len(CARDS)} share images in assets/og/")


if __name__ == "__main__":
    main()
