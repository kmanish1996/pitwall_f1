/* Happy Diwali from Pit Wall F1 — festive decorations that switch themselves off.
   Shown until the end of Thursday 12 November 2026 (India time); after that this script does nothing.
   Adds: a marigold toran under the header, a greeting banner with five diyas that light up like F1 start
   lights (and stay lit), soft fireworks behind the banner, and warm gold glows on the cards.
   Preview any time with ?diwali=1, hide with ?diwali=0. */
(function () {
  "use strict";
  var END = Date.parse("2026-11-13T00:00:00+05:30");
  var q = location.search;
  if (/[?&]embed=/.test(q) || /[?&]diwali=0\b/.test(q)) return;
  if (Date.now() >= END && !/[?&]diwali=1\b/.test(q)) return;
  var reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- styles ---------- */
  var TORAN = "data:image/svg+xml," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="40" viewBox="0 0 120 40">' +
    '<path d="M0 3 Q60 26 120 3" fill="none" stroke="#C9871F" stroke-width="2"/>' +
    // mango leaves
    '<g fill="#2E8B3D"><path d="M14 7 q4 10 0 17 q-4 -7 0 -17z"/><path d="M46 14 q4 10 0 17 q-4 -7 0 -17z"/><path d="M74 14 q4 10 0 17 q-4 -7 0 -17z"/><path d="M106 7 q4 10 0 17 q-4 -7 0 -17z"/></g>' +
    '<g fill="#3FA552"><path d="M14 9 q2 7 0 12z"/><path d="M46 16 q2 7 0 12z"/><path d="M74 16 q2 7 0 12z"/><path d="M106 9 q2 7 0 12z"/></g>' +
    // marigolds
    '<g><circle cx="30" cy="12" r="6.5" fill="#FF8C1A"/><circle cx="30" cy="12" r="4" fill="#FFB238"/><circle cx="30" cy="12" r="1.8" fill="#E2611A"/>' +
    '<circle cx="60" cy="15" r="7" fill="#FFC21A"/><circle cx="60" cy="15" r="4.3" fill="#FFD960"/><circle cx="60" cy="15" r="1.9" fill="#E8940E"/>' +
    '<circle cx="90" cy="12" r="6.5" fill="#FF8C1A"/><circle cx="90" cy="12" r="4" fill="#FFB238"/><circle cx="90" cy="12" r="1.8" fill="#E2611A"/>' +
    '<line x1="60" y1="22" x2="60" y2="30" stroke="#C9871F" stroke-width="1.2"/><circle cx="60" cy="33" r="4" fill="#FF6A1A"/><circle cx="60" cy="33" r="2" fill="#FFB238"/></g></svg>');
  var RANGOLI = "data:image/svg+xml," + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-100 -100 200 200">' +
    '<g fill="none" stroke-width="3">' +
    [0, 45, 90, 135, 180, 225, 270, 315].map(function (a) {
      return '<path transform="rotate(' + a + ')" d="M0 -20 C 18 -40 18 -70 0 -92 C -18 -70 -18 -40 0 -20z" stroke="#FFC93C" fill="rgba(255,79,154,.18)"/>';
    }).join("") +
    [22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5].map(function (a) {
      return '<circle transform="rotate(' + a + ')" cx="0" cy="-62" r="7" fill="#2FD480" stroke="none" opacity=".75"/>';
    }).join("") +
    '<circle r="16" stroke="#FF8C1A" fill="rgba(255,140,26,.25)"/><circle r="6" fill="#FFC93C" stroke="none"/><circle r="40" stroke="#FFC93C" stroke-dasharray="4 7" opacity=".7"/></g></svg>');
  var css = "" +
    ".dw-toran{height:40px;margin-bottom:-22px;position:relative;z-index:3;pointer-events:none;background:url(\"" + TORAN + "\") repeat-x 0 0/120px 40px;filter:drop-shadow(0 3px 4px rgba(0,0,0,.35))}" +
    "header.strip+.dw-toran,header.top+.dw-toran{margin-top:-1px}" +
    ".dw-banner{position:relative;overflow:hidden;margin:26px 0 4px;border-radius:6px;color:#FFF4DC;isolation:isolate;" +
    "background:radial-gradient(120% 140% at 0% 0%,#5A1530 0%,#2E0B33 45%,#160A24 100%);border:1px solid rgba(255,201,60,.45);box-shadow:0 0 0 1px rgba(0,0,0,.2),0 14px 40px rgba(255,140,26,.12)}" +
    ".dw-banner canvas{position:absolute;inset:0;width:100%;height:100%;z-index:-1}" +
    ".dw-banner:before{content:'';position:absolute;right:-60px;top:50%;width:260px;height:260px;transform:translateY(-50%);background:url(\"" + RANGOLI + "\") center/contain no-repeat;opacity:.55;z-index:-1}" +
    ".dw-banner:after{content:'';position:absolute;left:-70px;bottom:-90px;width:200px;height:200px;background:url(\"" + RANGOLI + "\") center/contain no-repeat;opacity:.3;z-index:-1}" +
    ".dw-in{display:flex;align-items:center;gap:22px 28px;padding:18px 54px 18px 22px;flex-wrap:wrap}" +
    ".dw-diyas{display:flex;gap:10px;padding:10px 14px 8px;background:rgba(0,0,0,.35);border:1px solid rgba(255,201,60,.25);border-radius:8px}" +
    ".dw-diya{width:40px;height:44px;position:relative}" +
    ".dw-diya svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}" +
    ".dw-flame{transform-origin:20px 22px;transform:scale(0);opacity:0;transition:transform .35s cubic-bezier(.3,1.6,.5,1),opacity .2s}" +
    ".dw-diya.on .dw-flame{transform:scale(1);opacity:1;animation:dwFlick 1.6s ease-in-out infinite alternate}" +
    ".dw-glow{opacity:0;transition:opacity .4s}.dw-diya.on .dw-glow{opacity:1}" +
    "@keyframes dwFlick{0%{transform:scale(1) rotate(-2deg)}35%{transform:scale(1.06,.94) rotate(2deg)}70%{transform:scale(.95,1.07) rotate(-1deg)}100%{transform:scale(1.03) rotate(1.5deg)}}" +
    ".dw-txt{flex:1;min-width:220px}" +
    ".dw-txt h2{margin:0;font-family:var(--f-display,var(--fd,'Saira Condensed',sans-serif));font-style:italic;font-weight:800;text-transform:uppercase;font-size:clamp(28px,4vw,40px);line-height:1;letter-spacing:.01em;" +
    "background:linear-gradient(180deg,#FFE7A3 0%,#FFC93C 55%,#FF9A1F 100%);-webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 2px 8px rgba(255,160,40,.35))}" +
    ".dw-txt p{margin:6px 0 0;font-size:15px;line-height:1.45;color:#F4DDBB;max-width:62ch}" +
    ".dw-x{position:absolute;top:8px;right:8px;width:34px;height:34px;border-radius:50%;border:1px solid rgba(255,201,60,.35);background:rgba(0,0,0,.25);color:#FFE7A3;font-size:18px;line-height:1;cursor:pointer}" +
    ".dw-x:hover{background:rgba(0,0,0,.45)}" +
    "html.dw-on .next,html.dw-on .pulse-card,html.dw-on .last-race{box-shadow:0 0 0 1px rgba(255,201,60,.18),0 10px 34px rgba(255,140,26,.10)}" +
    ".dw-rang{position:absolute;right:-50px;top:-50px;width:190px;height:190px;background:url(\"" + RANGOLI + "\") center/contain no-repeat;opacity:.14;pointer-events:none;z-index:0}" +
    "@media (max-width:640px){.dw-in{padding:16px 46px 16px 16px;gap:14px}.dw-diya{width:32px;height:36px}.dw-diyas{gap:6px;padding:8px 10px 6px}.dw-txt p{font-size:14px}.dw-banner:before{width:180px;height:180px;right:-70px}}" +
    "@media (prefers-reduced-motion:reduce){.dw-diya.on .dw-flame{animation:none}}";
  var st = document.createElement("style"); st.id = "dw-style"; st.textContent = css; document.head.appendChild(st);

  function diyaSVG(i) {
    return '<svg viewBox="0 0 40 44" aria-hidden="true">' +
      '<defs><radialGradient id="dwg' + i + '" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#FFD25C" stop-opacity=".9"/><stop offset="1" stop-color="#FF8C1A" stop-opacity="0"/></radialGradient>' +
      '<linearGradient id="dwf' + i + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFF6C8"/><stop offset=".45" stop-color="#FFC93C"/><stop offset="1" stop-color="#FF6A1A"/></linearGradient></defs>' +
      '<circle class="dw-glow" cx="20" cy="16" r="18" fill="url(#dwg' + i + ')"/>' +
      '<path class="dw-flame" d="M20 4 C 26 12 25 19 20 23 C 15 19 14 12 20 4z" fill="url(#dwf' + i + ')"/>' +
      '<path d="M3 26 Q20 24 37 26 Q34 38 20 39 Q6 38 3 26z" fill="#B5502A"/>' +
      '<path d="M3 26 Q20 24 37 26 Q20 30 3 26z" fill="#7A2E15"/>' +
      '<path d="M8 32 q3 2 6 0 M17 33.5 q3 2 6 0 M26 32 q3 2 6 0" stroke="#FFC93C" stroke-width="1.4" fill="none"/>' +
      '<ellipse cx="20" cy="41.5" rx="11" ry="1.6" fill="#000" opacity=".35"/></svg>';
  }

  function build() {
    if (document.querySelector(".dw-banner")) return;
    document.documentElement.classList.add("dw-on");
    var header = document.querySelector("header.strip, header.top");
    if (header) {
      var t = document.createElement("div"); t.className = "dw-toran"; t.setAttribute("aria-hidden", "true");
      header.parentNode.insertBefore(t, header.nextSibling);
    }
    var nx = document.querySelector(".next");
    if (nx) { var rg = document.createElement("span"); rg.className = "dw-rang"; rg.setAttribute("aria-hidden", "true"); nx.appendChild(rg); }
    var closed = false;
    try { closed = sessionStorage.getItem("pw_dw_closed") === "1"; } catch (e) {}
    if (closed) return;
    var main = document.querySelector("main"); if (!main) return;
    var b = document.createElement("section"); b.className = "dw-banner"; b.setAttribute("aria-label", "Happy Diwali");
    var d = ""; for (var i = 0; i < 5; i++) d += '<div class="dw-diya">' + diyaSVG(i) + "</div>";
    b.innerHTML = '<canvas aria-hidden="true"></canvas><div class="dw-in"><div class="dw-diyas" role="img" aria-label="Five diyas, lit one by one">' + d + '</div>' +
      '<div class="dw-txt"><h2>Happy Diwali</h2><p>Five lights on, and this time they stay on. Wishing every F1 fan a season full of light, colour and fastest laps. 🪔</p></div></div>' +
      '<button type="button" class="dw-x" aria-label="Close the Diwali greeting">×</button>';
    var anchor = main.querySelector(".pw-h1");
    var at = main.querySelector(".hero") || (anchor ? anchor.nextSibling : main.firstChild);
    main.insertBefore(b, at);
    b.querySelector(".dw-x").addEventListener("click", function () {
      b.remove(); try { sessionStorage.setItem("pw_dw_closed", "1"); } catch (e) {}
    });
    // diyas light up one by one, like the start lights, and stay lit
    var lamps = b.querySelectorAll(".dw-diya");
    for (var k = 0; k < lamps.length; k++) (function (el, n) { setTimeout(function () { el.classList.add("on"); }, reduce ? 0 : 500 + n * 650); })(lamps[k], k);
    if (!reduce) fireworks(b, b.querySelector("canvas"));
  }

  /* ---------- soft fireworks behind the banner ---------- */
  function fireworks(box, cv) {
    var ctx = cv.getContext("2d"); if (!ctx) return;
    var W = 0, H = 0, dpr = Math.min(2, window.devicePixelRatio || 1), parts = [], next = 0, visible = true, raf = 0;
    var COLS = ["#FFC93C", "#FF8C1A", "#FF4F9A", "#2FD480", "#FFE7A3", "#B54BE8"];
    function size() { var r = box.getBoundingClientRect(); W = r.width; H = r.height; cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); }
    size(); addEventListener("resize", size);
    function burst() {
      var x = W * (0.35 + Math.random() * 0.6), y = H * (0.18 + Math.random() * 0.5), c = COLS[(Math.random() * COLS.length) | 0], n = 34 + ((Math.random() * 16) | 0);
      for (var i = 0; i < n; i++) { var a = (i / n) * Math.PI * 2, s = 0.8 + Math.random() * 1.8; parts.push({ x: x, y: y, vx: Math.cos(a) * s, vy: Math.sin(a) * s, life: 1, c: c }); }
    }
    function frame(t) {
      raf = 0; if (!visible || document.hidden) return;
      ctx.clearRect(0, 0, W, H);
      if (t > next) { burst(); next = t + 900 + Math.random() * 1400; }
      ctx.globalCompositeOperation = "lighter";
      for (var i = parts.length - 1; i >= 0; i--) {
        var p = parts[i]; p.x += p.vx; p.y += p.vy; p.vy += 0.02; p.vx *= 0.985; p.vy *= 0.985; p.life -= 0.012;
        if (p.life <= 0) { parts.splice(i, 1); continue; }
        ctx.globalAlpha = Math.max(0, p.life) * 0.8; ctx.fillStyle = p.c;
        ctx.beginPath(); ctx.arc(p.x, p.y, 1.6, 0, 6.283); ctx.fill();
      }
      ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";
      raf = requestAnimationFrame(frame);
    }
    function go() { if (!raf && visible && !document.hidden) raf = requestAnimationFrame(frame); }
    if ("IntersectionObserver" in window) new IntersectionObserver(function (es) { visible = es[0].isIntersecting; go(); }).observe(box);
    document.addEventListener("visibilitychange", go);
    // stop drawing at the deadline even if the tab stays open
    setTimeout(function () { visible = false; }, Math.max(0, END - Date.now()));
    go();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", build); else build();
  // take everything down at the deadline if the page is still open
  var left = END - Date.now();
  if (left > 0 && left < 2147483647) setTimeout(function () {
    var x = document.querySelectorAll(".dw-banner,.dw-toran,.dw-rang,#dw-style"); for (var i = 0; i < x.length; i++) x[i].remove();
    document.documentElement.classList.remove("dw-on");
  }, left);
})();
