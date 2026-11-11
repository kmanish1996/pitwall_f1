/* Pit Wall F1 service worker: only shows race alerts the visitor turned on. It does not cache pages. */
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("push", (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data && e.data.text() }; }
  e.waitUntil(self.registration.showNotification(d.title || "Pit Wall F1", {
    body: d.body || "", tag: d.tag, renotify: !!d.tag, icon: "/assets/icon-192.png", badge: "/favicon-96.png",
    data: { url: d.url || "/" },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = new URL((e.notification.data && e.notification.data.url) || "/", self.location.origin).href;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((cs) => {
    for (const c of cs) if (c.url === url && "focus" in c) return c.focus();
    return self.clients.openWindow(url);
  }));
});

// the browser replaced the subscription: tell the server, keeping the visitor's choices
self.addEventListener("pushsubscriptionchange", (e) => {
  e.waitUntil((async () => {
    const reg = self.registration;
    const keyRes = await fetch("/api/alerts"); const { publicKey } = await keyRes.json();
    const pad = "=".repeat((4 - publicKey.length % 4) % 4);
    const raw = atob((publicKey + pad).replace(/-/g, "+").replace(/_/g, "/"));
    const sub = e.newSubscription || await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: Uint8Array.from(raw, (c) => c.charCodeAt(0)) });
    let prefs = { race: true, results: true };
    try { const c = await caches.open("pw-alerts"); const r = await c.match("/__prefs"); if (r) prefs = await r.json(); } catch (_) {}
    await fetch("/api/alerts", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ subscription: sub.toJSON(), prefs }) });
  })());
});
