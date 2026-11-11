// Runs every 5 minutes. When a session someone asked about is starting (race, qualifying, sprint), or a
// new race result has been published, it sends one notification to every browser that opted in.
// Each alert is sent once: a "sent/<id>" marker is stored before sending.
import { getStore } from "@netlify/blobs";
import { getVapid, sendPush } from "../lib/webpush.mjs";

const SITE = "https://pitwallf1.in";
const KIND = { GP: "race", Q: "quali", S: "sprint", SQ: null };

export function dueAlerts(sessions, last, now) {
  const due = [];
  for (const s of sessions.sessions || []) {
    const kind = KIND[s.key];
    const t = Date.parse(s.start);
    if (!kind || !(now >= t - 5 * 60e3 && now <= t + 20 * 60e3)) continue;
    const what = kind === "race" ? "Lights out" : kind === "quali" ? "Qualifying is live" : "Sprint is live";
    due.push({ id: `${sessions.season}-r${s.round}-${s.key}`, kind, tag: `r${s.round}-${s.key}`,
      title: `🔴 ${what}: ${s.gp}`, body: kind === "race" ? `The ${s.gp} is starting now. Follow the timing, then get the full story here after the flag.` : `${s.name} at the ${s.gp} has started.`,
      url: `${SITE}/race-centre` });
  }
  if (last && last.round && last.podium && now - Date.parse(last.date) < 18 * 3600e3) {
    const p = last.podium;
    due.push({ id: `${sessions.season}-r${last.round}-results`, kind: "results", tag: `r${last.round}-results`,
      title: `🏁 ${p[0].name} wins the ${last.name}`, body: `P2 ${p[1] ? p[1].name : "–"} · P3 ${p[2] ? p[2].name : "–"}. How the race was won, lap by lap.`,
      url: SITE + ((last.links && (last.links.story || last.links.results)) || "/") });
  }
  return due;
}

export default async () => {
  const store = getStore({ name: "alerts", consistency: "strong" });
  const now = Date.now();
  const get = (p) => fetch(SITE + p, { headers: { "cache-control": "no-cache" } }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  const [sessions, last] = await Promise.all([get("/api/sessions.json"), get("/api/last-race.json")]);
  if (!sessions) return new Response("no schedule");
  const todo = [];
  for (const d of dueAlerts(sessions, last, now)) if (!(await store.get("sent/" + d.id))) todo.push(d);
  if (!todo.length) return new Response("nothing due");
  for (const d of todo) await store.set("sent/" + d.id, String(now));
  const keys = await getVapid(store);
  const { blobs } = await store.list({ prefix: "sub/" });
  let sent = 0, gone = 0, failed = 0;
  for (let i = 0; i < blobs.length; i += 25) {
    await Promise.all(blobs.slice(i, i + 25).map(async ({ key }) => {
      const rec = await store.get(key, { type: "json" });
      if (!rec) return;
      for (const d of todo) {
        if (!rec.prefs || !rec.prefs[d.kind]) continue;
        try {
          const st = await sendPush(rec.s, { title: d.title, body: d.body, url: d.url, tag: d.tag }, keys, { topic: d.tag, ttl: d.kind === "results" ? 6 * 3600 : 1800 });
          if (st === 404 || st === 410) { await store.delete(key); gone++; return; }
          st < 300 ? sent++ : failed++;
        } catch { failed++; }
      }
    }));
  }
  const msg = `alerts ${todo.map((d) => d.id).join(", ")}: sent ${sent}, removed ${gone}, failed ${failed}`;
  console.log(msg);
  return new Response(msg);
};

export const config = { schedule: "*/5 * * * *" };
