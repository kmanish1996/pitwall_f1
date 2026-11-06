#!/usr/bin/env python3
"""Build crawlable HTML pages for search engines, plus sitemap.xml.

Run from the repo root:  python3 scripts/build_pages.py

Writes real pages (no JavaScript needed to read them) for the 2026 standings, the calendar,
every Grand Prix, every driver, every team, every circuit and the games, plus machine-readable
JSON under /api/, llms.txt for AI assistants, robots.txt and sitemap.xml (a page's lastmod only
changes when its content does). Data comes from the same places the app uses:
the constants in index.html (standings, calendar, lap records) and the session results in data/.
Needs Node.js to read the constants from index.html.
"""
import html, json, math, os, re, subprocess, unicodedata
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://pitwallf1.in"
YEAR = 2026
BRAND = "Pit Wall F1"
INSTAGRAM = "https://www.instagram.com/pitwall_f1_/"
NATIONS = {"ITA": "Italy", "GBR": "United Kingdom", "NED": "Netherlands", "MON": "Monaco", "AUS": "Australia", "FRA": "France",
           "NZL": "New Zealand", "ARG": "Argentina", "GER": "Germany", "BRA": "Brazil", "ESP": "Spain", "THA": "Thailand",
           "JPN": "Japan", "CAN": "Canada", "FIN": "Finland", "MEX": "Mexico"}
COUNTRY = {"AUS": "Australia", "CHN": "China", "JPN": "Japan", "MIA": "United States", "CAN": "Canada", "MON": "Monaco",
           "BCN": "Spain", "AUT": "Austria", "GBR": "United Kingdom", "BEL": "Belgium", "HUN": "Hungary", "NED": "Netherlands",
           "ITA": "Italy", "ESP": "Spain", "AZE": "Azerbaijan", "BHR": "Malaysia", "SGP": "Singapore", "USA": "United States",
           "MEX": "Mexico", "BRA": "Brazil", "LVG": "United States", "QAT": "Qatar", "ABU": "United Arab Emirates"}
SESSION_ORDER = ["Race", "Sprint", "Qualifying", "Sprint Qualifying", "Practice 3", "Practice 2", "Practice 1"]

e = html.escape


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def app_data():
    js = r"""
const fs=require('fs'),vm=require('vm');const h=fs.readFileSync(process.argv[1],'utf8');
const a=h.indexOf('const TEAMS={'),b=h.indexOf('const POINTS=');const c={};vm.createContext(c);
vm.runInContext(h.slice(a,b)+';this.o={TEAMS,DRIVERS,CONSTRUCTORS,PER_RACE,RACES,SPRINT_WIN,LAP_RECORD,LONG_NAMES,COMPLETED,TOTAL,SESSIONS,CHAMPIONS:typeof CHAMPIONS!=="undefined"?CHAMPIONS:[]};',c);
const t0=h.indexOf('const TRACK_INFO={'),t1=h.indexOf('const TK={');
if(t0>0){vm.runInContext(h.slice(t0,t1)+';this.o.TRACK_INFO=TRACK_INFO;this.o.TRACK_SOURCES=TRACK_SOURCES;',c)}
const l0=h.indexOf('/* ================= LEARN F1: illustrations'),l1=h.indexOf('/* ---------- 3D steering wheel'),l2=h.indexOf('const LW={');
if(l0>0){vm.runInContext(h.slice(l0,l1)+h.slice(l1,l2)+`;this.o.LEARN={terms:LN_TERMS.map(t=>({id:t.id,name:t.name,short:t.short,body:t.body,svg:t.svg()})),
 tyres:LN_TYRES.map(t=>({...t,svg:lnTyreSvg(t)})),tech:LN_TECH.map(t=>({id:t.id,name:t.name,kick:t.kick,body:t.body,svg:t.svg()})),people:LN_PEOPLE.map(t=>({id:t.id,name:t.name,kick:t.kick,body:t.body,svg:t.svg()})),
 history:LN_HISTORY,nums:LN_NUMS,wcc:LN_WCC,awards:LN_AWARDS,sess:LN_SESS.map(s=>({id:s.id,name:s.name,when:s.when,time:s.time,body:s.body,svg:'<svg viewBox="0 0 320 160" class="ln-svg" role="img">'+lnDefs+s.svg()+'</svg>'})),limit:LN_LIMIT.map(c=>({t:c.t,d:c.d,svg:'<svg viewBox="0 0 200 110" class="ln-svg" role="img">'+lnDefs+c.svg+'</svg>'})),parts:LN_PARTS.map(p=>({name:p.name,txt:p.txt})),
 ctrl:LN_CTRL.map(c=>({id:c.id,name:c.name,txt:c.txt}))};`,c)}
process.stdout.write(JSON.stringify(c.o));"""
    out = subprocess.run(["node", "-e", js, os.path.join(ROOT, "index.html")], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def fmt_lap(s):
    if s is None: return "—"
    m = int(s // 60); r = s - m * 60
    return f"{m}:{r:06.3f}" if m else f"{r:.3f}"


def fmt_race(s):
    if s is None: return ""
    h = int(s // 3600); m = int(s % 3600 // 60); r = s % 60
    return f"{h}:{m:02d}:{r:06.3f}" if h else f"{m}:{r:06.3f}"


def nice_date(iso):
    d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return f"{d.day} {d.strftime('%B')} {d.year}"


CSS = """
:root{--bg:#0A0C11;--panel:#12161E;--panel2:#1A1F2A;--line:#262C39;--fg:#F1F3F7;--muted:#8C94A6;--red:#E10600;--purple:#B54BE8;
--fd:"Saira Condensed","Arial Narrow",Impact,sans-serif;--fb:"Barlow","Segoe UI",system-ui,sans-serif;--fm:"JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 var(--fb);-webkit-font-smoothing:antialiased}
a{color:var(--red);font-weight:700;text-decoration:none}a:hover{text-decoration:underline;text-underline-offset:3px}
.w{max-width:1080px;margin:0 auto;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
header.top{border-bottom:1px solid var(--line);background:var(--bg)}
header.top .w{display:flex;align-items:center;gap:20px;min-height:60px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:10px;color:var(--fg);font:italic 900 24px/1 var(--fd);text-transform:uppercase}
.brand:hover{text-decoration:none}.brand i{width:22px;height:22px;background:conic-gradient(#F1F3F7 25%,#0A0C11 0 50%,#F1F3F7 0 75%,#0A0C11 0) 0 0/11px 11px;border:1px solid #F1F3F7;transform:skewX(-12deg)}
.brand b{color:var(--red)}.brand small{display:block;font:500 11px var(--fb);text-transform:none;color:var(--muted);margin-top:2px}
nav.main{display:flex;gap:4px 16px;flex-wrap:wrap;margin-left:auto}
nav.main a{color:var(--muted);font:700 14px var(--fd);text-transform:uppercase;letter-spacing:.08em}nav.main a:hover{color:var(--fg);text-decoration:none}
.crumbs{font-size:13px;color:var(--muted);margin:22px 0 6px}.crumbs a{color:var(--muted);font-weight:500}
h1,h2,h3{font-family:var(--fd);text-transform:uppercase;line-height:1;margin:0;text-wrap:balance}
h1{font-size:clamp(34px,6vw,58px);font-weight:900;font-style:italic;margin:4px 0 8px}
h2{font-size:clamp(24px,3.4vw,32px);font-weight:900;font-style:italic;margin:36px 0 12px}
h3{font-size:20px;font-weight:800;margin:24px 0 8px}
.sub{color:var(--muted);margin:0 0 18px}
.lead{font-size:18px;max-width:72ch}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:4px;overflow:hidden;margin:18px 0}
.tile{background:var(--panel);padding:12px 14px}.tile span{display:block;font:700 11px var(--fd);text-transform:uppercase;letter-spacing:.12em;color:var(--muted)}
.tile b{font:700 24px var(--fm)}.tile small{display:block;color:var(--muted);font-size:12px}
.tbl{overflow-x:auto;border:1px solid var(--line);border-radius:4px;background:var(--panel)}
table{width:100%;border-collapse:collapse;font-size:14px}
th{font:700 11px var(--fd);text-transform:uppercase;letter-spacing:.1em;color:var(--muted);text-align:left;padding:9px 10px;background:var(--panel2);white-space:nowrap}
td{padding:8px 10px;border-top:1px solid var(--line);white-space:nowrap}
td.n{font:700 14px var(--fm);text-align:right}th.n{text-align:right}
td.pos{font:italic 900 17px var(--fd);width:40px}
.sw{display:inline-block;width:4px;height:16px;vertical-align:-3px;margin-right:8px;background:var(--team,#888)}
.btn{display:inline-block;background:var(--red);color:#fff;font:800 13px var(--fd);text-transform:uppercase;letter-spacing:.08em;padding:9px 14px;border-radius:3px}
.btn:hover{text-decoration:none;filter:brightness(1.1)}
.note{color:var(--muted);font-size:14px}
.rec{border-left:3px solid var(--purple);padding:8px 12px;background:var(--panel);margin:16px 0}.rec b{color:var(--purple);font-family:var(--fm)}
.pager{display:flex;justify-content:space-between;gap:12px;margin:36px 0 0;flex-wrap:wrap}
details{margin:10px 0}summary{cursor:pointer;font:800 18px var(--fd);text-transform:uppercase}
footer.site{margin-top:48px;border-top:1px solid var(--line);padding:24px 0 32px;text-align:center;font-size:13px;color:var(--muted)}
footer.site p{margin:8px auto;max-width:110ch}footer.site nav{display:flex;flex-wrap:wrap;justify-content:center;gap:6px 14px}
footer.site nav a{color:var(--fg);font-weight:500}
@media (max-width:640px){header.top .w{padding-block:10px;row-gap:6px}header.top .brand{margin-right:auto}nav.main{margin-left:0;flex:1 1 100%;flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;padding-bottom:4px;-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 40px),transparent);mask-image:linear-gradient(90deg,#000 calc(100% - 40px),transparent)}nav.main a{white-space:nowrap}}
:root[data-theme="light"]{--bg:#F3F4F7;--panel:#FFFFFF;--panel2:#EEF0F4;--line:#DCE0E7;--fg:#12151C;--muted:#5A6272;--red:#D70500;--purple:#8A32CF;color-scheme:light}
.theme-btn{display:inline-grid;place-items:center;width:34px;height:32px;border-radius:3px;border:1px solid var(--line);background:transparent;color:var(--fg);cursor:pointer}
.theme-btn svg{width:17px;height:17px}.theme-btn .sun{display:none}:root[data-theme="light"] .theme-btn .sun{display:block}:root[data-theme="light"] .theme-btn .moon{display:none}
"""
THEME_HEAD = """<meta name="color-scheme" content="dark light">
<script>try{var t=localStorage.getItem("pw_theme");if(t!=="light")t="dark";document.documentElement.dataset.theme=t}catch(e){document.documentElement.dataset.theme="dark"}</script>"""
THEME_BTN = """<button type="button" class="theme-btn" aria-label="Switch between light and dark mode" title="Light / dark mode" onclick="var r=document.documentElement,t=r.dataset.theme==='light'?'dark':'light';r.dataset.theme=t;try{localStorage.setItem('pw_theme',t)}catch(e){}"><svg class="moon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" fill="currentColor"/></svg><svg class="sun" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.5" fill="currentColor"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></g></svg></button>"""


CHANGED = {}


OG_BY_PREFIX = [("/circuits/", "circuits"), ("/f1-reaction-test/", "reaction"), ("/f1-qualifying-game/", "quali"), ("/formula-1-standings-", "standings"),
                ("/f1-calendar-", "calendar"), ("/races/", "calendar"), ("/formula-1-world-champions/", "champions"), ("/drivers/", "drivers"), ("/teams/", "teams")]


def og_image(path, og):
    og = og or next((k for p, k in OG_BY_PREFIX if path.startswith(p)), None)
    return f"{SITE}/assets/og/{og}.jpg" if og and os.path.exists(os.path.join(ROOT, "assets", "og", f"{og}.jpg")) else f"{SITE}/assets/og-image.png"


def page(path, title, desc, body, crumbs, ld=None, extra_head="", ld_list=None, og=None):
    url = f"{SITE}{path}"
    trail = [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + p} for i, (n, p) in enumerate([("Home", "/")] + crumbs)]
    blocks = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": trail}] + ([ld] if ld else []) + (ld_list or [])
    crumb_html = " › ".join([f'<a href="/">Home</a>'] + [f'<a href="{p}">{e(n)}</a>' if i < len(crumbs) - 1 else e(n) for i, (n, p) in enumerate(crumbs)])
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{og_image(path, og)}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{og_image(path, og)}">
<meta name="theme-color" content="#0A0C11">
{THEME_HEAD}
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/favicon-96.png" type="image/png" sizes="96x96">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Saira+Condensed:wght@700;800;900&family=Barlow:wght@400;500;700&family=JetBrains+Mono:wght@500;700&display=swap">
<style>{CSS}</style>
{extra_head}
{''.join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>' for b in blocks)}
</head>
<body>
<header class="top"><div class="w">
<a class="brand" href="/"><i aria-hidden="true"></i><span>Pit Wall <b>F1</b><small>The unofficial Formula 1 fan hub</small></span></a>
{THEME_BTN}
<nav class="main" aria-label="Main"><a href="/next-f1-race/">Next race</a><a href="/formula-1-standings-{YEAR}/">Standings</a><a href="/f1-results-{YEAR}/">Results</a><a href="/f1-stats-{YEAR}/">Stats</a><a href="/f1-calendar-{YEAR}/">Calendar</a><a href="/circuits/">Circuits</a><a href="/learn-f1/">Learn F1</a><a href="/drivers/">Drivers</a><a href="/teams/">Teams</a><a href="/formula-1-world-champions/">Champions</a><a href="/f1-reaction-test/">Reaction test</a></nav>
</div></header>
<main class="w">
<div class="crumbs">{crumb_html}</div>
{body}
</main>
<footer class="site"><div class="w">
<p>This website is unofficial and is not associated in any way with the Formula 1 companies. F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX and related marks are trade marks of Formula One Licensing B.V.</p>
<nav aria-label="Site"><a href="/next-f1-race/">Next F1 race</a><a href="/f1-results-{YEAR}/">{YEAR} results</a><a href="/f1-stats-{YEAR}/">{YEAR} F1 stats</a><a href="/how-fast-is-an-f1-car/">How fast is an F1 car?</a><a href="/formula-1-standings-{YEAR}/">{YEAR} standings</a><a href="/f1-calendar-{YEAR}/">{YEAR} calendar</a><a href="/drivers/">Drivers</a><a href="/teams/">Teams</a><a href="/formula-1-world-champions/">World champions</a><a href="/circuits/">F1 circuits</a><a href="/learn-f1/">Learn F1</a><a href="/f1-reaction-test/">F1 reaction test</a><a href="/f1-qualifying-game/">Qualifying game</a><a href="/#privacy">Privacy Policy</a><a href="/#terms">Terms</a><a href="/#contact">Contact us</a><a href="/#about">About us</a><a href="{INSTAGRAM}" rel="noopener">Instagram</a></nav>
<p>©{YEAR} {BRAND}. Timing data from OpenF1.</p>
</div></footer>
</body>
</html>
"""
    out = os.path.join(ROOT, path.strip("/"), "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    old = open(out).read() if os.path.exists(out) else None
    CHANGED[path] = old != doc
    if old != doc: open(out, "w").write(doc)
    return path


def main():
    A = app_data()
    T, D, C, RACES = A["TEAMS"], A["DRIVERS"], A["CONSTRUCTORS"], A["RACES"]
    done = A["COMPLETED"]; total = A["TOTAL"]
    by_code = {d["code"]: d for d in D}
    dslug = {d["code"]: slug(f"{d['first']} {d['last']}") for d in D}
    tslug = {t: slug(t.replace(" F1 Team", "")) for t in T}
    gp_long = lambda r: A["LONG_NAMES"].get(str(r["rd"])) or r["name"].replace(" GP", " Grand Prix")
    rslug = {r["rd"]: slug(f"{gp_long(r)} {YEAR}") for r in RACES}
    race_url = lambda rd: f"/races/{rslug[rd]}/"
    drv = lambda code: f'<a href="/drivers/{dslug[code]}/">{e(by_code[code]["first"])} {e(by_code[code]["last"])}</a>' if code in by_code else e(code)
    team_link = lambda t: f'<a href="/teams/{tslug[t]}/">{e(t)}</a>' if t in tslug else e(t)
    tc = lambda t: T.get(t, {}).get("c", "#888")
    wins = {}
    for r in RACES:
        if r.get("win"): wins[r["win"]] = wins.get(r["win"], 0) + 1
    swins = {}
    for v in A["SPRINT_WIN"].values(): swins[v[0]] = swins.get(v[0], 0) + 1

    # sessions with replay data, grouped by round
    idx = json.load(open(os.path.join(ROOT, "data", "index.json")))
    def round_of(s):
        dt = datetime.fromisoformat(s["date"]).timestamp()
        best = None
        for r in RACES:
            diff = datetime.fromisoformat(r["race"].replace("Z", "+00:00")).timestamp() - dt
            if -6 * 3600 < diff < 4 * 86400 and (best is None or diff < best[0]): best = (diff, r["rd"])
        return best[1] if best else None
    sess = {}
    for s in idx:
        rd = round_of(s)
        if rd: sess.setdefault(rd, {})[s["type"]] = s["sk"]
    cache = {}
    def sdata(sk):
        if sk not in cache: cache[sk] = json.load(open(os.path.join(ROOT, "data", f"{sk}.json")))
        return cache[sk]
    def finish(rd, code, kind="Race"):
        sk = sess.get(rd, {}).get(kind)
        if not sk: return None
        d = sdata(sk); num = {x["c"]: x["n"] for x in d["drivers"]}
        for r in d["result"]:
            if r[1] == num.get(code): return r[4] or r[0]
        return None
    leader, second = D[0], D[1]
    CHL = (A.get("CHAMPIONS") or [[0, ""]])[-1]
    champ_now = CHL[0] == YEAR and CHL[1] == f"{leader['first']} {leader['last']}"
    left = (total - done) * 25
    pages = []

    # ---------- standings ----------
    rows = "".join(f'<tr style="--team:{tc(d["team"])}"><td class="pos">{i+1}</td><td><span class="sw"></span>{drv(d["code"])}</td><td>{e(NATIONS.get(d["nat"], d["nat"]))}</td><td>{team_link(d["team"])}</td><td class="n">{wins.get(d["code"], 0)}</td><td class="n">{d["pts"]}</td><td class="n">{"" if i == 0 else "+" + str(leader["pts"] - d["pts"])}</td></tr>' for i, d in enumerate(D))
    trows = "".join(f'<tr style="--team:{tc(t)}"><td class="pos">{i+1}</td><td><span class="sw"></span>{team_link(t)}</td><td>{", ".join(drv(d["code"]) for d in D if d["team"] == t)}</td><td class="n">{p}</td></tr>' for i, (t, p) in enumerate(C))
    body = f"""<h1>Formula 1 standings {YEAR}</h1>
<p class="sub">Drivers' and constructors' championships after round {done} of {total}, the {e(gp_long(RACES[done-1]))}.</p>
<p class="lead">{drv(leader["code"])} {"is the " + str(YEAR) + " Formula 1 World Champion. He has" if champ_now else "leads the " + str(YEAR) + " drivers' championship with"} {leader["pts"]} points, {leader["pts"]-second["pts"]} more than {drv(second["code"])}. With {total-done} races left, {left} points are still available. {team_link(C[0][0])} lead the constructors' championship on {C[0][1]} points.</p>
<h2>Drivers' championship</h2><div class="tbl"><table><thead><tr><th>Pos</th><th>Driver</th><th>Nationality</th><th>Team</th><th class="n">Wins</th><th class="n">Points</th><th class="n">Gap</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Constructors' championship</h2><div class="tbl"><table><thead><tr><th>Pos</th><th>Team</th><th>Drivers</th><th class="n">Points</th></tr></thead><tbody>{trows}</tbody></table></div>
<p class="note" style="margin-top:16px">Want the title maths? <a href="/#title-fight">See who can still win the {YEAR} championship</a>, or <a href="/#replay">replay the season round by round</a>.</p>"""
    pages.append(page(f"/formula-1-standings-{YEAR}/", f"F1 {YEAR} standings: drivers' & constructors' table | {BRAND}",
                      f"Formula 1 {YEAR} championship standings after round {done}: {leader['first']} {leader['last']} leads on {leader['pts']} points. Full drivers' and constructors' tables with wins and gaps.",
                      body, [(f"{YEAR} standings", f"/formula-1-standings-{YEAR}/")]))

    # ---------- calendar ----------
    crow = []
    for r in RACES:
        rd = r["rd"]; res = ""
        if r.get("win"): res = f'Winner: {drv(r["win"])}'
        elif sess.get(rd): res = "Weekend under way"
        crow.append(f'<tr><td class="pos">{rd}</td><td><a href="{race_url(rd)}">{e(gp_long(r))}</a>{" · Sprint" if r["sprint"] else ""}</td><td>{e(r["circuit"])}, {e(r["place"])}</td><td>{e(r["dates"])}</td><td>{res}</td></tr>')
    body = f"""<h1>F1 calendar {YEAR}</h1>
<p class="sub">All {total} rounds of the {YEAR} Formula 1 World Championship, with circuits, dates, winners and session results.</p>
<p class="lead">The {YEAR} season runs from the {e(gp_long(RACES[0]))} in March to the {e(gp_long(RACES[-1]))} in December, with six sprint weekends. The Saudi Arabian Grand Prix was cancelled and the Bahrain Grand Prix moved to Sepang, Malaysia.</p>
<div class="tbl"><table><thead><tr><th>Rd</th><th>Grand Prix</th><th>Circuit</th><th>Dates</th><th>Result</th></tr></thead><tbody>{''.join(crow)}</tbody></table></div>
<p class="note" style="margin-top:16px">Session times in your own time zone, with live countdowns: <a href="/#calendar">open the interactive calendar</a>.</p>"""
    pages.append(page(f"/f1-calendar-{YEAR}/", f"F1 {YEAR} calendar: every Grand Prix, date and result | {BRAND}",
                      f"The full {YEAR} Formula 1 calendar: all {total} Grands Prix with circuits, dates, sprint weekends, winners and results.",
                      body, [(f"{YEAR} calendar", f"/f1-calendar-{YEAR}/")]))

    # ---------- races ----------
    def result_table(sk, kind):
        d = sdata(sk); dm = {x["n"]: x for x in d["drivers"]}
        q = "Qualifying" in kind
        head = "<th class='n'>Q1</th><th class='n'>Q2</th><th class='n'>Q3</th>" if q else ("<th class='n'>Best lap</th><th class='n'>Gap</th>" if kind.startswith("Practice") else "<th class='n'>Time / gap</th><th class='n'>Points</th>")
        trs = []
        for i, r in enumerate(d["result"]):
            x = dm.get(r[1])
            if not x: continue
            name = drv(x["c"]) if x["c"] in by_code else e(f'{x["f"]} {x["l"]}')
            if q:
                qs = r[6] if isinstance(r[6], list) else []
                cells = "".join(f"<td class='n'>{fmt_lap(qs[k]) if k < len(qs) and qs[k] is not None else '—'}</td>" for k in range(3))
            elif kind.startswith("Practice"):
                cells = f"<td class='n'>{fmt_lap(r[6]) if isinstance(r[6], (int, float)) else '—'}</td><td class='n'>{'+%.3f' % r[3] if i and isinstance(r[3], (int, float)) else ''}</td>"
            else:
                g = r[4] or (fmt_race(r[6]) if i == 0 else ("+%.3f" % r[3] if isinstance(r[3], (int, float)) else (r[3] or "")))
                cells = f"<td class='n'>{e(str(g))}</td><td class='n'>{int(r[5]) if r[5] else ''}</td>"
            trs.append(f'<tr style="--team:{x["col"]}"><td class="pos">{r[0] if r[0] is not None else "–"}</td><td><span class="sw"></span>{name}</td><td>{e(x["t"])}</td>{cells}</tr>')
        return f'<div class="tbl"><table><thead><tr><th>Pos</th><th>Driver</th><th>Team</th>{head}</tr></thead><tbody>{"".join(trs)}</tbody></table></div><p style="margin:10px 0 0"><a class="btn" href="/?replay={sk}#race-centre">Watch the {e(kind.lower())} replay</a></p>'

    for i, r in enumerate(RACES):
        rd = r["rd"]; name = gp_long(r); have = sess.get(rd, {})
        start = r["race"]
        L = A["LAP_RECORD"].get(str(rd))
        pole = None
        if have.get("Qualifying"):
            d = sdata(have["Qualifying"]); dm = {x["n"]: x["c"] for x in d["drivers"]}
            if d["result"]: pole = dm.get(d["result"][0][1])
        if r.get("win"):
            sw = A["SPRINT_WIN"].get(str(rd))
            lead = f'{drv(r["win"])} won the {YEAR} {e(name)} for {team_link(r["winTeam"])}, in a race time of {e(r["time"])}.'
            if pole: lead += f' {drv(pole)} started from pole position.'
            if sw: lead += f' {drv(sw[0])} won the sprint.'
        else:
            lead = f'The {YEAR} {e(name)} is round {rd} of {total}, held at {e(r["circuit"])} in {e(r["place"])} on {e(r["dates"])} {YEAR}. The race starts at {datetime.fromisoformat(start.replace("Z","+00:00")).strftime("%H:%M")} UTC on {nice_date(start)}.'
            if pole: lead += f' {drv(pole)} took pole position.'
        secs = []
        for kind in SESSION_ORDER:
            if kind in have:
                tag = "h2" if kind in ("Race", "Qualifying", "Sprint") else "h3"
                block = f"<{tag}>{e(kind)} results</{tag}>{result_table(have[kind], kind)}"
                secs.append(block if tag == "h2" else f"<details><summary>{e(kind)} results</summary>{result_table(have[kind], kind)}</details>")
        rec = f'<div class="rec">Lap record: <b>{e(L[0])}</b>, {e(L[1])} ({e(L[2])}, {L[3]})</div>' if L else ""
        csl = next((k for k, v in (A.get("TRACK_INFO") or {}).items() if v["rd"] == rd), None)
        if csl: rec += f'<p class="note">About the track: <a href="/circuits/{csl}/">{e(r["circuit"])} map, facts and pole lap telemetry</a>, or <a href="/#tracks/{csl}">explore it in 3D</a>.</p>'
        prev = f'<a href="{race_url(RACES[i-1]["rd"])}">← {e(gp_long(RACES[i-1]))}</a>' if i else "<span></span>"
        nxt = f'<a href="{race_url(RACES[i+1]["rd"])}">{e(gp_long(RACES[i+1]))} →</a>' if i + 1 < len(RACES) else "<span></span>"
        body = f"""<h1>{e(name)} {YEAR}</h1>
<p class="sub">Round {rd} of {total} · {e(r["circuit"])}, {e(r["place"])} · {e(r["dates"])} {YEAR}{" · Sprint weekend" if r["sprint"] else ""}</p>
<p class="lead">{lead}</p>{rec}
{''.join(secs) or '<p class="note">Results appear here about 30 to 45 minutes after each session ends.</p>'}
<div class="pager">{prev}<a href="/f1-calendar-{YEAR}/">Full calendar</a>{nxt}</div>"""
        ld = {"@context": "https://schema.org", "@type": "SportsEvent", "name": f"{YEAR} {name}", "sport": "Formula 1",
              "startDate": start, "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
              "location": {"@type": "Place", "name": r["circuit"], "address": {"@type": "PostalAddress", "addressLocality": r["place"], "addressCountry": COUNTRY.get(r["short"], "")}},
              "url": SITE + race_url(rd)}
        if r.get("win") and r["win"] in by_code:
            ld["winner"] = {"@type": "Person", "name": f'{by_code[r["win"]]["first"]} {by_code[r["win"]]["last"]}'}
        desc = (f'{name} {YEAR} results: {by_code[r["win"]]["first"]} {by_code[r["win"]]["last"]} won at {r["circuit"]}. Race, qualifying and practice results, lap record and full replays.'
                if r.get("win") and r["win"] in by_code else f'{name} {YEAR} at {r["circuit"]}, {r["dates"]}: schedule, results from every session, lap record and full replays.')
        pages.append(page(race_url(rd), f"{name} {YEAR}: results, qualifying and lap record | {BRAND}", desc, body,
                          [(f"{YEAR} calendar", f"/f1-calendar-{YEAR}/"), (name, race_url(rd))], ld))

    # ---------- drivers ----------
    for pos, d in enumerate(D, 1):
        code = d["code"]; full = f'{d["first"]} {d["last"]}'
        tm = next((x for x in D if x["team"] == d["team"] and x["code"] != code), None)
        rows = []
        for r in RACES[:done]:
            f = finish(r["rd"], code); q = finish(r["rd"], code, "Qualifying")
            pts = A["PER_RACE"].get(code, [None] * done)[r["rd"] - 1] if code in A["PER_RACE"] else None
            rows.append(f'<tr><td class="pos">{r["rd"]}</td><td><a href="{race_url(r["rd"])}">{e(gp_long(r))}</a></td><td class="n">{q if q is not None else "–"}</td><td class="n">{f if f is not None else "–"}</td><td class="n">{"" if pts is None else pts}</td></tr>')
        lead = ((f'{e(full)} is the {YEAR} Formula 1 World Champion. ' if champ_now and pos == 1 else "") + f'{e(full)} drives car number {d["no"]} for {team_link(d["team"])} in the {YEAR} Formula 1 season. '
                f'After round {done}, {e(d["first"])} is P{pos} in the drivers\' championship with {d["pts"]} points'
                + (f', {wins[code]} Grand Prix win{"s" if wins[code] > 1 else ""}' if wins.get(code) else "")
                + (f' and {swins[code]} sprint win{"s" if swins[code] > 1 else ""}' if swins.get(code) else "") + ".")
        if tm: lead += f' Teammate {drv(tm["code"])} has {tm["pts"]} points.'
        body = f"""<h1>{e(full)}</h1>
<p class="sub">#{d["no"]} · {team_link(d["team"])} · {e(NATIONS.get(d["nat"], d["nat"]))}</p>
<p class="lead">{lead}</p>
<div class="tiles"><div class="tile"><span>Championship</span><b>P{pos}</b></div><div class="tile"><span>Points</span><b>{d["pts"]}</b></div><div class="tile"><span>GP wins</span><b>{wins.get(code, 0)}</b></div><div class="tile"><span>Sprint wins</span><b>{swins.get(code, 0)}</b></div><div class="tile"><span>Gap to leader</span><b>{"—" if pos == 1 else "+" + str(leader["pts"] - d["pts"])}</b></div></div>
<h2>{YEAR} season, race by race</h2>
<div class="tbl"><table><thead><tr><th>Rd</th><th>Grand Prix</th><th class="n">Qualified</th><th class="n">Finished</th><th class="n">Points</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="note" style="margin-top:10px">Points include sprint points. <a href="/formula-1-standings-{YEAR}/">See the full {YEAR} standings</a>.</p>"""
        ld = {"@context": "https://schema.org", "@type": "Person", "name": full, "nationality": NATIONS.get(d["nat"], d["nat"]),
              "jobTitle": "Racing driver", "memberOf": {"@type": "SportsTeam", "name": d["team"], "sport": "Formula 1"}, "url": f"{SITE}/drivers/{dslug[code]}/"}
        pages.append(page(f"/drivers/{dslug[code]}/", f"{full} {YEAR}: F1 points, results and standings | {BRAND}",
                          f"{full} in the {YEAR} Formula 1 season: P{pos} with {d['pts']} points for {d['team']}. Race-by-race qualifying and finishing positions.",
                          body, [("Drivers", "/drivers/"), (full, f"/drivers/{dslug[code]}/")], ld))
    rows = "".join(f'<tr style="--team:{tc(d["team"])}"><td class="pos">{i+1}</td><td><span class="sw"></span>{drv(d["code"])}</td><td class="n">{d["no"]}</td><td>{team_link(d["team"])}</td><td>{e(NATIONS.get(d["nat"], d["nat"]))}</td><td class="n">{d["pts"]}</td></tr>' for i, d in enumerate(D))
    pages.append(page("/drivers/", f"F1 drivers {YEAR}: every driver, number and team | {BRAND}",
                      f"All {len(D)} Formula 1 drivers in {YEAR}, with car numbers, teams, nationalities and championship points.",
                      f'<h1>F1 drivers {YEAR}</h1><p class="sub">Every driver on the {YEAR} grid, in championship order.</p><div class="tbl"><table><thead><tr><th>Pos</th><th>Driver</th><th class="n">No.</th><th>Team</th><th>Nationality</th><th class="n">Points</th></tr></thead><tbody>{rows}</tbody></table></div>',
                      [("Drivers", "/drivers/")]))

    # ---------- teams ----------
    for pos, (t, p) in enumerate(C, 1):
        ds = [d for d in D if d["team"] == t]
        rows = []
        for r in RACES[:done]:
            fs = " · ".join(f'{x["code"]} {finish(r["rd"], x["code"]) or "–"}' for x in ds)
            rows.append(f'<tr><td class="pos">{r["rd"]}</td><td><a href="{race_url(r["rd"])}">{e(gp_long(r))}</a></td><td>{e(fs)}</td></tr>')
        tw = sum(wins.get(x["code"], 0) for x in ds)
        lead = f'{e(t)} are P{pos} in the {YEAR} Formula 1 constructors\' championship with {p} points' + (f' and {tw} Grand Prix win{"s" if tw > 1 else ""}' if tw else "") + f'. Drivers: {" and ".join(drv(x["code"]) + f" ({x['pts']} pts)" for x in ds)}.'
        body = f"""<h1>{e(t)}</h1>
<p class="sub">Formula 1 team · {YEAR} season</p>
<p class="lead">{lead}</p>
<div class="tiles"><div class="tile"><span>Constructors'</span><b>P{pos}</b></div><div class="tile"><span>Points</span><b>{p}</b></div><div class="tile"><span>GP wins</span><b>{tw}</b></div></div>
<h2>Finishing positions by race</h2>
<div class="tbl"><table><thead><tr><th>Rd</th><th>Grand Prix</th><th>Finishes</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"""
        ld = {"@context": "https://schema.org", "@type": "SportsTeam", "name": t, "sport": "Formula 1",
              "athlete": [{"@type": "Person", "name": f'{x["first"]} {x["last"]}'} for x in ds], "url": f"{SITE}/teams/{tslug[t]}/"}
        pages.append(page(f"/teams/{tslug[t]}/", f"{t} F1 {YEAR}: points, drivers and results | {BRAND}",
                          f"{t} in the {YEAR} Formula 1 season: P{pos} in the constructors' championship with {p} points. Drivers, wins and race-by-race results.",
                          body, [("Teams", "/teams/"), (t, f"/teams/{tslug[t]}/")], ld))
    rows = "".join(f'<tr style="--team:{tc(t)}"><td class="pos">{i+1}</td><td><span class="sw"></span>{team_link(t)}</td><td>{", ".join(drv(d["code"]) for d in D if d["team"] == t)}</td><td class="n">{p}</td></tr>' for i, (t, p) in enumerate(C))
    pages.append(page("/teams/", f"F1 teams {YEAR}: every team and its drivers | {BRAND}",
                      f"All {len(C)} Formula 1 teams in {YEAR}, with their drivers and constructors' championship points.",
                      f'<h1>F1 teams {YEAR}</h1><p class="sub">Every team on the {YEAR} grid, in constructors\' championship order.</p><div class="tbl"><table><thead><tr><th>Pos</th><th>Team</th><th>Drivers</th><th class="n">Points</th></tr></thead><tbody>{rows}</tbody></table></div>',
                      [("Teams", "/teams/")]))

    # ---------- world champions ----------
    CH = A.get("CHAMPIONS") or []
    if CH:
        counts = {}
        for c in CH: counts[c[1]] = counts.get(c[1], 0) + 1
        most = sorted(counts.items(), key=lambda x: -x[1])[:6]
        latest = CH[-1]
        name2code = {f"{d['first']} {d['last']}": d["code"] for d in D}
        trs = "".join(f'<tr><td class="pos">{c[0]}</td><td>{drv(name2code[c[1]]) if c[1] in name2code else e(c[1])}</td><td>{e(c[3])}</td></tr>' for c in reversed(CH))
        body = f"""<h1>Formula 1 world champions</h1>
<p class="sub">Every World Drivers' Champion from 1950 to {latest[0]}.</p>
<p class="lead">{e(latest[1])} is the {latest[0]} Formula 1 World Champion with {e(latest[3])}. {len(counts)} different drivers have won the title since the first championship in 1950. The most successful are {", ".join(f"{e(n)} ({k})" for n, k in most[:4])}.</p>
<h2>Most titles</h2><div class="tbl"><table><thead><tr><th>Driver</th><th class="n">Titles</th><th>Seasons</th></tr></thead><tbody>{"".join(f'<tr><td>{e(n)}</td><td class="n">{k}</td><td>{", ".join(str(c[0]) for c in CH if c[1] == n)}</td></tr>' for n, k in most)}</tbody></table></div>
<h2>Every champion</h2><div class="tbl"><table><thead><tr><th>Year</th><th>Driver</th><th>Team</th></tr></thead><tbody>{trs}</tbody></table></div>"""
        pages.append(page("/formula-1-world-champions/", f"Formula 1 world champions: every F1 champion since 1950 | {BRAND}",
                          f"Every Formula 1 World Drivers' Champion from 1950 to {latest[0]}, including {latest[1]} in {latest[0]}. Most titles, teams and seasons.",
                          body, [("World champions", "/formula-1-world-champions/")],
                          {"@context": "https://schema.org", "@type": "ItemList", "name": "Formula 1 World Drivers' Champions",
                           "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": f"{c[0]}: {c[1]}"} for i, c in enumerate(reversed(CH))]}))

    # ---------- circuits ----------
    pages += build_circuits(A, RACES, race_url, gp_long, drv, by_code, total, done)
    # ---------- games and the F1 guide ----------
    pages += build_games()
    if A.get("LEARN"): pages += build_learn_pages(A["LEARN"], A, D)
    # ---------- pages people search for every weekend ----------
    pages += build_next_race(A, RACES, done, total, gp_long, race_url, drv)
    pages += build_results(A, RACES, done, gp_long, race_url, drv, sess, sdata)
    pages += build_stats(A, RACES, done, gp_long, race_url, drv, team_link, sess, sdata)
    pages += build_speed(A)
    # ---------- machine-readable data, llms.txt, robots.txt ----------
    write_api(A, D, C, RACES, wins, race_url, gp_long, dslug, tslug, done, total, champ_now)
    write_llms(A, D, C, RACES, done, total, champ_now, gp_long, race_url)
    write_robots()

    # ---------- sitemap: lastmod only moves when a page actually changes ----------
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    smp = os.path.join(ROOT, "sitemap.xml")
    old = dict(re.findall(r"<loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", open(smp).read())) if os.path.exists(smp) else {}
    urls = ["/"] + pages
    def lm(u):
        if u == "/": return today if CHANGED.get(f"/formula-1-standings-{YEAR}/") or SITE + "/" not in old else old[SITE + "/"]
        return today if CHANGED.get(u, True) or SITE + u not in old else old[SITE + u]
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"  <url><loc>{SITE}{u}</loc><lastmod>{lm(u)}</lastmod></url>\n" for u in urls) + "</urlset>\n"
    open(smp, "w").write(sm)
    print(f"Built {len(pages)} pages and sitemap.xml ({sum(1 for u in urls if lm(u) == today)} updated today)")


def fill_bits(b, d):
    st = d["stats"]
    rep = {"{ELEV}": st["elev"], "{VMAX}": st["vmax"], "{VMIN}": st["vmin"], "{FT}": st["fullThrottle"],
           "{DRV}": d["source"]["driverName"], "{GEARS}": st["gearChanges"], "{YEAR}": d["source"]["year"]}
    for k, v in rep.items(): b = b.replace(k, str(v))
    return b


def strip_tags(s): return re.sub(r"<[^>]+>", "", s)


def track_svg(d, w=720, h=480):
    """Circuit outline as inline SVG, drawn from the pole lap."""
    P = d["pts"][::3]
    xs, ys = [p[0] for p in P], [p[1] for p in P]
    sx, sy = max(xs) - min(xs), max(ys) - min(ys)
    k = min((w - 60) / sx, (h - 60) / sy)
    ox, oy = (w - sx * k) / 2 - min(xs) * k, (h + sy * k) / 2 + min(ys) * k
    pt = lambda x, y: (round(ox + x * k, 1), round(oy - y * k, 1))
    path = "M" + " L".join(f"{a},{b}" for a, b in (pt(p[0], p[1]) for p in P)) + " Z"
    sx0, sy0 = pt(d["pts"][0][0], d["pts"][0][1])
    labels = ""
    for c in sorted(d["corners"], key=lambda c: c["v"])[:4]:
        x, y = pt(d["pts"][c["i"]][0], d["pts"][c["i"]][1])
        labels += f'<g><circle cx="{x}" cy="{y}" r="4" fill="#E10600"/><text x="{x + 8}" y="{y - 8}" fill="#F1F3F7" font-size="13" font-family="monospace">{c["v"]} km/h</text></g>'
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="Map of the circuit" style="width:100%;height:auto;background:#12161E;border:1px solid #262C39;border-radius:4px">'
            f'<path d="{path}" fill="none" stroke="#000" stroke-width="12" stroke-linejoin="round"/>'
            f'<path d="{path}" fill="none" stroke="#e6e6e6" stroke-width="8" stroke-linejoin="round"/>'
            f'<path d="{path}" fill="none" stroke="#30343d" stroke-width="5" stroke-linejoin="round"/>'
            f'<rect x="{sx0 - 6}" y="{sy0 - 6}" width="12" height="12" fill="#fff" stroke="#000"/>{labels}</svg>')


def build_circuits(A, RACES, race_url, gp_long, drv, by_code, total, done):
    TI, SRC = A.get("TRACK_INFO") or {}, A.get("TRACK_SOURCES") or []
    out, rows = [], []
    order = sorted(TI.items(), key=lambda kv: kv[1]["rd"])
    for n, (sl, I) in enumerate(order):
        fp = os.path.join(ROOT, "data", "tracks", f"{sl}.json")
        if not os.path.exists(fp): continue
        d = json.load(open(fp)); st = d["stats"]; src = d["source"]
        r = next((x for x in RACES if x["rd"] == I["rd"]), None)
        laps = 78 if I["rd"] == 6 else math.ceil(305 / I["length"])
        L = A["LAP_RECORD"].get(str(I["rd"]))
        lt = fmt_lap(d["lapTime"]); avg = round(d["length"] / d["lapTime"] * 3.6)
        bits = [fill_bits(b, d) for b in I["bits"]]
        url = f"/circuits/{sl}/"
        gp = gp_long(r) if r else ""
        won = r and r.get("win") and r["win"] in by_code
        winner = f'{by_code[r["win"]]["first"]} {by_code[r["win"]]["last"]}' if won else None
        faq = [
            (f"How long is {I['full']}?", f"{I['full']} is {I['length']:.3f} km long, with {I['turns']} corners. The {YEAR} {gp} runs over {laps} laps, a race distance of {I['length'] * laps:.3f} km."),
            (f"What is the lap record at {I['full']}?", f"The race lap record is {L[0]}, set by {L[1]} ({L[2]}) in {L[3]}." if L else "There's no race lap record yet."),
            (f"Who was on pole for the {src['year']} {gp}?", f"{src['driverName']} ({src['team']}) took pole with a {lt}. On that lap the car reached {st['vmax']} km/h and averaged {avg} km/h."),
            (f"When was the first Formula 1 race at {I['full']}?", f"{I['firstGP']}."),
        ]
        if winner: faq.insert(3, (f"Who won the {YEAR} {gp}?", f"{winner} won the {YEAR} {gp}, in a race time of {r.get('time')}."))
        elif r: faq.insert(3, (f"When is the {YEAR} {gp}?", f"Round {r['rd']} of {total}, on {nice_date(r['race'])} ({r['dates']}). The race starts at {datetime.fromisoformat(r['race'].replace('Z', '+00:00')).strftime('%H:%M')} UTC."))
        tiles = [("Length", f"{I['length']:.3f} km"), ("Corners", I["turns"]), ("Race laps", laps), ("Lap record", L[0] if L else "—"),
                 (f"{src['year']} pole", lt), ("First F1 race", I["firstGP"])]
        nums = [("Top speed", f"{st['vmax']} km/h"), ("Slowest point", f"{st['vmin']} km/h"), ("Average speed", f"{avg} km/h"),
                ("Full throttle", f"{st['fullThrottle']}% of the lap"), ("Gear changes", st["gearChanges"]), ("Height change", f"{st['elev']} m")]
        prev = f'<a href="/circuits/{order[n - 1][0]}/">← {e(order[n - 1][1]["name"])}</a>' if n else "<span></span>"
        nxt = f'<a href="/circuits/{order[n + 1][0]}/">{e(order[n + 1][1]["name"])} →</a>' if n + 1 < len(order) else "<span></span>"
        body = f"""<h1>{e(I['full'])}</h1>
<p class="sub">{e(I['city'])} · Round {I['rd']} of the {YEAR} season{f' · <a href="{race_url(r["rd"])}">{e(gp)} {YEAR}</a>' if r else ''}</p>
<p class="lead">{e(I['full'])} is a {I['length']:.3f} km Formula 1 circuit in {e(I['city'])} with {I['turns']} corners, first used for a world championship Grand Prix in {I['firstGP']}. {f"{e(winner)} won the {YEAR} {e(gp)} here." if winner else (f"The {YEAR} {e(gp)} is on {nice_date(r['race'])}." if r else "")} {e(src['driverName'])}'s {src['year']} pole lap of {lt} peaked at {st['vmax']} km/h.</p>
<p><a class="btn" href="/#tracks/{sl}">Explore {e(I['name'])} in 3D</a></p>
{track_svg(d)}
<p class="note">Circuit outline drawn from {e(src['driverName'])}'s {src['year']} pole lap, with the four slowest corners marked.</p>
<div class="tiles">{''.join(f'<div class="tile"><span>{k}</span><b>{e(str(v))}</b></div>' for k, v in tiles)}</div>
<h2>Interesting facts</h2><ul>{''.join(f'<li>{b}</li>' for b in bits)}</ul>
<h2>The {src['year']} pole lap in numbers</h2>
<div class="tiles">{''.join(f'<div class="tile"><span>{k}</span><b>{e(str(v))}</b></div>' for k, v in nums)}</div>
<p class="note">Telemetry from {e(src['driverName'])} ({e(src['team'])}), {src['year']} {e(src['sessionName'].lower())}, via OpenF1.</p>
<h2>Questions and answers</h2>{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in faq)}
<p class="note">Sources: {', '.join(f'<a href="{u}" rel="noopener">{e(t)}</a>' for t, u in SRC if sl == "albert-park" or "Albert Park" not in t)}, <a href="https://openf1.org" rel="noopener">OpenF1</a>.</p>
<div class="pager">{prev}<a href="/circuits/">All circuits</a>{nxt}</div>"""
        place = {"@context": "https://schema.org", "@type": "SportsActivityLocation", "name": I["full"], "url": SITE + url,
                 "address": {"@type": "PostalAddress", "addressLocality": I["city"], "addressCountry": COUNTRY.get(r["short"], "") if r else ""},
                 "description": strip_tags(bits[0]) if bits else ""}
        faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
        title = f"{I['full']}: F1 track guide & lap record | {BRAND}"
        desc = f"{I['full']}, {I['city']}: {I['length']:.3f} km, {I['turns']} corners, {laps} laps. Lap record {L[0] if L else '—'}, {src['year']} pole {lt} by {src['driverName']}. Explore the track in 3D."
        out.append(page(url, title, desc, body, [("Circuits", "/circuits/"), (I["name"], url)], place, ld_list=[faq_ld]))
        rows.append(f'<tr><td class="pos">{I["rd"]}</td><td><a href="{url}">{e(I["full"])}</a></td><td>{e(I["city"])}</td><td class="n">{I["length"]:.3f} km</td><td class="n">{I["turns"]}</td><td class="n">{L[0] if L else "—"}</td><td class="n">{I["firstGP"]}</td></tr>')
    if rows:
        body = f"""<h1>F1 circuits {YEAR}</h1>
<p class="sub">All {len(rows)} tracks on the {YEAR} Formula 1 calendar, with length, corners, lap records and a 3D model of each.</p>
<p class="lead">Every circuit is rebuilt from a real pole lap: its shape, its height and the car's speed and gears all the way round. Open any of them in 3D on <a href="/#tracks">Pit Wall</a>.</p>
<div class="tbl"><table><thead><tr><th>Rd</th><th>Circuit</th><th>Location</th><th class="n">Length</th><th class="n">Corners</th><th class="n">Lap record</th><th class="n">First F1 race</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"""
        out.append(page("/circuits/", f"F1 circuits {YEAR}: every track, map, length and lap record | {BRAND}",
                        f"All {len(rows)} Formula 1 circuits of {YEAR}: length, corners, lap records, first F1 race and an interactive 3D model of every track.",
                        body, [("Circuits", "/circuits/")],
                        {"@context": "https://schema.org", "@type": "ItemList", "name": f"Formula 1 circuits {YEAR}",
                         "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/circuits/{sl}/", "name": I["full"]} for i, (sl, I) in enumerate(order)]}))
    return out


RX_PAGE = """<h1>F1 reaction test</h1>
<p class="sub">Five red lights. Lights out. How fast can you react?</p>
<div id="rx" tabindex="0" style="background:radial-gradient(120% 90% at 50% 0%,#1a1f2a,#07090d 70%);border:1px solid var(--line);border-radius:4px;min-height:340px;display:grid;place-items:center;align-content:center;gap:20px;padding:24px 12px;cursor:pointer;user-select:none;touch-action:manipulation;outline:none">
<div id="rxg" style="display:flex;gap:clamp(8px,2vw,14px);background:#05070a;border:1px solid #1d2230;border-radius:8px;padding:12px" aria-hidden="true"></div>
<div id="rxt" style="font:700 clamp(40px,9vw,68px)/1 var(--fm);min-height:1em" aria-live="polite"></div>
<div id="rxm" style="color:var(--muted);text-align:center;max-width:44ch">Can you beat Bottas's 0.201s? Tap here, or press Space, to start. When all five lights go out, tap as fast as you can.</div>
</div>
<div class="tiles"><div class="tile"><span>Your best</span><b id="rxb">–</b></div><div class="tile"><span>The time to beat</span><b>0.201s</b></div><div class="tile"><span>Average human</span><b>~0.25s</b></div></div>
<h2>How the F1 start works</h2>
<p>At the start of a Grand Prix, five pairs of red lights come on one after another, a second apart. After all five are lit there's a short, random pause, then they all go out together. That's the signal to go. React too early and it's a jump start; the stewards hand out a penalty.</p>
<h2>The famous 0.201s</h2>
<p>At the 2017 Austrian Grand Prix, Valtteri Bottas got away so fast that rivals thought he had jumped the start. The FIA looked at the data, found he had reacted in 0.201 seconds, and let his win stand. His time was measured from lights out to the car moving; yours here is from lights out to your tap.</p>
<h2>More to play</h2>
<p>Try <a href="/f1-qualifying-game/">Pit Wall Dash</a>, a three-lap qualifying game against the 2026 grid, or open the <a href="/#games">games page</a> for your full history.</p>
<script>
(function(){var st="idle",T=[],t0=0,best=null;try{best=parseFloat(localStorage.getItem("pw_rx_best"))||null}catch(e){}
var g=document.getElementById("rxg"),tt=document.getElementById("rxt"),m=document.getElementById("rxm"),b=document.getElementById("rxb"),box=document.getElementById("rx");
for(var i=0;i<5;i++){var c=document.createElement("div");c.style.cssText="display:grid;gap:8px;background:#0c0f15;border-radius:6px;padding:7px";c.innerHTML='<i style="display:block;width:clamp(30px,8vw,52px);aspect-ratio:1;border-radius:50%;background:#2a0a0a"></i><i style="display:block;width:clamp(30px,8vw,52px);aspect-ratio:1;border-radius:50%;background:#2a0a0a"></i>';g.appendChild(c)}
function lit(n){[].forEach.call(g.children,function(c,i){[].forEach.call(c.children,function(l){l.style.background=i<n?"radial-gradient(circle at 40% 35%,#ff6a5e,#e10600 55%,#8a0300)":"#2a0a0a";l.style.boxShadow=i<n?"0 0 20px 3px rgba(225,6,0,.45)":"none"})})}
function show(){b.textContent=best?(best/1000).toFixed(3)+"s":"–"}show();
function start(){st="arm";tt.textContent="";tt.style.color="";lit(0);m.textContent="Wait for it…";for(var i=1;i<=5;i++)(function(i){T.push(setTimeout(function(){lit(i);if(i===5){st="wait";T.push(setTimeout(function(){requestAnimationFrame(function(){if(st!=="wait")return;lit(0);t0=performance.now();st="go";m.textContent="GO!"})},200+Math.random()*2800))}},i*1000))})(i)}
function press(){var now=performance.now();
 if(st==="idle"||st==="done")return start();
 if(st==="arm"||st==="wait"){T.forEach(clearTimeout);T=[];st="done";lit(0);tt.textContent="JUMP START";tt.style.color="#E10600";m.textContent="You went before the lights went out. Tap to try again.";return}
 if(st==="go"){var ms=now-t0;st="done";if(ms<100){tt.textContent=(ms/1000).toFixed(3);tt.style.color="#E10600";m.textContent="Under 0.1s is a guess, not a reaction. Tap to go again.";return}
  var pb=!best||ms<best;if(pb){best=ms;try{localStorage.setItem("pw_rx_best",ms.toFixed(1))}catch(e){}}show();
  tt.textContent=(ms/1000).toFixed(3)+"s";tt.style.color=pb?"#B54BE8":ms<250?"#2FD480":"#F1F3F7";
  var gap=(ms-201)/1000;m.textContent=(pb?"New personal best! ":"")+(ms<=201?"You beat Bottas by "+(-gap).toFixed(3)+"s! ":gap.toFixed(3)+"s off Bottas's 0.201s. ")+"Tap to go again."}}
box.addEventListener("pointerdown",function(e){if(e.button>0)return;e.preventDefault();press()});
box.addEventListener("keydown",function(e){if(e.key===" "||e.key==="Enter"){e.preventDefault();if(!e.repeat)press()}});})();
</script>"""

QG_PAGE = """<h1>F1 qualifying game</h1>
<p class="sub">Pit Wall Dash: three flying laps, 22 drivers to beat.</p>
<p class="lead">Take your team's car out for qualifying at Pit Wall Park. Your best of three laps goes on the timing sheet against the whole 2026 grid. A ghost car of the driver just ahead shows you where you're losing time, with live delta and purple, green and yellow sectors like the real timing screens.</p>
<p><a class="btn" href="/#games">Play Pit Wall Dash</a></p>
<h2>How to play</h2>
<ul><li><b>Steer</b> with ← → or A and D. On a phone, hold the left or right side of the screen.</li>
<li><b>Brake</b> with ↓ or S, or the BRAKE button. The car follows the track; arrive at a corner too fast and it slides wide.</li>
<li><b>ERS boost</b> with ↑ or W, or the ⚡ button. It refills every lap, so spend it on the straights.</li>
<li><b>Track limits</b>: put all four wheels off the track and the lap is deleted.</li>
<li>The racing line turns red where you need to brake, and corner signs show the speed each corner can be taken at.</li></ul>
<h2>Where will you qualify?</h2>
<p>P1 is pole position. P2 to P10 make it into Q3, P11 to P16 are out in Q2, and P17 or lower are out in Q1. Most first runs end up in the midfield; braking later and using ERS well gets you to the front.</p>
<p>Warming up? Try the <a href="/f1-reaction-test/">F1 reaction test</a> first.</p>"""


def build_games():
    out = []
    out.append(page("/f1-reaction-test/", f"F1 reaction test: can you beat Bottas's 0.201s? | {BRAND}",
                    "Free F1 reaction time test with the real five-light start sequence. Beat Valtteri Bottas's famous 0.201s start from the 2017 Austrian Grand Prix. Works on phone and desktop.",
                    RX_PAGE, [("F1 reaction test", "/f1-reaction-test/")],
                    {"@context": "https://schema.org", "@type": "WebApplication", "name": "F1 reaction test", "applicationCategory": "GameApplication",
                     "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "url": f"{SITE}/f1-reaction-test/"}))
    out.append(page("/f1-qualifying-game/", f"F1 qualifying game: beat the 2026 grid in Pit Wall Dash | {BRAND}",
                    "Free browser F1 qualifying game: three flying laps, a ghost car to chase, sector times and the 2026 grid to beat. Play on phone or desktop.",
                    QG_PAGE, [("F1 qualifying game", "/f1-qualifying-game/")],
                    {"@context": "https://schema.org", "@type": "VideoGame", "name": "Pit Wall Dash", "genre": "Racing", "gamePlatform": "Web browser",
                     "applicationCategory": "GameApplication", "operatingSystem": "Any", "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "url": f"{SITE}/#games"}))
    return out


LEARN_CSS = """<style>
.ln-svg,.ln-tyre{display:block;width:100%;height:auto;border-radius:4px;background:#12161E}
.ln-t{font-family:var(--fd);font-weight:700;font-size:12px;letter-spacing:.06em;fill:#F1F3F7;text-transform:uppercase}
.ln-t.y{fill:#FFC93C}.ln-t.r{fill:#ff5a52}.ln-t.g{fill:#2FD480}.ln-t.w{fill:#fff}.ln-t.k{fill:#111}.ln-t.s{font-size:10px;fill:#B9C0CF}.ln-t.big{font-size:30px;font-family:var(--fm)}
.ln-gear{font-family:var(--fm);font-weight:700;font-size:84px;fill:#fff}
.ln-dash,.ln-air{animation:lnDash 1.2s linear infinite}@keyframes lnDash{to{stroke-dashoffset:-24}}
.ln-aero .ln-rflap{transform-box:fill-box;transform-origin:center;transform:rotate(-38deg)}.ln-aero .ln-fflap{transform-box:fill-box;transform-origin:center;transform:rotate(-24deg)}
.ln-diff .ln-whl{animation:lnSpin .9s linear infinite}@keyframes lnSpin{to{transform:translateX(5px)}}
.lg{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}.lg article{background:var(--panel);border:1px solid var(--line);border-radius:4px;overflow:hidden}
.lg .tx{padding:12px 14px}.lg h3{margin:0 0 4px}.lg .k{color:var(--red);font:700 12px var(--fd);text-transform:uppercase;letter-spacing:.08em}.lg p{margin:6px 0 0;font-size:15px}
.tyres{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px}.tyres div{background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:10px}
@media (prefers-reduced-motion:reduce){.ln-dash,.ln-air,.ln-diff .ln-whl{animation:none}}
</style>"""


LEARN_TOPICS = [
    ("what-is-formula-1", "about", "What is Formula 1?", "What is Formula 1? F1 explained for beginners",
     "What Formula 1 is, how fast the cars go, how they're built, and a brief history of F1 from 1950 to the 2026 rules, with animated pictures."),
    ("race-weekend-format", "weekend", "Race weekend & points", "F1 race weekend explained: practice, qualifying, sprint and the points system",
     "How an F1 weekend works: FP1, FP2, FP3, Sprint Qualifying, the Sprint, the Q1-Q2-Q3 qualifying knockout, the Grand Prix, and how many points each finish is worth."),
    ("trophies-and-championships", "trophies", "Trophies & championships", "F1 trophies and championships: Drivers' and Constructors' titles explained",
     "The F1 World Drivers' and Constructors' Championships explained: who has won the most titles, how they're decided, and the prizes at every race."),
    ("track-terms", "track", "Track talk", "F1 terms explained: racing line, apex, kerbs, chicanes, VSC and flags",
     "The words you hear on an F1 broadcast, explained with animations: racing line and apex, kerbs, chicanes, hairpins, slipstream, track limits, pit lane, the virtual safety car and every flag."),
    ("f1-tyres-explained", "tyres", "Tyres", "F1 tyres explained: soft, medium, hard, intermediate and wet (2026)",
     "How Formula 1 tyres work in 2026: the C1 to C5 compounds, soft, medium and hard, intermediates and wets, the two-compound rule, and tyre words like deg, graining and undercut."),
    ("f1-steering-wheel-buttons", "wheel", "The steering wheel", "F1 steering wheel buttons explained: what every control does",
     "What the buttons, dials and paddles on an F1 steering wheel do: pit limiter, radio, overtake mode, brake balance, differential, shift lights and more."),
    ("f1-car-technology-2026", "tech", "Car tech & 2026 rules", "F1 2026 car technology explained: active aero, overtake mode, ERS and more",
     "The tech inside a 2026 F1 car: the hybrid power unit, ERS, active aerodynamics (straight and corner mode), overtake mode, the differential, brakes, gearbox, halo, size and weight."),
    ("people-of-f1", "people", "The people of F1", "Who's who in F1: drivers, race engineers, strategists, pit crews, marshals and stewards",
     "The people who make a Grand Prix happen: drivers, team principals, race engineers, strategists, pit crews, mechanics, designers, marshals, race control, stewards, the safety car and more."),
]
SEO_TITLE = {"what-is-formula-1": "What is Formula 1? F1 explained for beginners", "race-weekend-format": "F1 race weekend & points system explained",
             "trophies-and-championships": "F1 championships & trophies explained", "track-terms": "F1 terms explained: apex, kerbs, VSC & flags",
             "f1-tyres-explained": "F1 tyres explained: compounds & colours (2026)", "f1-steering-wheel-buttons": "F1 steering wheel buttons explained",
             "f1-car-technology-2026": "F1 2026 tech explained: active aero, ERS & more", "people-of-f1": "Who's who in F1: engineers, pit crews & more"}
TYRE_TALK = [("Degradation (\"deg\")", "The tyre slowly losing grip as it wears and heats up, so lap times drop off."),
             ("Graining", "Little rolls of rubber tear off and stick to the surface, making the tyre slide until they wear away."),
             ("Blistering", "The rubber gets so hot underneath that pockets bubble up and break off."),
             ("Undercut", "Pitting before a rival so your fresh tyres let you set faster laps and jump ahead when they stop."),
             ("Overcut", "Staying out longer than a rival and using clear track to gain time instead."),
             ("Marbles", "Bits of worn rubber that collect off the racing line and feel like driving on ball bearings.")]


def article_ld(url, headline, desc):
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "description": desc, "url": url,
            "inLanguage": "en", "dateModified": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "author": {"@type": "Organization", "name": BRAND, "url": SITE + "/"}, "publisher": {"@type": "Organization", "name": BRAND, "url": SITE + "/"}}


def faq_ld(qa):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}} for q, a in qa]}


def qa_html(qa): return "<h2>Questions and answers</h2>" + "".join(f"<h3>{e(q)}</h3><p>{a}</p>" for q, a in qa)


def build_learn_pages(L, A, D):
    """The Learn F1 hub plus one page per topic, each answering the questions people search for."""
    out = []
    card = lambda t, kick: f'<article id="{t["id"]}">{t["svg"]}<div class="tx"><h3>{e(t["name"])}</h3><div class="k">{e(kick)}</div><p>{t["body"]}</p></div></article>'
    CH = A.get("CHAMPIONS") or []
    counts = {}
    for c in CH: counts[c[1]] = counts.get(c[1], 0) + 1
    top = sorted(counts.items(), key=lambda x: -x[1])[:8]
    pts = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
    def topic_body(key):
        if key == "about":
            return (f"""<p class="lead">Formula 1 is the world's fastest racing championship. Eleven teams build their own cars from scratch, pushing engineering, aerodynamics, materials and software as far as the rules allow, and 22 drivers race them at 23 Grands Prix around the world in 2026.</p>
<div class="tiles">{''.join(f'<div class="tile"><span>{e(l)}</span><b>{n:,}{e(u)}</b></div>' if n != 1950 else f'<div class="tile"><span>{e(l)}</span><b>1950</b></div>' for n, u, l in L.get("nums", []))}</div>
<h2>Pushing everything to the limit</h2><div class="lg">{''.join(f'<article>{c["svg"]}<div class="tx"><h3>{e(c["t"])}</h3><p>{e(c["d"])}</p></div></article>' for c in L.get("limit", []))}</div>
<h2>Anatomy of an F1 car</h2><dl>{''.join(f'<dt><b>{e(x["name"])}</b></dt><dd>{e(x["txt"])}</dd>' for x in L.get("parts", []))}</dl>
<h2>A brief history of F1</h2><ul>{''.join(f'<li><b>{y}: {e(t)}.</b> {e(d)}</li>' for y, t, d in L.get("history", []))}</ul>""",
                    [("What is Formula 1?", "Formula 1 (F1) is the top level of single-seater motor racing: 11 teams and 22 drivers race purpose-built cars at 23 Grands Prix around the world in 2026, competing for the Drivers' and Constructors' world championships."),
                     ("How fast is an F1 car?", "F1 cars reach around 350 km/h on the longest straights; on 2026 pole laps the highest top speed was 350 km/h at Mexico City. They brake at more than 5 g. See <a href=\"/how-fast-is-an-f1-car/\">top speeds at every track</a>."),
                     ("How much horsepower does an F1 car have?", "About 1,000 hp in 2026: roughly 400 kW from the 1.6-litre V6 turbo engine and up to 350 kW from the electric motor (MGU-K)."),
                     ("When did Formula 1 start?", "The first World Championship race was held at Silverstone on 13 May 1950. Nino Farina won it and became the first world champion.")])
        if key == "weekend":
            sess = "".join(f'<article id="{s["id"]}">{s["svg"]}<div class="tx"><h3>{e(s["name"])}</h3><div class="k">{e(s["when"])} · {e(s["time"])}</div><p>{s["body"]}</p></div></article>' for s in L.get("sess", []))
            return (f"""<p class="lead">A Grand Prix weekend runs from Friday to Sunday. Most weekends have three practice sessions, qualifying on Saturday and the race on Sunday. Six weekends in 2026 are <b>sprint weekends</b>, with Sprint Qualifying on Friday and a short Sprint race on Saturday.</p>
<h2>Normal weekend</h2><p><b>Friday:</b> Practice 1, Practice 2. <b>Saturday:</b> Practice 3, Qualifying. <b>Sunday:</b> Grand Prix.</p>
<h2>Sprint weekend</h2><p><b>Friday:</b> Practice 1, Sprint Qualifying. <b>Saturday:</b> Sprint, Qualifying. <b>Sunday:</b> Grand Prix.</p>
<h2>Every session explained</h2><div class="lg">{sess}</div>
<h2>The F1 points system</h2>
<div class="tbl"><table><thead><tr><th>Finish</th>{''.join(f'<th class="n">P{i+1}</th>' for i in range(10))}</tr></thead><tbody>
<tr><td>Grand Prix</td>{''.join(f'<td class="n">{p}</td>' for p in pts)}</tr>
<tr><td>Sprint</td>{''.join(f'<td class="n">{p}</td>' for p in [8,7,6,5,4,3,2,1,0,0])}</tr></tbody></table></div>
<p>A perfect weekend is worth 25 points, or 33 on a sprint weekend. There has been no bonus point for the fastest lap since 2025. Both of a team's drivers score for the Constructors' Championship, and ties are broken by countback: most wins, then most second places, and so on.</p>""",
                    [("How many points do you get for winning an F1 race?", "25 points. The top ten score 25, 18, 15, 12, 10, 8, 6, 4, 2 and 1."),
                     ("How many points is an F1 sprint worth?", "The top eight in a Sprint score 8, 7, 6, 5, 4, 3, 2 and 1 points."),
                     ("How does F1 qualifying work?", "It's a knockout in three parts. In Q1 (18 minutes) the slowest six of the 22 cars are eliminated, in Q2 (15 minutes) another six go, and the top ten fight for pole position in Q3 (12 minutes)."),
                     ("What is a sprint race in F1?", "A short race of about 100 km on Saturday of a sprint weekend, roughly a third of a Grand Prix, with no compulsory pit stop. Its grid is set by Sprint Qualifying on Friday."),
                     ("How long is an F1 race?", "About 305 km (Monaco is shorter), usually around 90 minutes, with a two-hour limit."),
                     ("Is there a point for the fastest lap?", "Not any more. The bonus point for the fastest lap was dropped from 2025.")])
        if key == "trophies":
            wcc = L.get("wcc", [])
            return (f"""<p class="lead">Two titles are decided every season: the <b>World Drivers' Championship</b> for the driver with the most points, and the <b>World Constructors' Championship</b> for the team. Both are presented at the FIA's prize-giving at the end of the year.</p>
<h2>World Drivers' Championship</h2><p>Awarded since 1950. Every point a driver scores in Grands Prix and Sprints counts. {len(counts)} different drivers have been world champion; the youngest is Kimi Antonelli, who won in 2026 at the age of 20, and the oldest Juan Manuel Fangio, 46 when he won in 1957.</p>
<div class="tbl"><table><thead><tr><th>Driver</th><th class="n">Titles</th></tr></thead><tbody>{''.join(f'<tr><td>{e(n)}</td><td class="n">{k}</td></tr>' for n, k in top)}</tbody></table></div>
<p><a href="/formula-1-world-champions/">Every world champion since 1950</a>.</p>
<h2>World Constructors' Championship</h2><p>Awarded since 1958, when Vanwall won it. Both of a team's drivers' points count, and the final order decides each team's share of the sport's prize money.</p>
<div class="tbl"><table><thead><tr><th>Team</th><th class="n">Titles (to 2025)</th></tr></thead><tbody>{''.join(f'<tr><td>{e(n)}</td><td class="n">{k}</td></tr>' for n, k, c in wcc)}</tbody></table></div>
<h2>Prizes at every race</h2><ul>{''.join(f'<li><b>{e(t)}.</b> {e(d)}</li>' for i, t, d in L.get("awards", []))}</ul>
<p class="note">Constructors' title counts: Autosport (to 2024) plus McLaren's 2025 title.</p>""",
                    [("Who has won the most F1 world championships?", f"Michael Schumacher and Lewis Hamilton, with seven titles each. Juan Manuel Fangio won five."),
                     ("Which team has the most F1 constructors' championships?", "Ferrari, with 16 titles, followed by McLaren (10), Williams (9) and Mercedes (8), counting to the end of 2025."),
                     ("Who is the youngest F1 world champion?", "Kimi Antonelli, who won the 2026 title for Mercedes at the age of 20."),
                     ("What is the difference between the Drivers' and Constructors' Championship?", "The Drivers' Championship ranks individual drivers by their points; the Constructors' Championship adds up the points of both of a team's drivers to rank the teams.")])
        if key == "track":
            terms = L.get("terms", [])
            ask = {"line": "What is the racing line and apex in F1?", "kerbs": "What are kerbs in F1?", "chicane": "What is a chicane in F1?", "hairpin": "What is a hairpin in F1?",
                   "tow": "What is slipstream (a tow) in F1?", "limits": "What are track limits in F1?", "vsc": "What is a virtual safety car (VSC) in F1?", "flags": "What do the flags mean in F1?", "pit": "How does the pit lane work in F1?"}
            return (f'<p class="lead">The words you hear on an F1 broadcast, each with an animated picture.</p><div class="lg">{"".join(card(t, t["short"]) for t in terms)}</div>',
                    [(ask[t["id"]], t["body"]) for t in terms if t["id"] in ask])
        if key == "tyres":
            ty = L.get("tyres", [])
            return (f"""<p class="lead">Tyres are the only part of the car touching the track, and managing them decides races.</p>
<div class="tyres">{''.join(f'<div>{t["svg"]}<h3>{e(t["name"])}</h3><p class="note">{e(t["tag"])}</p><p>{e(t["txt"])}</p></div>' for t in ty)}</div>
<h2>How tyres work in 2026</h2><ul><li><b>Five dry compounds, C1 to C5.</b> C1 is the hardest and C5 the softest; the C6 used in 2025 was dropped.</li>
<li><b>Three per weekend.</b> Pirelli picks three: the hardest is called the Hard (white), the middle the Medium (yellow), the softest the Soft (red).</li>
<li><b>Two for the rain:</b> Intermediates (green) and full Wets (blue).</li>
<li><b>Two compounds in a dry race.</b> Every driver must use at least two different dry compounds, so everyone pits at least once.</li>
<li><b>Narrower for 2026.</b> Still 18-inch wheels, but the fronts are 25 mm narrower and the rears 30 mm narrower.</li></ul>
<h2>Tyre talk</h2><dl>{''.join(f'<dt><b>{e(k)}</b></dt><dd>{e(v)}</dd>' for k, v in TYRE_TALK)}</dl>""",
                    [("What are the different F1 tyres?", "Three dry tyres each weekend, Soft (red), Medium (yellow) and Hard (white), chosen from five compounds C1 to C5, plus Intermediates (green) and full Wets (blue) for rain."),
                     ("Why do F1 cars have to change tyres?", "In a dry race every driver must use at least two different dry compounds, and tyres lose grip as they wear, so drivers make at least one pit stop."),
                     ("What is the undercut in F1?", TYRE_TALK[3][1]),
                     ("What is tyre degradation in F1?", TYRE_TALK[0][1])])
        if key == "wheel":
            ct = L.get("ctrl", [])
            dl = "".join(f"<dt><b>{e(c['name'])}</b></dt><dd>{e(c['txt'])}</dd>" for c in ct)
            return (f'<p class="lead">A modern F1 steering wheel has 20 or more buttons, dials and paddles. These are the ones you\'ll hear about most. <a href="/#learn/wheel">Spin and click the 3D wheel</a>.</p><dl>{dl}</dl>',
                    [(f"What does the {c['name']} do on an F1 steering wheel?", c["txt"]) for c in ct if c["id"] in ("pit", "ot", "bbal", "diff", "lights", "clutch")])
        if key == "tech":
            tech = L.get("tech", [])
            return (f'<p class="lead">2026 brought the biggest rule change in years: active aerodynamics, a near 50:50 split of engine and electric power, 100% sustainable fuel, and smaller, lighter cars.</p><div class="lg">{"".join(card(t, t["kick"]) for t in tech)}</div>',
                    [(f"What is {t['name'].lower()} in F1?", t["body"]) for t in tech if t["id"] in ("aero", "ot", "ers", "diff", "halo")])
        if key == "people":
            ppl = L.get("people", [])
            return (f'<p class="lead">A Grand Prix takes thousands of people: around a thousand or more at each big team, plus FIA officials, tyre engineers, medical crews and the marshals.</p><div class="lg">{"".join(card(t, t["kick"]) for t in ppl)}</div>',
                    [(f"What does {('an' if t['name'][0] in 'AEIOU' else 'a')} {t['name'].lower()} do in F1?", t["body"]) for t in ppl if t["id"] in ("tp", "engineer", "strategist", "pitcrew", "marshals", "stewards")])
        return ("", [])
    for n, (slug_, key, short, h1, desc) in enumerate(LEARN_TOPICS):
        url = f"/learn-f1/{slug_}/"
        content, qa = topic_body(key)
        prev = f'<a href="/learn-f1/{LEARN_TOPICS[n-1][0]}/">← {e(LEARN_TOPICS[n-1][2])}</a>' if n else '<a href="/learn-f1/">← Learn F1</a>'
        nxt = f'<a href="/learn-f1/{LEARN_TOPICS[n+1][0]}/">{e(LEARN_TOPICS[n+1][2])} →</a>' if n + 1 < len(LEARN_TOPICS) else '<a href="/learn-f1/">Learn F1 →</a>'
        body = f"""<h1>{e(h1)}</h1><p class="sub">Learn F1 · {e(short)} · <a href="/#learn/{key}">Open the interactive version</a></p>
{content}{qa_html(qa) if qa else ''}
<div class="pager">{prev}<a href="/learn-f1/">All topics</a>{nxt}</div>"""
        out.append(page(url, f"{SEO_TITLE.get(slug_, h1)} | {BRAND}", desc, body, [("Learn F1", "/learn-f1/"), (short, url)], article_ld(SITE + url, h1, desc),
                        extra_head=LEARN_CSS, ld_list=[faq_ld(qa)] if qa else None, og=f"learn-{key}"))
    hub = f"""<h1>Learn F1: Formula 1 explained for beginners</h1>
<p class="sub">New to F1, or want to understand what the commentators are on about? Start here.</p>
<p class="lead">Formula 1 is the world's fastest racing championship: 11 teams, 22 drivers, 23 Grands Prix and cars that reach 350 km/h. These guides explain it all with animated pictures, from how a race weekend works to what every button on the steering wheel does.</p>
<div class="lg">{''.join(f'<article><div class="tx"><div class="k">{i+1:02d}</div><h3><a href="/learn-f1/{s}/">{e(short)}</a></h3><p>{e(d)}</p></div></article>' for i, (s, k, short, h1, d) in enumerate(LEARN_TOPICS))}</div>
<h2>Try it hands-on</h2><ul><li><a href="/#learn">The interactive Learn F1 section</a>: a 3D car and steering wheel you can spin and click.</li>
<li><a href="/f1-reaction-test/">F1 reaction test</a>: can you beat Valtteri Bottas's 0.201s start?</li>
<li><a href="/f1-qualifying-game/">F1 qualifying game</a>: three laps against the 2026 grid.</li>
<li><a href="/circuits/">Every 2026 circuit</a>, with maps and pole-lap telemetry.</li></ul>"""
    hub_qa = [("Is F1 hard to understand?", "Not once you know the basics: 22 drivers race for points over a season, the fastest in Saturday's qualifying starts at the front, and the top ten in Sunday's race score points. These guides explain the rest."),
              ("How many races are in an F1 season?", "23 Grands Prix in 2026, from Australia in March to Abu Dhabi in December, six of them with an extra Saturday sprint."),
              ("What is the difference between F1 and other motorsport?", "Every F1 team designs and builds its own car, so the championship is as much an engineering contest as a driving one.")]
    out.append(page("/learn-f1/", f"Learn F1: Formula 1 explained for beginners (2026 guide) | {BRAND}",
                    "Formula 1 explained for beginners: what F1 is, how a race weekend and the points work, tyres, the steering wheel, 2026 car tech, the people of F1 and the trophies, with animated pictures.",
                    hub + qa_html(hub_qa), [("Learn F1", "/learn-f1/")], article_ld(SITE + "/learn-f1/", "Learn F1: Formula 1 explained for beginners", "A beginner's guide to Formula 1."),
                    extra_head=LEARN_CSS, ld_list=[faq_ld(hub_qa)], og="learn"))
    return out


def fetch_next_schedule(nxt):
    """Session times for the next round from OpenF1 (kept in data/ so builds work offline too)."""
    cache = os.path.join(ROOT, "data", "next_schedule.json")
    try:
        import urllib.request
        start = datetime.fromisoformat(nxt["race"].replace("Z", "+00:00"))
        url = f"https://api.openf1.org/v1/sessions?year={YEAR}&date_start%3E={(start - timedelta(days=4)).strftime('%Y-%m-%d')}&date_start%3C={(start + timedelta(days=1)).strftime('%Y-%m-%d')}"
        rows = json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "pitwall-pages"}), timeout=20))
        sess = sorted(({"name": r["session_name"], "start": r["date_start"]} for r in rows), key=lambda r: r["start"])
        if sess:
            json.dump({"round": nxt["rd"], "sessions": sess}, open(cache, "w"), indent=1)
            return sess
    except Exception as ex:
        print("  next-race schedule: OpenF1 not reachable, using saved copy", type(ex).__name__)
    if os.path.exists(cache):
        c = json.load(open(cache))
        if c.get("round") == nxt["rd"]: return c["sessions"]
    return [{"name": "Race", "start": nxt["race"]}]


def build_next_race(A, RACES, done, total, gp_long, race_url, drv):
    nxt = next((r for r in RACES if r["rd"] == done + 1), None)
    TI = A.get("TRACK_INFO") or {}
    last = RACES[done - 1] if done else None
    if not nxt:
        body = f"<h1>Next F1 race</h1><p class=\"lead\">The {YEAR} season is complete. The {YEAR + 1} calendar will appear here when it's confirmed.</p>"
        return [page("/next-f1-race/", f"Next F1 race | {BRAND}", f"The {YEAR} Formula 1 season is complete.", body, [("Next F1 race", "/next-f1-race/")], og="next-race")]
    name = gp_long(nxt)
    sess = fetch_next_schedule(nxt)
    csl = next((k for k, v in TI.items() if v["rd"] == nxt["rd"]), None)
    I = TI.get(csl, {})
    fmt = lambda iso: datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)
    rows = "".join(f'<tr><td>{e(s["name"])}</td><td>{fmt(s["start"]).strftime("%a %d %b")}</td><td class="n">{fmt(s["start"]).strftime("%H:%M")} UTC</td><td class="n" data-local="{fmt(s["start"]).isoformat()}"></td></tr>' for s in sess)
    race_dt = fmt(nxt["race"])
    sprint = any("Sprint" in s["name"] for s in sess)
    lastline = f'The last race, the {e(gp_long(last))}, was won by {drv(last["win"])}.' if last and last.get("win") else ""
    body = f"""<h1>Next F1 race: {e(name)} {YEAR}</h1>
<p class="sub">Round {nxt["rd"]} of {total} · {e(nxt["circuit"])}, {e(nxt["place"])} · {e(nxt["dates"])} {YEAR}{" · Sprint weekend" if sprint else ""}</p>
<p class="lead">The next Formula 1 race is the <b>{e(name)}</b> on <b>{race_dt.strftime("%A %d %B %Y")}</b>, starting at <b>{race_dt.strftime("%H:%M")} UTC</b> (<span data-local="{race_dt.isoformat()}" data-full="1"></span>). {lastline}</p>
<div class="tiles"><div class="tile"><span>Lights out in</span><b id="cd">–</b></div><div class="tile"><span>Circuit</span><b style="font-size:16px">{e(nxt["circuit"])}</b></div>{f'<div class="tile"><span>Length</span><b>{I["length"]:.3f} km</b></div><div class="tile"><span>Race laps</span><b>{78 if I.get("rd") == 6 else math.ceil(305 / I["length"])}</b></div>' if I else ""}</div>
<h2>Weekend schedule</h2>
<div class="tbl"><table><thead><tr><th>Session</th><th>Day</th><th class="n">UTC</th><th class="n">Your time</th></tr></thead><tbody>{rows}</tbody></table></div>
<p style="margin-top:14px"><a class="btn" href="/#calendar">Live countdowns on Pit Wall</a> {f'<a class="btn" href="/circuits/{csl}/" style="margin-left:6px">About {e(I.get("name", "the circuit"))}</a> <a class="btn" href="/#tracks/{csl}" style="margin-left:6px">Explore the track in 3D</a>' if csl else ''}</p>
<h2>Championship so far</h2><p>After round {done}, see the <a href="/formula-1-standings-{YEAR}/">{YEAR} standings</a>, every <a href="/f1-results-{YEAR}/">race result</a>, and the <a href="{race_url(nxt["rd"])}">{e(name)} page</a> for results as each session finishes.</p>
<script>
(function(){{document.querySelectorAll("[data-local]").forEach(function(el){{var d=new Date(el.getAttribute("data-local"));el.textContent=el.dataset.full?d.toLocaleString([], {{weekday:"short",day:"numeric",month:"short",hour:"2-digit",minute:"2-digit"}})+" your time":d.toLocaleString([], {{weekday:"short",hour:"2-digit",minute:"2-digit"}})}});
var t=new Date("{race_dt.isoformat()}").getTime(),c=document.getElementById("cd");function f(){{var s=Math.max(0,(t-Date.now())/1000),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);c.textContent=s>0?d+"d "+h+"h "+m+"m":"Race day!"}}f();setInterval(f,30000)}})();
</script>"""
    ld = {"@context": "https://schema.org", "@type": "SportsEvent", "name": f"{YEAR} {name}", "sport": "Formula 1", "startDate": nxt["race"],
          "eventStatus": "https://schema.org/EventScheduled", "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
          "location": {"@type": "Place", "name": nxt["circuit"], "address": {"@type": "PostalAddress", "addressLocality": nxt["place"], "addressCountry": COUNTRY.get(nxt["short"], "")}},
          "url": SITE + "/next-f1-race/", "subEvent": [{"@type": "SportsEvent", "name": f'{name}: {s["name"]}', "startDate": s["start"]} for s in sess]}
    qa = [(f"When is the next F1 race?", f"The {name} on {race_dt.strftime('%A %d %B %Y')} at {race_dt.strftime('%H:%M')} UTC, at {nxt['circuit']} in {nxt['place']}."),
          (f"What time does the {name} start?", f"Lights out is at {race_dt.strftime('%H:%M')} UTC on {race_dt.strftime('%d %B')}. " + (f"Qualifying is at {fmt(next(s['start'] for s in sess if s['name'] == 'Qualifying')).strftime('%H:%M')} UTC on {fmt(next(s['start'] for s in sess if s['name'] == 'Qualifying')).strftime('%A')}." if any(s['name'] == 'Qualifying' for s in sess) else ""))]
    return [page("/next-f1-race/", f"Next F1 race: {name} {YEAR} start time & schedule | {BRAND}",
                 f"The next F1 race is the {name} on {race_dt.strftime('%d %B %Y')}, lights out {race_dt.strftime('%H:%M')} UTC. Full weekend schedule in your time zone, countdown and circuit guide.",
                 body + qa_html(qa), [("Next F1 race", "/next-f1-race/")], ld, ld_list=[faq_ld(qa)], og="next-race")]


def build_results(A, RACES, done, gp_long, race_url, drv, sess, sdata):
    rows, items = [], []
    for r in RACES[:done]:
        have = sess.get(r["rd"], {})
        pod, pole = [], None
        if have.get("Race"):
            d = sdata(have["Race"]); dm = {x["n"]: x["c"] for x in d["drivers"]}
            pod = [dm.get(x[1]) for x in d["result"][:3]]
        if have.get("Qualifying"):
            d = sdata(have["Qualifying"]); dm = {x["n"]: x["c"] for x in d["drivers"]}
            pole = dm.get(d["result"][0][1]) if d["result"] else None
        spr = A["SPRINT_WIN"].get(str(r["rd"]))
        rows.append(f'<tr><td class="pos">{r["rd"]}</td><td><a href="{race_url(r["rd"])}">{e(gp_long(r))}</a></td>{"".join(f"<td>{drv(c) if c else chr(8211)}</td>" for c in (pod + [None] * 3)[:3])}<td>{drv(pole) if pole else "–"}</td><td>{drv(spr[0]) if spr else ""}</td></tr>')
        items.append({"@type": "ListItem", "position": r["rd"], "url": SITE + race_url(r["rd"]), "name": f'{gp_long(r)} {YEAR}: won by {r.get("win") or "?"}'})
    last = RACES[done - 1]
    body = f"""<h1>F1 results {YEAR}</h1>
<p class="sub">Every Grand Prix of the {YEAR} season so far: winner, podium, pole position and sprint winner.</p>
<p class="lead">After {done} rounds, the latest race was the {e(gp_long(last))}, won by {drv(last["win"])}. Tap a race for full results from every session and a lap-by-lap replay.</p>
<div class="tbl"><table><thead><tr><th>Rd</th><th>Grand Prix</th><th>Winner</th><th>2nd</th><th>3rd</th><th>Pole</th><th>Sprint winner</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="note" style="margin-top:12px">See also the <a href="/formula-1-standings-{YEAR}/">{YEAR} standings</a> and the <a href="/next-f1-race/">next race</a>.</p>"""
    return [page(f"/f1-results-{YEAR}/", f"F1 results {YEAR}: every Grand Prix winner, podium and pole | {BRAND}",
                 f"Formula 1 {YEAR} results: winners, podiums, pole positions and sprint winners for all {done} races so far, latest the {gp_long(last)}.",
                 body, [(f"{YEAR} results", f"/f1-results-{YEAR}/")], {"@context": "https://schema.org", "@type": "ItemList", "name": f"F1 {YEAR} race results", "itemListElement": items}, og="results")]


def build_stats(A, RACES, done, gp_long, race_url, drv, team_link, sess, sdata):
    """Season stats leaderboard: wins, podiums, poles, fastest laps, sprint wins, retirements, points."""
    D = A["DRIVERS"]; teams = {d["code"]: d["team"] for d in D}
    S = {d["code"]: {"pts": d["pts"], "w": 0, "pod": 0, "pole": 0, "fl": 0, "spr": 0, "dnf": 0, "st": 0, "best": None} for d in D}
    T = {}
    def add(code, k):
        if code not in S: return
        S[code][k] += 1
        tt = T.setdefault(teams[code], {"w": 0, "pod": 0, "pole": 0, "fl": 0}); tt[k] += 1
    for r in RACES[:done]:
        have = sess.get(r["rd"], {})
        if have.get("Race"):
            d = sdata(have["Race"]); dm = {x["n"]: x["c"] for x in d["drivers"]}
            for row in d["result"]:
                c = dm.get(row[1])
                if c not in S: continue
                ok = row[0] and not row[4]  # classified finisher
                if row[4] != "DNS": S[c]["st"] += 1
                if row[4] == "DNF": S[c]["dnf"] += 1
                if ok and (S[c]["best"] is None or row[0] < S[c]["best"]): S[c]["best"] = row[0]
                if ok and row[0] == 1: add(c, "w")
                if ok and row[0] <= 3: add(c, "pod")
        if have.get("Qualifying"):
            d = sdata(have["Qualifying"]); dm = {x["n"]: x["c"] for x in d["drivers"]}
            if d["result"]: add(dm.get(d["result"][0][1]), "pole")
        if r.get("flBy"): add(r["flBy"], "fl")
    for v in A["SPRINT_WIN"].values():
        if v[0] in S: S[v[0]]["spr"] += 1
    order = sorted(S, key=lambda c: (-S[c]["pts"], -S[c]["w"], -S[c]["pod"]))
    lead = lambda k: max(order, key=lambda c: (S[c][k], S[c]["pts"]))
    mw, mp, mpo, mfl = lead("w"), lead("pod"), lead("pole"), lead("fl")
    winners = sorted({c for c in S if S[c]["w"]}, key=lambda c: -S[c]["w"])
    rows = "".join(f'<tr><td class="pos">{i + 1}</td><td>{drv(c)}</td><td>{team_link(teams[c])}</td><td class="n">{S[c]["pts"]}</td><td class="n">{S[c]["w"]}</td><td class="n">{S[c]["pod"]}</td><td class="n">{S[c]["pole"]}</td><td class="n">{S[c]["fl"]}</td><td class="n">{S[c]["spr"]}</td><td class="n">{S[c]["best"] or "–"}</td><td class="n">{S[c]["dnf"]}</td></tr>' for i, c in enumerate(order))
    trows = "".join(f'<tr><td>{team_link(t)}</td><td class="n">{pts}</td><td class="n">{T.get(t, {}).get("w", 0)}</td><td class="n">{T.get(t, {}).get("pod", 0)}</td><td class="n">{T.get(t, {}).get("pole", 0)}</td><td class="n">{T.get(t, {}).get("fl", 0)}</td></tr>' for t, pts in A["CONSTRUCTORS"])
    nm = lambda c: f'{D[[x["code"] for x in D].index(c)]["first"]} {D[[x["code"] for x in D].index(c)]["last"]}'
    last = RACES[done - 1]
    body = f"""<h1>F1 stats {YEAR}</h1>
<p class="sub">Every driver and team of the {YEAR} season by the numbers: wins, podiums, poles, fastest laps, sprint wins and retirements.</p>
<p class="lead">After {done} of {A["TOTAL"]} rounds (latest: the {e(gp_long(last))}), {drv(mw)} leads the way with <b>{S[mw]["w"]} wins</b>. {len(winners)} different drivers have won a Grand Prix this year, and {drv(mpo)} has the most pole positions with {S[mpo]["pole"]}.</p>
<div class="tiles"><div class="tile"><span>Most wins</span><b>{S[mw]["w"]}</b><small>{e(nm(mw))}</small></div><div class="tile"><span>Most podiums</span><b>{S[mp]["pod"]}</b><small>{e(nm(mp))}</small></div><div class="tile"><span>Most poles</span><b>{S[mpo]["pole"]}</b><small>{e(nm(mpo))}</small></div><div class="tile"><span>Most fastest laps</span><b>{S[mfl]["fl"]}</b><small>{e(nm(mfl))}</small></div><div class="tile"><span>Different winners</span><b>{len(winners)}</b><small>{done} races</small></div></div>
<h2>Driver stats</h2>
<div class="tbl"><table><thead><tr><th>#</th><th>Driver</th><th>Team</th><th>Pts</th><th>Wins</th><th>Podiums</th><th>Poles</th><th>Fastest laps</th><th>Sprint wins</th><th>Best finish</th><th>DNFs</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Team stats</h2>
<div class="tbl"><table><thead><tr><th>Team</th><th>Pts</th><th>Wins</th><th>Podiums</th><th>Poles</th><th>Fastest laps</th></tr></thead><tbody>{trows}</tbody></table></div>
<h2>More F1 numbers</h2>
<p>How fast do they go? See <a href="/how-fast-is-an-f1-car/">top speeds at every track</a>. Want the race by race story? See every <a href="/f1-results-{YEAR}/">{YEAR} result</a>, the <a href="/formula-1-standings-{YEAR}/">championship standings</a>, or relive any race lap by lap in the <a href="/#replay">race replay</a>.</p>
<p class="note">Stats are calculated from official timing data via OpenF1 and update automatically after every session. Fastest laps are the quickest race lap of each Grand Prix.</p>"""
    faq = {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f"Who has the most F1 wins in {YEAR}?", "acceptedAnswer": {"@type": "Answer", "text": f"{nm(mw)}, with {S[mw]['w']} wins after {done} rounds."}},
        {"@type": "Question", "name": f"Who has the most pole positions in {YEAR}?", "acceptedAnswer": {"@type": "Answer", "text": f"{nm(mpo)}, with {S[mpo]['pole']} poles after {done} rounds."}},
        {"@type": "Question", "name": f"How many different drivers have won an F1 race in {YEAR}?", "acceptedAnswer": {"@type": "Answer", "text": f"{len(winners)}: " + ", ".join(f"{nm(c)} ({S[c]['w']})" for c in winners) + "."}}]}
    return [page(f"/f1-stats-{YEAR}/", f"F1 stats {YEAR}: wins, podiums, poles & fastest laps | {BRAND}",
                 f"Formula 1 {YEAR} stats for every driver and team: wins, podiums, pole positions, fastest laps, sprint wins and DNFs after {done} rounds. {nm(mw)} leads with {S[mw]['w']} wins.",
                 body, [(f"{YEAR} stats", f"/f1-stats-{YEAR}/")], faq, og="stats")]


def build_speed(A):
    TI = A.get("TRACK_INFO") or {}
    rows = []
    for sl, I in TI.items():
        fp = os.path.join(ROOT, "data", "tracks", f"{sl}.json")
        if not os.path.exists(fp): continue
        d = json.load(open(fp)); st = d["stats"]
        rows.append((sl, I, st, round(d["length"] / d["lapTime"] * 3.6), d["source"]))
    if not rows: return []
    rows.sort(key=lambda x: -x[2]["vmax"])
    fastest, slowest_top = rows[0], rows[-1]
    by_avg = sorted(rows, key=lambda x: -x[3])
    slow_corner = min(rows, key=lambda x: x[2]["vmin"])
    table = "".join(f'<tr><td><a href="/circuits/{sl}/">{e(I["full"])}</a></td><td class="n">{st["vmax"]} km/h</td><td class="n">{avg} km/h</td><td class="n">{st["vmin"]} km/h</td><td class="n">{st["fullThrottle"]}%</td><td>{e(src["driver"])} {src["year"]}</td></tr>' for sl, I, st, avg, src in rows)
    body = f"""<h1>How fast is an F1 car?</h1>
<p class="sub">Top speeds, average speeds and the slowest corners at every 2026 circuit, from real pole-lap telemetry.</p>
<p class="lead">On the {len(rows)} pole laps of the 2026 calendar, the highest top speed was <b>{fastest[2]["vmax"]} km/h</b> at {e(fastest[1]["full"])}, where the thin air at altitude means less drag. The fastest lap overall was at {e(by_avg[0][1]["full"])}, averaging <b>{by_avg[0][3]} km/h</b>, and the slowest corner was {e(slow_corner[1]["full"])}'s, taken at just <b>{slow_corner[2]["vmin"]} km/h</b>.</p>
<div class="tiles"><div class="tile"><span>Top speed</span><b>{fastest[2]["vmax"]} km/h</b></div><div class="tile"><span>Power</span><b>~1,000 hp</b></div><div class="tile"><span>Weight</span><b>768 kg</b></div><div class="tile"><span>Braking</span><b>5 g+</b></div></div>
<h2>Why F1 cars are so fast</h2><ul>
<li><b>Power:</b> about 1,000 hp from a 1.6-litre V6 turbo and an electric motor, in a car weighing just 768 kg.</li>
<li><b>Downforce:</b> the wings and floor press the car onto the track, so it can take corners at speeds no road car could.</li>
<li><b>Braking:</b> carbon brakes at around 1,000°C slow the car with more than 5 g.</li>
<li><b>2026 active aero:</b> on the straights the wings flatten to cut drag and raise top speed.</li></ul>
<h2>Every 2026 circuit, by top speed</h2>
<div class="tbl"><table><thead><tr><th>Circuit</th><th class="n">Top speed</th><th class="n">Average</th><th class="n">Slowest corner</th><th class="n">Full throttle</th><th>Pole lap</th></tr></thead><tbody>{table}</tbody></table></div>
<p class="note" style="margin-top:10px">From OpenF1 telemetry of each weekend's pole lap (2025 for the circuits not yet raced in 2026; Las Vegas 2025 was wet). <a href="/#tracks">Ride along in 3D</a>.</p>"""
    qa = [("How fast is an F1 car?", f"F1 cars reach around 350 km/h. On 2026 pole laps the highest top speed was {fastest[2]['vmax']} km/h at {fastest[1]['full']}."),
          ("What is the fastest F1 track?", f"By average speed over a lap, {by_avg[0][1]['full']}: {by_avg[0][3]} km/h on the pole lap. {by_avg[1][1]['full']} was next at {by_avg[1][3]} km/h."),
          ("What is the slowest corner in F1?", f"{slow_corner[1]['full']}'s, taken at {slow_corner[2]['vmin']} km/h on the pole lap."),
          ("How much horsepower does a 2026 F1 car have?", "About 1,000 hp: roughly 400 kW from the engine and up to 350 kW from the electric motor.")]
    return [page("/how-fast-is-an-f1-car/", f"How fast is an F1 car? Top speeds at every 2026 track | {BRAND}",
                 f"How fast F1 cars really go: up to {fastest[2]['vmax']} km/h, with top speed, average speed and slowest corner for every 2026 circuit from real pole-lap telemetry.",
                 body + qa_html(qa), [("How fast is an F1 car?", "/how-fast-is-an-f1-car/")], article_ld(SITE + "/how-fast-is-an-f1-car/", "How fast is an F1 car?", "Top speeds at every 2026 track."),
                 ld_list=[faq_ld(qa)], og="speed")]


def write_json(rel, obj):
    p = os.path.join(ROOT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, indent=1)
    if not os.path.exists(p) or open(p).read() != txt: open(p, "w").write(txt)


def write_api(A, D, C, RACES, wins, race_url, gp_long, dslug, tslug, done, total, champ_now):
    """Small, stable JSON files any site or AI agent can read (CORS is open, see _headers)."""
    meta = {"source": SITE, "licence": "Free to use with a link to pitwallf1.in. Unofficial; not associated with Formula 1.",
            "season": YEAR, "afterRound": done, "rounds": total}
    write_json("api/standings.json", {**meta, "champion": f"{D[0]['first']} {D[0]['last']}" if champ_now else None,
        "drivers": [{"position": i + 1, "code": d["code"], "name": f"{d['first']} {d['last']}", "number": d["no"], "team": d["team"],
                     "points": d["pts"], "wins": wins.get(d["code"], 0), "url": f"{SITE}/drivers/{dslug[d['code']]}/"} for i, d in enumerate(D)],
        "constructors": [{"position": i + 1, "team": t, "points": p, "url": f"{SITE}/teams/{tslug[t]}/"} for i, (t, p) in enumerate(C)]})
    write_json("api/calendar.json", {**meta, "races": [{"round": r["rd"], "name": gp_long(r), "circuit": r["circuit"], "location": r["place"],
        "dates": r["dates"], "raceStart": r["race"], "sprint": r["sprint"], "winner": r.get("win"), "winnerTeam": r.get("winTeam"),
        "raceTime": r.get("time"), "url": SITE + race_url(r["rd"])} for r in RACES]})
    TI = A.get("TRACK_INFO") or {}
    circ = []
    for sl, I in sorted(TI.items(), key=lambda kv: kv[1]["rd"]):
        fp = os.path.join(ROOT, "data", "tracks", f"{sl}.json")
        if not os.path.exists(fp): continue
        d = json.load(open(fp)); L = A["LAP_RECORD"].get(str(I["rd"]))
        circ.append({"slug": sl, "name": I["full"], "city": I["city"], "round": I["rd"], "lengthKm": I["length"], "corners": I["turns"],
                     "firstF1Race": I["firstGP"], "lapRecord": {"time": L[0], "driver": L[1], "team": L[2], "year": L[3]} if L else None,
                     "poleLap": {"driver": d["source"]["driverName"], "year": d["source"]["year"], "time": fmt_lap(d["lapTime"]), **d["stats"]},
                     "trackData": f"{SITE}/data/tracks/{sl}.json", "url": f"{SITE}/circuits/{sl}/"})
    write_json("api/circuits.json", {**meta, "circuits": circ})
    write_json("api/index.json", {**meta, "endpoints": {
        "standings": f"{SITE}/api/standings.json", "calendar": f"{SITE}/api/calendar.json", "circuits": f"{SITE}/api/circuits.json",
        "trackData": f"{SITE}/data/tracks/{{slug}}.json", "sessionIndex": f"{SITE}/data/index.json", "session": f"{SITE}/data/{{sessionKey}}.json"},
        "docs": f"{SITE}/llms.txt"})


def write_llms(A, D, C, RACES, done, total, champ_now, gp_long, race_url):
    nxt = next((r for r in RACES if r["rd"] == done + 1), None)
    last = RACES[done - 1]
    TI = A.get("TRACK_INFO") or {}
    txt = f"""# Pit Wall F1

> Pit Wall F1 (pitwallf1.in) is an unofficial Formula 1 fan hub for the {YEAR} season: championship standings, every race result, lap-by-lap replays with team radio, an interactive 3D model of every circuit built from real pole-lap telemetry, the calendar with lap records, race travel planning, and F1 games. Data comes from OpenF1 and updates automatically after every session.

Current state (after round {done} of {total}, the {gp_long(last)}):
- {"World champion" if champ_now else "Championship leader"}: {D[0]['first']} {D[0]['last']} ({D[0]['team']}), {D[0]['pts']} points; P2 {D[1]['first']} {D[1]['last']} {D[1]['pts']}; P3 {D[2]['first']} {D[2]['last']} {D[2]['pts']}.
- Constructors: {C[0][0]} {C[0][1]}, {C[1][0]} {C[1][1]}, {C[2][0]} {C[2][1]}.
- Last race: {gp_long(last)}, won by {next((f"{d['first']} {d['last']}" for d in D if d['code'] == last.get('win')), last.get('win') or 'n/a')}.
{f"- Next race: {gp_long(nxt)} at {nxt['circuit']}, {nxt['dates']} (race start {nxt['race']})." if nxt else "- The season is complete."}

## Pages
- [{YEAR} standings]({SITE}/formula-1-standings-{YEAR}/): drivers' and constructors' championship tables
- [{YEAR} calendar]({SITE}/f1-calendar-{YEAR}/): every round with dates, circuits and winners
- [Drivers]({SITE}/drivers/) and [Teams]({SITE}/teams/): one page each, with race-by-race results
- [Circuits]({SITE}/circuits/): every {YEAR} track with length, corners, lap record, pole lap telemetry and facts
- [World champions]({SITE}/formula-1-world-champions/): every champion since 1950
- [Next F1 race]({SITE}/next-f1-race/): date, start time and full weekend schedule of the next Grand Prix
- [{YEAR} results]({SITE}/f1-results-{YEAR}/): winner, podium, pole and sprint winner of every race so far
- [{YEAR} F1 stats]({SITE}/f1-stats-{YEAR}/): wins, podiums, poles, fastest laps, sprint wins and DNFs for every driver and team
- [How fast is an F1 car?]({SITE}/how-fast-is-an-f1-car/): top speed, average speed and slowest corner at every circuit, from pole-lap telemetry
- [Learn F1]({SITE}/learn-f1/): beginner's guide to track terms, tyres, the steering wheel and 2026 car tech (active aero, overtake mode, ERS)
- [F1 reaction test]({SITE}/f1-reaction-test/): the five-light start, playable in the browser
- [F1 qualifying game]({SITE}/f1-qualifying-game/): three-lap qualifying against the {YEAR} grid
- Race pages: {SITE}/races/<grand-prix>-{YEAR}/ (for example {SITE}{race_url(last['rd'])})

## Learn F1 topics
""" + "".join(f"- [{t[3]}]({SITE}/learn-f1/{t[0]}/)\n" for t in LEARN_TOPICS) + f"""
## Circuits
""" + "".join(f"- [{I['full']}]({SITE}/circuits/{sl}/): {I['city']}, round {I['rd']}\n" for sl, I in sorted(TI.items(), key=lambda kv: kv[1]["rd"])) + f"""
## Data (JSON, CORS enabled, free to use with a link back)
- {SITE}/api/index.json: list of endpoints
- {SITE}/api/standings.json: drivers' and constructors' standings
- {SITE}/api/calendar.json: all rounds, start times and winners
- {SITE}/api/circuits.json: circuit facts and pole-lap stats
- {SITE}/data/tracks/<slug>.json: circuit outline, height and pole-lap telemetry every 5 m (columns x, y, z in metres, t in seconds, speed km/h, gear, throttle %, brake)
- {SITE}/data/index.json and {SITE}/data/<sessionKey>.json: every session with results, laps, positions and race control

## Notes
- Unofficial and not associated with the Formula 1 companies. F1 and related marks belong to Formula One Licensing B.V.
- Contact: kmanish1996@gmail.com · Instagram: https://www.instagram.com/pitwall_f1_/
"""
    p = os.path.join(ROOT, "llms.txt")
    if not os.path.exists(p) or open(p).read() != txt: open(p, "w").write(txt)


def write_robots():
    txt = f"""# Pit Wall F1 welcomes search engines and AI assistants.
User-agent: *
Allow: /

# AI search and assistant crawlers are welcome too
User-agent: GPTBot
User-agent: OAI-SearchBot
User-agent: ChatGPT-User
User-agent: ClaudeBot
User-agent: Claude-SearchBot
User-agent: Claude-User
User-agent: PerplexityBot
User-agent: Perplexity-User
User-agent: Google-Extended
User-agent: Applebot-Extended
User-agent: Bingbot
User-agent: DuckAssistBot
User-agent: Amazonbot
User-agent: meta-externalagent
User-agent: CCBot
Allow: /

Sitemap: {SITE}/sitemap.xml
"""
    open(os.path.join(ROOT, "robots.txt"), "w").write(txt)


if __name__ == "__main__":
    main()
