// /api/alerts: turn race alerts on or off for one browser.
//   GET              -> { publicKey }  (the site's VAPID key, needed to subscribe)
//   POST {subscription, prefs: {race, quali, sprint, results}}  -> saves or updates the subscription
//   DELETE {endpoint} -> forgets it
// Subscriptions are stored in Netlify Blobs (private to the site). Nothing else about the visitor is kept.
import { getStore } from "@netlify/blobs";
import { getVapid, validSubscription, subKey, sendPush } from "../lib/webpush.mjs";

const KINDS = ["race", "quali", "sprint", "results"];
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

export default async (req) => {
  const store = getStore({ name: "alerts", consistency: "strong" });
  if (req.method === "GET") return json({ publicKey: (await getVapid(store)).publicKey });
  const text = await req.text();
  if (text.length > 4000) return json({ error: "too large" }, 413);
  let b;
  try { b = JSON.parse(text); } catch { return json({ error: "bad json" }, 400); }
  if (req.method === "POST") {
    const s = b.subscription;
    if (!s || !validSubscription(s)) return json({ error: "bad subscription" }, 400);
    const prefs = Object.fromEntries(KINDS.map((k) => [k, !!(b.prefs || {})[k]]));
    if (!KINDS.some((k) => prefs[k])) { await store.delete(subKey(s.endpoint)); return json({ ok: true, on: false }); }
    const key = subKey(s.endpoint), isNew = !(await store.get(key));
    const clean = { endpoint: s.endpoint, keys: { p256dh: s.keys.p256dh, auth: s.keys.auth } };
    await store.setJSON(key, { s: clean, prefs, t: Date.now() });
    // a confirmation on first sign-up, so the visitor (and we) know delivery works on this device
    let test = null;
    if (isNew) {
      try {
        test = await sendPush(clean, { title: "✅ Race alerts are on", body: "You'll get a notification here when the session starts. Turn them off any time from the 🔔 button.", url: "https://pitwallf1.in/", tag: "welcome" },
                              await getVapid(store), { ttl: 600, urgency: "normal" });
      } catch { test = 0; }
    }
    return json({ ok: true, on: true, prefs, test });
  }
  if (req.method === "DELETE") {
    if (typeof b.endpoint === "string") await store.delete(subKey(b.endpoint));
    return json({ ok: true, on: false });
  }
  return json({ error: "method not allowed" }, 405);
};

export const config = { path: "/api/alerts" };
