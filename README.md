# Pit Wall F1

An unofficial Formula 1 fan hub for the 2026 season. It's a single static page, with no build step and no backend.

- **Standings:** drivers' and constructors' championships, driver season cards and title-fight maths
- **Race centre:** every 2026 race and sprint replayed lap by lap, with a timing tower, track map, sector times, tyres, race control messages and team radio
- **Season replay:** animated points race and points-progression chart
- **Calendar:** every round with sprint and race winners, lap records, flags and countdowns in your time zone
- **Race travel:** official ticket prices in 11 currencies, a trip cost planner and first-timer tips
- **Legal pages:** Privacy, Affiliate Disclosure, Terms, Contact, About

## Run locally

The replays load JSON and audio with `fetch`, so serve the folder over http instead of opening the file directly:

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Deploy

Upload the repo root (`index.html`, `data/`, `radio/`) to any static host: GitHub Pages, Netlify, Vercel or Cloudflare Pages.

## Before going live

Open `index.html`, search for `SITE SETTINGS` and fill in your name, domain and city. Unfilled values show as yellow placeholders on the legal pages.

- `hostRadio`: set to `false` to link team radio to F1's servers instead of serving `radio/*.mp3` yourself. The recordings belong to Formula 1, so re-hosting them publicly carries copyright risk.

## Data pipeline (`scripts/`)

Replay data comes from the [OpenF1 API](https://openf1.org). To add a new session (Python 3 and ffmpeg needed):

```bash
cd scripts
python3 fetch.py <session_key>       # laps, positions, stints, pits, race control, radio, weather, results
python3 fetchloc.py <session_key>    # one reference lap of car positions for the track map
python3 compact.py <session_key>     # writes site/data/<session_key>.json
python3 radio.py <session_key>       # joins radio clips into site/radio/<session_key>.mp3
```

Then copy the outputs into `data/` and `radio/`, add the session to `data/index.json`, and add the round to `REPLAY` in `index.html`.

## Disclaimer

This website is unofficial and is not associated in any way with the Formula 1 companies. F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX and related marks are trade marks of Formula One Licensing B.V.
