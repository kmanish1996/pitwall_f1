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
    # Pit stops and tyre sets. The pit-lane log says when a car went through the pit lane; OpenF1's stints
    # say which tyres it ran. A visit after which the car is still on the same set (same compound, tyre
    # age carrying on) was a drive-through or the safety car leading the field through the pit lane, not
    # a stop. Very long visits are cars parked under a red flag, and tyres changed during a red flag are a
    # free change, not a stop. Stints that start after the driver's last classified lap are ignored.
    # If the two sources disagree (a stop with no new stint, or a new stint with no stop) the tyre
    # sequence is marked unreliable and only the stop count is used.
    visits, parked = collections.defaultdict(list), collections.defaultdict(set)
    for row in d["pits"]:
        t, n, lap, lane = (list(row) + [None] * 4)[:4]
        if t is None or t <= 0 or not lap:
            continue
        if (lane is not None and lane > 90) or lap in reds:
            parked[n].add(lap)
            continue
        visits[n].append(lap)
    stops, stints, sets, redchg, reliable, stoplaps = collections.Counter(), {}, {}, {}, {}, {}
    for n in set(visits) | {int(k) for k in d["stints"]}:
        last = min(classified.get(n, 10 ** 6), total)
        raw = sorted(r for r in d["stints"].get(str(n), []) if r[0] is not None and r[0] <= last)
        starts = {r[0]: i for i, r in enumerate(raw)}
        ok = bool(raw) and raw[0][0] <= 2
        cuts = []
        for lap in sorted(set(visits.get(n, []))):
            if lap >= last:
                continue
            i = starts.get(lap + 1, starts.get(lap))
            if i is not None and i > 0:
                pr, nx = raw[i - 1], raw[i]
                age_on = len(pr) > 3 and len(nx) > 3 and nx[3] == (pr[3] or 0) + (pr[1] or pr[0]) - pr[0] + 1
                if pr[2] == nx[2] and age_on:
                    continue  # same set: drive-through or pit-lane pass under the safety car
            elif raw:
                ok = False  # a stop the tyre data doesn't show
            cuts.append((lap, False))
        stops[n] = len(cuts); stoplaps[n] = [l for l, _ in cuts]
        for l in sorted(set(reds) | parked.get(n, set())):
            if l < last and l not in {c for c, _ in cuts} and any(starts.get(x) for x in (l, l + 1)):
                cuts.append((l, True))
        cut_laps = {l for l, _ in cuts}
        if any(r[0] > 1 and not ({r[0] - 1, r[0]} & cut_laps) and not (r[2] == raw[i - 1][2] and len(r) > 3 and r[3] == (raw[i - 1][3] or 0) + (raw[i - 1][1] or raw[i - 1][0]) - raw[i - 1][0] + 1)
               for i, r in enumerate(raw) if i):
            ok = False  # a new set the pit-lane log doesn't show

        def comp(lap):
            hit = [r[2] for r in raw if r[0] <= lap <= max(r[1] or last, r[0])]
            return hit[-1] if hit else "U"
        out, start, red = [], 1, False
        for lap, is_red in sorted(cuts) + [(last, None)]:
            if lap < start:
                continue
            out.append({"a": start, "b": lap, "c": comp(start if start == 1 else min(start + 1, lap)), "red": red})
            start, red = lap + 1, bool(is_red)
        stints[n] = [[x["a"], x["b"], x["c"], x["red"]] for x in out]
        sets[n] = out
        redchg[n] = [x["c"] for x in out[1:] if x["red"]]
        reliable[n] = ok and all(x["c"] in "SMHIW" for x in out)
    neutral = [(k, lap_at(a), lap_at(b)) for k, a, b in d.get("status", [])]
    top = {}
    for n, rows in d["laps"].items():
        sp = [r[6] for r in rows if len(r) > 6 and isinstance(r[6], (int, float))]
        if sp:
            top[int(n)] = max(sp)
    return dict(order=order, total=total, leaders=leaders, led=collections.Counter(leaders),
                changes=sum(1 for a, b in zip(leaders, leaders[1:]) if a != b), grid=grid, stops=stops,
                stints=stints, sets=sets, redchg=redchg, reliable=reliable, stoplaps=stoplaps, classified=classified, neutral=neutral, reds=reds, top=top)


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
        for a, b, c, red in S["stints"][n]:
            col, nm = TYRE.get(c, ("#888", c))
            out.append(f'<rect x="{x(a):.1f}" y="{yy}" width="{max(2, x(b + 1) - x(a) - 1.5):.1f}" height="{rh - 5}" rx="3" fill="{col}"><title>{e(drivers[n]["c"])}: {nm}, laps {a}–{b}{" (fitted under the red flag)" if red else ""}</title></rect>')
    used = sorted({v[2] for vs in S["stints"].values() for v in vs}, key=lambda c: "SMHIWU".find(c))
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
        ws = " → ".join(TYRE.get(x["c"], ("", x["c"]))[1] + (" under the red flag" if x["red"] else "") for x in S["sets"].get(win, [])) if S["reliable"].get(win) else ""
        txt = (f'{who(win)} made {winner_stops} pit stop{"s" if winner_stops != 1 else ""}' + (f" ({ws})" if ws else "")) if winner_stops else f'{who(win)} didn\'t stop' + (f" ({ws} tyres throughout)" if ws else "")
        txt += f'. Finishers averaged {avg:.1f} stop{"s" if round(avg, 1) != 1 else ""}' if round(avg, 1) else ". No finisher made a stop"
        if most[1] > winner_stops and round(avg, 1):
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


def why(d, S, link_of):
    """'Why it went this way': how the winner got the lead, undercuts and overcuts at the front,
    stops under the safety car, race pace on clean laps and the podium drivers' teammate battles.
    Every line is worked out from the lap, pit and position data; nothing is guessed."""
    num = {x["n"]: x for x in d["drivers"]}
    who = lambda n: link_of(num[n]["c"]) if n in num else e(str(n))
    res = [r for r in d["result"] if r[1] in num]
    if len(res) < 3 or not S["order"]:
        return []
    win, total, order = res[0][1], S["total"], S["order"]
    fin = {r[1]: r for r in res if r[0] and not r[4]}
    place = {r[1]: r[0] for r in res if r[0]}
    stoplaps = S["stoplaps"]
    neutral = set()
    for _, a, b in S["neutral"]:
        neutral |= set(range(a, b + 2))  # the lap after a restart is still bunched up
    for l in S["reds"]:
        neutral |= {l - 1, l, l + 1}

    def pos(n, lap):
        o = order[lap - 1] if 1 <= lap <= len(order) else []
        return o.index(n) + 1 if n in o else None
    laps_word = lambda k: f'{k} lap{"s" if k != 1 else ""}'
    out, explained = [], set()

    # 1. how the winner got the lead for good
    lead = S["leaders"]
    L = next((i + 1 for i in range(len(lead) - 1, 0, -1) if lead[i] == win and lead[i - 1] != win), None)
    if L is None and lead and lead[0] == win and S["changes"] == 0:
        pass  # led every lap: the story already says so
    elif L:
        prev = lead[L - 2]
        explained.add(frozenset((win, prev)))
        ws = [l for l in stoplaps.get(win, []) if L - 6 <= l <= L]
        ps = [l for l in stoplaps.get(prev, []) if L - 6 <= l <= L]
        later = [l for l in stoplaps.get(win, []) if l > L]
        sc = " under the safety car" if any(l in neutral for l in ps + ws) else ""
        if S["classified"].get(prev, total) <= L and prev not in fin:
            t = f"{who(win)} inherited the lead on lap {L} when {who(prev)} retired."
        elif ps and not ws:
            t = f"{who(win)} took the lead for good on lap {L}, when {who(prev)} pitted{sc}."
            if later:
                t += (f" {who(win)} stayed out until lap {later[0]}" + (" and stopped under the safety car" if later[0] in neutral else "")
                      + " without losing the lead.")
        elif ws and ps and min(ws) < min(ps):
            t = (f"{who(win)} won it in the pit stops{sc}: he came in on lap {min(ws)}, {who(prev)} waited until lap {min(ps)}, "
                 f"and came out ahead. The undercut worked.")
        elif ws and ps and min(ws) > min(ps):
            t = (f"{who(win)} won it in the pit stops{sc}: {who(prev)} came in first, on lap {min(ps)}, while {who(win)} stayed out until lap {min(ws)} "
                 f"and rejoined ahead. The overcut worked.")
        else:
            rs = " at a restart" if L in neutral or L - 1 in neutral else ""
            t = f"{who(win)} passed {who(prev)} on track for the lead on lap {L}{rs}, and led the rest of the way."
        out.append(("The decisive move", t))

    # 2. undercuts and overcuts among the top six
    top = [r[1] for r in res[:6] if r[1] in fin]
    seen = []
    for i, A in enumerate(top):
        for B in top[i + 1:]:
            if frozenset((A, B)) in explained:
                continue
            for a in stoplaps.get(A, []):
                for b in stoplaps.get(B, []):
                    first, second, l1, l2 = (A, B, a, b) if a < b else (B, A, b, a)
                    if not 1 <= l2 - l1 <= 5 or any(l in neutral for l in range(l1, l2 + 1)) or l1 < 2 or l2 + 1 > total:
                        continue
                    p1b, p2b, p1a, p2a = pos(first, l1 - 1), pos(second, l1 - 1), pos(first, l2 + 1), pos(second, l2 + 1)
                    if None in (p1b, p2b, p1a, p2a) or abs(p1b - p2b) > 2:
                        continue
                    if p1b > p2b and p1a < p2a:
                        seen.append((l1, f"{who(first)} undercut {who(second)}: in on lap {l1}, {laps_word(l2 - l1)} earlier, and out in front."))
                    elif p1b < p2b and p1a > p2a:
                        seen.append((l1, f"{who(second)} overcut {who(first)}: stayed out {laps_word(l2 - l1)} longer, until lap {l2}, and rejoined ahead."))
    for _, t in sorted(seen)[:3]:
        out.append(("Pit-stop battles", t))

    # 3. stops under the safety car (a pit stop costs far less time while the field is slowed)
    counted = set()
    for k, a, b in S["neutral"]:
        took = []
        for n in [r[1] for r in res[:10]]:
            l = next((l for l in stoplaps.get(n, []) if a <= l <= b + 1 and (n, l) not in counted), None)
            if l is not None:
                took.append(n); counted.add((n, l))
        if not took or a <= 1:
            continue
        name = "safety car" if k == "SC" else "virtual safety car"
        span = f"lap {a}" if a == b else f"laps {a}–{b}"
        names = [who(n) for n in took[:4]] + ([f"{len(took) - 4} more"] if len(took) > 4 else [])
        listed = ", ".join(names[:-1]) + " and " + names[-1] if len(names) > 1 else names[0]
        t = (f"Under the {name} on {span}, {len(took)} of the eventual top ten pitted: {listed}." if len(took) > 1
             else f"{listed} pitted under the {name} on {span}.")
        gain = max(((pos(n, a - 1) or 0) - place.get(n, 99), n) for n in took)
        if gain[0] >= 2:
            t += f" {who(gain[1])} gained most: P{pos(gain[1], a - 1)} before it, P{place[gain[1]]} at the flag."
        if win not in took:
            t += f" {who(win)} stayed out."
        out.append(("Safety car timing", t))

    # 4. race pace on clean laps
    def clean(n):
        stopset = set(stoplaps.get(n, []))
        ts = sorted(r[2] for r in d["laps"].get(str(n), [])
                    if r[0] > 1 and r[2] and not (len(r) > 8 and r[8]) and not r[7] and r[0] not in stopset and r[0] not in neutral
                    and r[0] <= S["classified"].get(n, total))
        if len(ts) < 8:
            return None
        ts = [t for t in ts if t <= ts[0] * 1.07]
        return ts[len(ts) // 2] if len(ts) >= 8 else None
    med = {n: clean(n) for n in [r[1] for r in res[:10]]}
    med = {n: v for n, v in med.items() if v}
    sec = res[1][1]
    if med.get(win) and med.get(sec):
        dlt = med[sec] - med[win]
        if abs(dlt) < 0.05:
            t = f"On clean laps (leaving out lap 1, pit stops and safety car laps), {who(win)} and {who(sec)} were evenly matched: their typical laps were within 0.05s."
        elif dlt > 0:
            t = f"On clean laps, {who(win)}'s typical lap was {dlt:.3f}s quicker than {who(sec)}'s."
        else:
            t = f"On clean laps {who(sec)} was actually {-dlt:.3f}s a lap quicker than {who(win)}, so track position won it."
        best = min(med, key=med.get)
        if best not in (win, sec):
            t += f" The best race pace in the top ten belonged to {who(best)}, who finished P{place.get(best)}."
        out.append(("Race pace", t))

    # 5. teammate battles for the podium
    tm = []
    for r in res[:3]:
        P = r[1]
        T = next((x["n"] for x in d["drivers"] if x["t"] == num[P]["t"] and x["n"] != P), None)
        if not T or frozenset((P, T)) in tm:
            continue
        tr = next((q for q in d["result"] if q[1] == T), None)
        if not tr:
            continue
        tres = f"P{tr[0]}" if tr[0] and not tr[4] else ("did not start" if tr[4] == "DNS" else "retired")
        g = ""
        gp, gt = S["grid"].get(P), S["grid"].get(T)
        if gp and gt:
            g = f" (started P{gp} vs P{gt})"
        tm.append(frozenset((P, T)))
        out.append(("Teammates", f"{who(P)} P{r[0]} vs {who(T)} {tres}{g}."))
    return out


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
.why{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--red,#E10600);border-radius:4px;padding:6px 18px}
.why b{color:var(--fg)}.why .note{font-size:13px;color:var(--muted)}
</style>"""
