# Pit Wall

An unofficial Formula 1 fan hub for the 2026 season. It's a single static page, with no build step and no backend.

- **Standings:** drivers' and constructors' championships, driver season cards and title-fight maths
- **Race centre:** every 2026 race and sprint replayed lap by lap, with a timing tower, track map, sector times, tyres, race control messages and team radio
- **Season replay:** animated points race and points-progression chart
- **Calendar:** every round with sprint and race winners, lap records, flags and countdowns in your time zone
- **Race travel:** circuit ticket prices (compiled by GP Destinations) in 11 currencies, a trip cost planner and first-timer tips
- **Legal pages:** Privacy, Terms, Contact, About (no ads, no affiliate links)

## Run locally

The replays load JSON and audio with `fetch`, so serve the folder over http instead of opening the file directly:

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Deploy

Upload the repo root (`index.html`, `data/`) to any static host: GitHub Pages, Netlify, Vercel or Cloudflare Pages.

## Before going live

Open `index.html`, search for `SITE SETTINGS` and fill in your name, domain and city. Unfilled values show as yellow placeholders on the legal pages.

- `radioPlayer`: team radio is never hosted here. With `true`, clips play in the page but stream straight from Formula 1's own servers. With `false`, each clip opens on F1's site instead. If F1's server refuses a clip, the page falls back to links automatically.

## Data pipeline

Replay data comes from the free [OpenF1 API](https://openf1.org). Every practice, qualifying, sprint and race session is added automatically:

- `.github/workflows/update-sessions.yml` runs every 10 minutes from Friday to Monday (UTC), and on demand from the Actions tab.
- It runs `scripts/update_sessions.py`, which finds 2026 sessions that ended at least 20 minutes ago and aren't in `data/index.json`, packs each into `data/<session_key>.json`, and commits the result. Your host redeploys from that commit.
- While a session is live, OpenF1 limits free access, so the script just exits and tries again on the next run. If OpenF1's lap data is incomplete, it waits up to 12 hours for the gaps to be filled.

To run it yourself (Python 3, no extra packages):

```bash
python3 scripts/update_sessions.py               # add every finished session that's missing
python3 scripts/update_sessions.py --only 11404  # add specific session keys
```

## Search pages

`scripts/build_pages.py` generates plain HTML pages that search engines can read: `/formula-1-standings-2026/`, `/f1-calendar-2026/`, `/drivers/<name>/`, `/teams/<name>/` and `/races/<grand-prix>-2026/`, plus `sitemap.xml`. The workflow reruns it whenever a new session arrives. After editing the standings or calendar in `index.html`, run it yourself:

```bash
python3 scripts/build_pages.py   # needs Node.js to read the data in index.html
```

## Standings

`scripts/update_standings.py` recalculates the championship from the race and sprint results in `data/` (points per round, driver and constructor totals, race and sprint winners, race times and fastest laps) and writes them into `index.html`. The workflow runs it after each new session, so standings, the calendar's winners and the title maths update automatically. The world champions list (`CHAMPIONS` in `index.html`) is edited by hand once a title is decided.

## Disclaimer

This website is unofficial and is not associated in any way with the Formula 1 companies. F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX and related marks are trade marks of Formula One Licensing B.V.
