"""Crawlable replay pages: /races/<gp>-2026/replay/ and /races/<gp>-2026/sprint-replay/.

Each page tells the story of the race in words (who led, lead changes, safety cars, pit stops,
fastest lap, biggest movers) and draws a lap-by-lap position chart and a tyre strategy chart,
all worked out from the same session data the in-app replay uses. A button opens the full replay
(timing tower, track map, race control, team radio) in the app.
"""
import collections
import html

e = html.escape
TYRE = {"S": ("#E10600", "Soft"), "M": ("#FFC93C", "Medium"), "H": ("#E8E8E8", "Hard"), "I": ("#2FD480", "Intermediate"), "W": ("#3C8DFF", "Wet"), "U": ("#8C94A6", "Unknown")}


def race_stats(d):
    """Lap-by-lap order, laps led, lead changes, pit stops, tyre stints, neutralisations, grid positions."""
    done = {}
    classified = {r[1]: r[2] for r in d["result"] if isinstance(r[2], int)}
    for n, rows in d["laps"].items():
        for r in rows:
            if r[1] is None or r[2] is None:
                continue
            if r[0] > classified.get(int(n), 10 ** 6):
                continue  # estimated laps after a car stopped
            done.setdefault(r[0], {})[int(n)] = r[1] + r[2]
    total = max(done) if done else 0
    order = [sorted(done.get(L, {}), key=lambda n, m=done.get(L, {}): m[n]) for L in range(1, total + 1)]
    leaders = [o[0] for o in order if o]
    lead_lap_end = [done[L][leaders[L - 1]] for L in range(1, len(leaders) + 1)]

    def lap_at(t):
        for i, x in enumerate(lead_lap_end):
            if x >= t:
                return i + 1
        return total

    reds = sorted({r[1] for r in d.get("rc", []) if str(r[4]).startswith("RED FLAG")})
    grid = {}
    for t, n, p in d["pos"]:
        if t <= 0:
            grid[n] = p
    stops = collections.Counter()
    for row in d["pits"]:
        t, n, lap, lane = (list(row) + [None] * 4)[:4]
        # pit-lane visits during the race; very long ones are cars parked in the pit lane under a red flag
        # (and visits on a red-flag lap: tyre changes in the suspended pit lane are not pit stops)
        if t is None or t <= 0 or not lap or (lane is not None and lane > 90) or lap in reds:
            continue
        stops[n] += 1
    stints = {}
    for n, rows in d["stints"].items():
        out = []
        for a, b, c, *_ in rows:
            if out and out[-1][2] == c and out[-1][1] + 1 >= a:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b, c])
        stints[int(n)] = out
    neutral = [(k, lap_at(a), lap_at(b)) for k, a, b in d.get("status", [])]
    top = {}
    for n, rows in d["laps"].items():
        sp = [r[6] for r in rows if len(r) > 6 and isinstance(r[6], (int, float))]
        if sp:
            top[int(n)] = max(sp)
    return dict(order=order, total=total, leaders=leaders, led=collections.Counter(leaders),
                changes=sum(1 for a, b in zip(leaders, leaders[1:]) if a != b), grid=grid, stops=stops,
                stints=stints, neutral=neutral, reds=reds, top=top)


def position_chart(d, S, label):
    """SVG: every driver's position at the end of each lap, in team colours."""
    drivers = {x["n"]: x for x in d["drivers"]}
    n_laps, n_cars = S["total"], max(len(d["drivers"]), 1)
    W, H, L, R, T, B = 900, 26 + n_cars * 20, 58, 52, 14, 26
    x = lambda lap: L + (lap - 1) / max(1, n_laps - 1) * (W - L - R)
    y = lambda p: T + (p - 1) * (H - T - B) / max(1, n_cars - 1)
    lines, labels = [], []
    finish = {r[1]: r for r in d["result"]}
    for n, dr in drivers.items():
        pts = [(lap, o.index(n) + 1) for lap, o in enumerate(S["order"], 1) if n in o]
        g = S["grid"].get(n)
        if g:
            pts = [(0, g)] + pts
        if len(pts) < 2:
            continue
        xs = lambda lap: L - 14 if lap == 0 else x(lap)
        path = " ".join(f"{xs(a):.1f},{y(b):.1f}" for a, b in pts)
        out = finish.get(n, [None] * 5)[4]
        lines.append(f'<polyline points="{path}" fill="none" stroke="{dr["col"]}" stroke-width="2" stroke-linejoin="round" opacity=".9"><title>{e(dr["f"])} {e(dr["l"])}</title></polyline>')
        lx, ly = xs(pts[-1][0]), y(pts[-1][1])
        labels.append(f'<text x="{lx + 6:.1f}" y="{ly + 4:.1f}" fill="{dr["col"]}" font-size="11" font-weight="700">{e(dr["c"])}{" ✕" if out else ""}</text>')
    grid_lines = "".join(f'<line x1="{L - 14}" x2="{W - R}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="currentColor" opacity=".08"/><text x="{L - 22}" y="{y(p) + 4:.1f}" font-size="10" text-anchor="end" fill="currentColor" opacity=".55">P{p}</text>' for p in range(1, n_cars + 1))
    step = 10 if n_laps > 40 else 5
    ticks = "".join(f'<text x="{x(l):.1f}" y="{H - 6}" font-size="10" text-anchor="middle" fill="currentColor" opacity=".55">{l}</text>' for l in range(step, n_laps + 1, step))
    shade = "".join(f'<rect x="{x(max(1, a)):.1f}" y="{T - 8}" width="{max(3, x(max(a, b)) - x(max(1, a))):.1f}" height="{H - T - B + 16}" fill="{"#FFC93C" if k == "SC" else "#FFC93C"}" opacity="{".16" if k == "SC" else ".08"}"><title>{"Safety car" if k == "SC" else "Virtual safety car"}, laps {a}–{b}</title></rect>' for k, a, b in S["neutral"])
    reds = "".join(f'<line x1="{x(l):.1f}" x2="{x(l):.1f}" y1="{T - 8}" y2="{H - B + 8}" stroke="#E10600" stroke-width="2" stroke-dasharray="4 3"><title>Red flag, lap {l}</title></line>' for l in S["reds"])
    return (f'<figure class="chart"><svg viewBox="0 0 {W} {H}" role="img" aria-label="{e(label)}" style="width:100%;height:auto;color:var(--fg)">'
            f'{shade}{reds}{grid_lines}{ticks}{"".join(lines)}{"".join(labels)}</svg>'
            f'<figcaption>Position at the end of every lap, from the starting grid on the left. Yellow bands are safety car (darker) and virtual safety car periods{", the red dashed line is the red flag" if S["reds"] else ""}. ✕ = did not finish.</figcaption></figure>')


def tyre_chart(d, S):
    """SVG: each driver's tyre stints, in finishing order."""
    drivers = {x["n"]: x for x in d["drivers"]}
    rows = [r for r in d["result"] if r[1] in drivers and S["stints"].get(r[1])]
    n_laps = S["total"] or 1
    W, L, R, rh = 900, 52, 10, 18
    H = 20 + len(rows) * rh + 10
    x = lambda lap: L + (lap - 1) / n_laps * (W - L - R)
    out = []
    for i, r in enumerate(rows):
        n, yy = r[1], 14 + i * rh
        out.append(f'<text x="{L - 8}" y="{yy + 12}" font-size="11" text-anchor="end" fill="currentColor" font-weight="700">{e(drivers[n]["c"])}</text>')
        for a, b, c in S["stints"][n]:
            col, nm = TYRE.get(c, ("#888", c))
            out.append(f'<rect x="{x(a):.1f}" y="{yy}" width="{max(2, x(b + 1) - x(a) - 1.5):.1f}" height="{rh - 5}" rx="3" fill="{col}"><title>{e(drivers[n]["c"])}: {nm}, laps {a}–{b}</title></rect>')
    used = sorted({c for v in S["stints"].values() for _, _, c in v}, key=lambda c: "SMHIW".find(c))
    key = " ".join(f'<span><i style="background:{TYRE.get(c, ("#888", c))[0]}"></i>{TYRE.get(c, ("#888", c))[1]}</span>' for c in used)
    return (f'<figure class="chart"><svg viewBox="0 0 {W} {H}" role="img" aria-label="Tyre strategy for every driver" style="width:100%;height:auto;color:var(--fg)">{"".join(out)}</svg>'
            f'<figcaption class="tyre-key">{key}</figcaption></figure>')


def story(d, S, kind, gp, year, fl, name_of, link_of):
    """The race in words, built only from the data."""
    num = {x["n"]: x for x in d["drivers"]}
    code = lambda n: num[n]["c"]
    who = lambda n: link_of(code(n)) if code(n) else e(n)
    res = d["result"]
    win, second, third = (res[i][1] for i in range(3))
    pole = next((n for n, p in S["grid"].items() if p == 1), None)
    paras = []
    p1 = f'{who(win)} won the {year} {e(gp)}{" sprint" if kind == "Sprint" else ""}'
    if pole and pole == win:
        p1 += " from pole position"
    elif win in S["grid"]:
        p1 += f' from P{S["grid"][win]} on the grid'
    gap = res[1][3]
    p1 += f', {gap:.3f}s ahead of {who(second)}' if isinstance(gap, (int, float)) and gap else f', ahead of {who(second)}'
    p1 += f', with {who(third)} completing the podium.'
    paras.append(p1)
    led = S["led"].most_common()
    if led:
        if S["changes"] == 0:
            paras.append(f'{who(led[0][0])} led every one of the {S["total"]} laps.')
        else:
            seq = []
            for n in S["leaders"]:
                if not seq or seq[-1] != n:
                    seq.append(n)
            parts = ", ".join(f'{who(n)} ({c} lap{"s" if c != 1 else ""})' for n, c in led)
            paras.append(f'The lead changed hands {S["changes"]} time{"s" if S["changes"] != 1 else ""}. Laps led: {parts}.')
    ev = []
    for k, a, b in S["neutral"]:
        ev.append(f'{"a safety car" if k == "SC" else "a virtual safety car"} on lap{"s" if b > a else ""} {a}{"–" + str(b) if b > a else ""}')
    for l in S["reds"]:
        ev.append(f"a red flag on lap {l}")
    if ev:
        paras.append("The race was neutralised by " + "; ".join(ev) + ".")
    elif kind != "Sprint":
        paras.append("There were no safety cars: the race ran green from start to finish.")
    if S["stops"]:
        winner_stops = S["stops"].get(win, 0)
        most = S["stops"].most_common(1)[0]
        avg = sum(S["stops"].get(r[1], 0) for r in res if not r[4]) / max(1, sum(1 for r in res if not r[4]))
        ws = " → ".join(TYRE.get(c, ("", c))[1] for _, _, c in S["stints"].get(win, []))
        txt = (f'{who(win)} made {winner_stops} pit stop{"s" if winner_stops != 1 else ""}' + (f" ({ws})" if ws else "")) if winner_stops else f'{who(win)} didn\'t stop' + (f" ({ws} tyres throughout)" if ws else "")
        txt += f'. Finishers averaged {avg:.1f} stop{"s" if round(avg, 1) != 1 else ""}'
        if most[1] > winner_stops:
            txt += f', while {who(most[0])} came in {most[1]} time{"s" if most[1] != 1 else ""}'
        paras.append(txt + ".")
    movers = sorted(((S["grid"][r[1]] - r[0], r[1]) for r in res if r[0] and not r[4] and r[1] in S["grid"]), reverse=True)
    if movers and movers[0][0] >= 3:
        g, n = movers[0]
        paras.append(f'Biggest climber: {who(n)}, from P{S["grid"][n]} on the grid to P{S["grid"][n] - g} at the flag (+{g}).')
    outs = [r for r in res if r[4] in ("DNF", "DNS")]
    if outs:
        paras.append(f'{len(outs)} driver{"s" if len(outs) != 1 else ""} didn\'t finish: ' + ", ".join(who(r[1]) for r in outs) + ".")
    if fl:
        paras.append(f'Fastest lap: {who(fl[1])} with a {fl[0]}.')
    if S["top"]:
        n, v = max(S["top"].items(), key=lambda kv: kv[1])
        paras.append(f'Top speed through the speed trap: {v} km/h by {who(n)}.')
    return paras


def fastest(d):
    """Quickest clean lap (sectors add up, not lap 1): (seconds, driver number)."""
    best = None
    for n, rows in d["laps"].items():
        for r in rows:
            if len(r) > 8 or r[0] < 2 or not r[2] or not (r[3] and r[4] and r[5]) or abs(r[3] + r[4] + r[5] - r[2]) > 0.05:
                continue
            if best is None or r[2] < best[0]:
                best = (r[2], int(n))
    return best


CSS = """<style>
.chart{margin:12px 0 22px;background:var(--panel);border:1px solid var(--line);border-radius:4px;padding:12px 10px 8px}
.chart figcaption{font-size:13px;color:var(--muted);margin-top:6px}
.tyre-key{display:flex;gap:14px;flex-wrap:wrap}.tyre-key i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.rp-cta{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:16px 0 8px}.rp-cta .btn{font-size:15px;padding:12px 18px}
.story p{max-width:72ch}
</style>"""
