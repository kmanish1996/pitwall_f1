/* Race alerts: opt-in browser notifications when a race (or qualifying / sprint) goes live and when the result is in.
   Any element with [data-alerts] becomes a button that opens the alert settings. Works on the app and the static pages. */
(function () {
  "use strict";
  var KINDS = [["race", "Race start", "When the lights go out"], ["quali", "Qualifying", "When qualifying starts"],
               ["sprint", "Sprint", "When a sprint starts"], ["results", "Race result", "Winner and podium, with the race story"]];
  var LS = "pw-alerts";
  function load() { try { return JSON.parse(localStorage.getItem(LS) || "null"); } catch (e) { return null; } }
  function save(v) { try { v ? localStorage.setItem(LS, JSON.stringify(v)) : localStorage.removeItem(LS); } catch (e) {} }
  function track(n) { try { if (window.goatcounter && goatcounter.count) goatcounter.count({ path: n, title: n, event: true }); } catch (e) {} }
  var ios = /iP(hone|ad|od)/.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  var standalone = window.matchMedia && matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  var supported = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

  function u8(b64) {
    var pad = "=".repeat((4 - b64.length % 4) % 4), raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(raw, function (c) { return c.charCodeAt(0); });
  }
  async function currentSub() {
    if (!supported) return null;
    var reg = await navigator.serviceWorker.getRegistration("/");
    return reg ? reg.pushManager.getSubscription() : null;
  }
  async function storePrefs(prefs) { try { var c = await caches.open("pw-alerts"); await c.put("/__prefs", new Response(JSON.stringify(prefs))); } catch (e) {} }
  async function turnOn(prefs) {
    var perm = await Notification.requestPermission();
    if (perm !== "granted") throw new Error(perm === "denied" ? "blocked" : "dismissed");
    var reg = await navigator.serviceWorker.register("/sw.js", { scope: "/" });
    await navigator.serviceWorker.ready;
    var sub = await reg.pushManager.getSubscription();
    if (!sub) {
      var k = await (await fetch("/api/alerts")).json();
      sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: u8(k.publicKey) });
    }
    var r = await fetch("/api/alerts", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ subscription: sub.toJSON(), prefs: prefs }) });
    if (!r.ok) throw new Error("server");
    await storePrefs(prefs); save(prefs); track("alerts/on");
  }
  async function turnOff() {
    var sub = await currentSub();
    if (sub) {
      try { await fetch("/api/alerts", { method: "DELETE", headers: { "content-type": "application/json" }, body: JSON.stringify({ endpoint: sub.endpoint }) }); } catch (e) {}
      await sub.unsubscribe();
    }
    save(null); track("alerts/off");
  }

  var css = ".pwa-bg{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9998;display:flex;align-items:flex-end;justify-content:center}" +
    "@media(min-width:600px){.pwa-bg{align-items:center}}" +
    ".pwa{background:var(--panel,#13161E);color:var(--fg,#F1F3F7);border:1px solid var(--line,#262B36);border-radius:10px 10px 0 0;width:100%;max-width:420px;padding:20px 20px 18px;font:15px/1.45 system-ui,sans-serif;box-shadow:0 20px 60px rgba(0,0,0,.5)}" +
    "@media(min-width:600px){.pwa{border-radius:10px}}" +
    ".pwa h3{margin:0 0 4px;font-size:20px}.pwa p{margin:0 0 12px;color:var(--muted,#8C94A6);font-size:14px}" +
    ".pwa label{display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-top:1px solid var(--line,#262B36);cursor:pointer}" +
    ".pwa label input{margin-top:3px;width:18px;height:18px;accent-color:#E10600}.pwa label small{display:block;color:var(--muted,#8C94A6)}" +
    ".pwa .row{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}.pwa button{font:inherit;font-weight:700;border-radius:6px;padding:10px 14px;cursor:pointer;border:1px solid var(--line,#262B36);background:transparent;color:inherit}" +
    ".pwa button.go{background:#E10600;border-color:#E10600;color:#fff}.pwa .msg{margin-top:10px;font-size:14px}.pwa .msg.err{color:#ff6b6b}.pwa .msg.ok{color:#2FD480}";

  function open(btn) {
    if (!document.getElementById("pwa-css")) { var st = document.createElement("style"); st.id = "pwa-css"; st.textContent = css; document.head.appendChild(st); }
    var on = load(), prefs = on || { race: true, quali: false, sprint: false, results: true };
    var bg = document.createElement("div"); bg.className = "pwa-bg";
    var box = '<div class="pwa" role="dialog" aria-modal="true" aria-labelledby="pwaT"><h3 id="pwaT">🔔 Race alerts</h3>';
    if (!supported || (ios && !standalone)) {
      box += ios ? "<p>On iPhone and iPad, alerts work once Pit Wall is on your Home Screen: tap <b>Share</b> → <b>Add to Home Screen</b>, open Pit Wall from there, then turn alerts on.</p>"
                 : "<p>This browser can't show notifications. Try Chrome, Edge, Firefox or Safari, or add the race calendar instead.</p>";
      box += '<div class="row"><a class="go" href="/subscribe/" style="font-weight:700;color:#E10600">Add the calendar instead</a><button type="button" data-x>Close</button></div></div>';
    } else {
      box += "<p>A notification on this device when the session starts. Free, no sign-up, turn off any time.</p>";
      KINDS.forEach(function (k) { box += '<label><input type="checkbox" name="' + k[0] + '"' + (prefs[k[0]] ? " checked" : "") + '><span>' + k[1] + "<small>" + k[2] + "</small></span></label>"; });
      box += '<div class="row"><button type="button" class="go" data-on>' + (on ? "Save" : "Turn on alerts") + "</button>" + (on ? '<button type="button" data-off>Turn off</button>' : "") + '<button type="button" data-x>Close</button></div><div class="msg" aria-live="polite"></div></div>';
    }
    bg.innerHTML = box; document.body.appendChild(bg);
    var msg = bg.querySelector(".msg");
    function close() { bg.remove(); document.removeEventListener("keydown", esc); }
    function esc(e) { if (e.key === "Escape") close(); }
    document.addEventListener("keydown", esc);
    bg.addEventListener("click", async function (e) {
      if (e.target === bg || e.target.closest("[data-x]")) return close();
      if (e.target.closest("[data-on]")) {
        var p = {}; KINDS.forEach(function (k) { p[k[0]] = bg.querySelector('input[name="' + k[0] + '"]').checked; });
        if (!KINDS.some(function (k) { return p[k[0]]; })) { msg.className = "msg err"; msg.textContent = "Pick at least one alert."; return; }
        msg.className = "msg"; msg.textContent = "Turning on…";
        try { await turnOn(p); msg.className = "msg ok"; msg.textContent = "Done. You'll get a notification when it matters."; label(); setTimeout(close, 1400); }
        catch (err) {
          msg.className = "msg err";
          msg.textContent = err.message === "blocked" ? "Notifications are blocked for this site. Allow them in your browser's site settings, then try again." :
            err.message === "dismissed" ? "No notification permission was given." : "Something went wrong. Please try again in a minute.";
        }
      }
      if (e.target.closest("[data-off]")) { await turnOff(); label(); close(); }
    });
    var first = bg.querySelector("input,button"); if (first) first.focus();
  }

  function label() {
    var on = load();
    document.querySelectorAll("[data-alerts]").forEach(function (b) { b.textContent = on ? "🔔 Race alerts on" : "🔔 Get race-live alerts"; b.setAttribute("aria-pressed", on ? "true" : "false"); });
  }
  // keep the saved state honest if the browser dropped the subscription
  if (supported && load()) currentSub().then(function (s) { if (!s) { save(null); label(); } }).catch(function () {});
  document.addEventListener("click", function (e) { var b = e.target.closest && e.target.closest("[data-alerts]"); if (b) { e.preventDefault(); open(b); } });
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", label); else label();
  window.pwAlerts = { open: open };
})();
