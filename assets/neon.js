/* Neon Nights: a Las Vegas race-weekend look for Pit Wall F1 that switches itself off.
   Shown until the end of Monday 23 November 2026 (India time); after that this script does nothing.
   Adds: neon pink and cyan accents on a deep purple night, a glowing header line, a synthwave sunset banner
   with a city skyline and a moving grid, neon headings and buttons.
   Preview any time with ?neon=1, hide with ?neon=0. Original artwork; no game or brand imagery. */
(function () {
  "use strict";
  var END = Date.parse("2026-11-24T00:00:00+05:30");
  var RACE = Date.parse("2026-11-22T04:00:00Z"); // Las Vegas GP, Saturday 8 PM local
  var q = location.search;
  if (/[?&]embed=/.test(q) || /[?&]neon=0\b/.test(q)) return;
  if (Date.now() >= END && !/[?&]neon=1\b/.test(q)) return;
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  var PINK = "#FF2E88", CYAN = "#2DE2E6", ORANGE = "#FF9A3C", VIOLET = "#8B5CF6";

  /* skyline: generic towers, nothing real */
  var SKY = "data:image/svg+xml," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 120" preserveAspectRatio="none">' +
    '<path fill="#0B0716" d="M0 120V92h18V70h14v22h10V58h22v62h6V80h16V44h8V30h6v14h8v76h10V66h20v54h8V86h12V52l12-10 12 10v68h10V74h18v46h6V60h10V38h14v22h8v60h12V82h16v38h8V50h22v70h6V72h12V36h6V20h4v16h6v84h10V64h18v56h10V90h14V56h18v64h8V78h12V46h20v74h10V84h14v36h6V62h16v58h10V94h14V70h18v50h12V88h20v32h12V76h18v44z"/>' +
    '<g fill="' + CYAN + '" opacity=".55"><rect x="74" y="50" width="3" height="3"/><rect x="74" y="60" width="3" height="3"/><rect x="200" y="58" width="3" height="3"/><rect x="200" y="70" width="3" height="3"/>' +
    '<rect x="292" y="44" width="3" height="3"/><rect x="292" y="56" width="3" height="3"/><rect x="370" y="44" width="3" height="3"/><rect x="452" y="54" width="3" height="3"/><rect x="452" y="66" width="3" height="3"/></g>' +
    '<g fill="' + PINK + '" opacity=".6"><rect x="128" y="74" width="3" height="3"/><rect x="243" y="62" width="3" height="3"/><rect x="331" y="58" width="3" height="3"/><rect x="331" y="70" width="3" height="3"/><rect x="520" y="78" width="3" height="3"/></g></svg>');

  var css = "" +
    /* night palette (dark mode), neon accents (both modes) */
    "html.nn-on:not([data-theme=light]){--carbon:#0B0716;--bg:#0B0716;--panel:#140D24;--panel-2:#1C1331;--panel2:#1C1331;--line:#2E2149;--muted:#A194BD}" +
    "html.nn-on{--red:" + PINK + ";--red-glow:rgba(255,46,136,.5)}" +
    "html.nn-on:not([data-theme=light]) body{background:radial-gradient(120% 60% at 50% -10%,rgba(139,92,246,.22),transparent 60%),radial-gradient(80% 50% at 100% 0%,rgba(255,46,136,.12),transparent 60%),var(--carbon);background-attachment:fixed}" +
    /* glowing line under the header */
    ".nn-line{height:3px;position:relative;z-index:3;background:linear-gradient(90deg," + PINK + "," + ORANGE + " 35%," + VIOLET + " 65%," + CYAN + ");box-shadow:0 0 12px rgba(255,46,136,.7),0 0 26px rgba(45,226,230,.35)}" +
    "html.nn-on .brand i{filter:drop-shadow(0 0 6px rgba(45,226,230,.8))}" +
    "html.nn-on .brand em,html.nn-on .brand b{text-shadow:0 0 8px rgba(255,46,136,.8)}" +
    /* neon headings, cards, buttons */
    "html.nn-on:not([data-theme=light]) :is(h1,.pw-h1,.next h2,.sec-h,main>h2){text-shadow:0 0 1px #fff,0 0 10px rgba(255,46,136,.55),0 0 26px rgba(139,92,246,.35)}" +
    "html.nn-on :is(.next,.pulse-card,.last-race,.card,.tiles){box-shadow:0 0 0 1px rgba(255,46,136,.22),0 0 30px rgba(139,92,246,.12)}" +
    "html.nn-on :is(.btn,.cta,.lr-btn.primary){box-shadow:0 0 14px rgba(255,46,136,.55)}" +
    "html.nn-on :is(nav a.on,.tabs a.on,.nav a[aria-current]){text-shadow:0 0 10px rgba(255,46,136,.8)}" +
    /* the banner */
    ".nn-banner{position:relative;overflow:hidden;margin:26px 0 4px;border-radius:6px;isolation:isolate;min-height:210px;color:#fff;" +
    "background:linear-gradient(180deg,#1A0B33 0%,#3A0F4D 45%,#6E1650 70%,#2A0A2E 100%);border:1px solid rgba(255,46,136,.5);box-shadow:0 0 0 1px rgba(0,0,0,.25),0 0 40px rgba(255,46,136,.2)}" +
    ".nn-sun{position:absolute;left:62%;bottom:34px;width:230px;height:230px;margin-left:-115px;border-radius:50%;z-index:-3;" +
    "background:linear-gradient(180deg,#FFE36E 0%," + ORANGE + " 40%," + PINK + " 75%,#B0247A 100%);" +
    "-webkit-mask:linear-gradient(180deg,#000 0 52%,transparent 52% 57%,#000 57% 66%,transparent 66% 70%,#000 70% 78%,transparent 78% 81%,#000 81% 88%,transparent 88% 90%,#000 90%);" +
    "mask:linear-gradient(180deg,#000 0 52%,transparent 52% 57%,#000 57% 66%,transparent 66% 70%,#000 70% 78%,transparent 78% 81%,#000 81% 88%,transparent 88% 90%,#000 90%);filter:drop-shadow(0 0 24px rgba(255,120,80,.6))}" +
    ".nn-sky{position:absolute;left:0;right:0;bottom:34px;height:78px;z-index:-2;background:url(\"" + SKY + "\") bottom/100% 100% no-repeat}" +
    ".nn-grid{position:absolute;left:-50%;right:-50%;bottom:0;height:34px;z-index:-1;background:#120624;perspective:120px;overflow:hidden}" +
    ".nn-grid:before{content:'';position:absolute;inset:-100% 0 0;transform:rotateX(62deg);transform-origin:50% 100%;" +
    "background-image:linear-gradient(" + PINK + " 1.5px,transparent 1.5px),linear-gradient(90deg," + PINK + " 1.5px,transparent 1.5px);background-size:44px 22px;opacity:.75;animation:nnRoad 1.1s linear infinite}" +
    ".nn-grid:after{content:'';position:absolute;left:0;right:0;top:0;height:2px;background:" + PINK + ";box-shadow:0 0 12px " + PINK + "}" +
    "@keyframes nnRoad{to{background-position:0 22px,0 0}}" +
    ".nn-in{position:relative;padding:20px 54px 122px 22px;max-width:60%}" +
    ".nn-in h2{margin:0;font-family:var(--f-display,var(--fd,'Saira Condensed',sans-serif));font-style:italic;font-weight:900;text-transform:uppercase;font-size:clamp(34px,5.4vw,58px);line-height:.95;letter-spacing:.02em;color:#fff;" +
    "text-shadow:0 0 2px #fff,0 0 8px " + PINK + ",0 0 18px " + PINK + ",0 0 36px rgba(255,46,136,.7)}" +
    ".nn-in h2 span{color:#E9FFFF;text-shadow:0 0 2px #fff,0 0 8px " + CYAN + ",0 0 18px " + CYAN + ",0 0 36px rgba(45,226,230,.6)}" +
    ".nn-on-flicker{animation:nnFlick 6s infinite}" +
    "@keyframes nnFlick{0%,18%,22%,62%,64%,100%{opacity:1}20%,63%{opacity:.35}}" +
    ".nn-in p{margin:8px 0 0;font-size:15px;line-height:1.45;color:#F3E6FF;max-width:52ch;text-shadow:0 1px 3px rgba(20,0,30,.9)}" +
    ".nn-in p b{color:#fff}" +
    ".nn-x{position:absolute;top:8px;right:8px;width:34px;height:34px;border-radius:50%;border:1px solid rgba(255,46,136,.5);background:rgba(0,0,0,.3);color:#fff;font-size:18px;line-height:1;cursor:pointer;z-index:2}" +
    ".nn-x:hover{background:rgba(0,0,0,.5)}" +
    "@media (max-width:700px){.nn-in{max-width:none;padding:16px 46px 104px 16px}.nn-sun{left:80%;width:120px;height:120px;margin-left:-60px}.nn-sky{height:60px}.nn-in p{font-size:14px}}" +
    "@media (prefers-reduced-motion:reduce){.nn-grid:before,.nn-on-flicker{animation:none}}";
  var st = document.createElement("style"); st.id = "nn-style"; st.textContent = css; document.head.appendChild(st);

  function raceLocal() {
    try {
      return new Intl.DateTimeFormat(undefined, { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" }).format(new Date(RACE));
    } catch (e) { return new Date(RACE).toString(); }
  }

  function build() {
    if (document.querySelector(".nn-banner")) return;
    document.documentElement.classList.add("nn-on");
    var header = document.querySelector("header.strip, header.top");
    if (header && !document.querySelector(".nn-line")) {
      var l = document.createElement("div"); l.className = "nn-line"; l.setAttribute("aria-hidden", "true");
      header.parentNode.insertBefore(l, header.nextSibling);
    }
    var closed = false;
    try { closed = sessionStorage.getItem("pw_nn_closed") === "1"; } catch (e) {}
    if (closed) return;
    var main = document.querySelector("main"); if (!main) return;
    var done = Date.now() > RACE + 2.5 * 3600e3;
    var b = document.createElement("section"); b.className = "nn-banner"; b.setAttribute("aria-label", "Neon Nights: Las Vegas race weekend");
    b.innerHTML = '<div class="nn-sun" aria-hidden="true"></div><div class="nn-sky" aria-hidden="true"></div><div class="nn-grid" aria-hidden="true"></div>' +
      '<div class="nn-in"><h2><span class="nn-on-flicker">Neon</span> Nights</h2>' +
      (done ? "<p>The lights are out in Las Vegas. <b>Read how the race was won</b> in the last-race card, or relive it lap by lap in the race centre.</p>"
            : "<p>Formula 1 races down the Las Vegas Strip under the lights. <b>Lights out: " + raceLocal() + "</b> your time (8 PM Saturday in Vegas).</p>") +
      "</div>" +
      '<button type="button" class="nn-x" aria-label="Close the Neon Nights banner">×</button>';
    var anchor = main.querySelector(".pw-h1");
    var at = main.querySelector(".hero") || (anchor ? anchor.nextSibling : main.firstChild);
    main.insertBefore(b, at);
    b.querySelector(".nn-x").addEventListener("click", function () {
      b.remove(); try { sessionStorage.setItem("pw_nn_closed", "1"); } catch (e) {}
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build); else build();
  // take everything down at the deadline if the page is still open
  var left = END - Date.now();
  if (left > 0 && left < 2147483647) setTimeout(function () {
    var x = document.querySelectorAll(".nn-banner,.nn-line,#nn-style"); for (var i = 0; i < x.length; i++) x[i].remove();
    document.documentElement.classList.remove("nn-on");
  }, left);
})();
