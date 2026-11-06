"""Per-page share images (1200x630 JPEG) for races, replays, drivers, teams and circuits.

Called from build_pages.py with one spec per page. Drawn with Pillow and the open-licensed fonts
in scripts/fonts (Saira Condensed, Barlow; SIL Open Font License). No logos, photos or official
marks: just the page's own facts, team colours and the circuit outline from our telemetry.
An image is redrawn only when its spec changes (hashes kept in assets/og/pages/manifest.json).
"""
import hashlib, json, math, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "og", "pages")
FONTS = os.path.join(ROOT, "scripts", "fonts")
W, H = 1200, 630
BG, FG, MUTED, RED = (10, 12, 17), (241, 243, 247), (140, 148, 166), (225, 6, 0)

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:  # Pillow missing: pages keep their section image
    Image = None


def _rgb(h):
    h = h.lstrip("#")[:6]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) if len(h) == 6 else (136, 136, 136)


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def _italic_text(img, xy, text, font, fill, skew=0.2):
    """Draw text slanted like the site's italic display type."""
    l, t, r, b = font.getbbox(text)
    w, h = r + 40, b + 20
    layer = Image.new("L", (w, h), 0)
    ImageDraw.Draw(layer).text((10, 0), text, font=font, fill=255)
    layer = layer.transform((w + int(h * skew), h), Image.AFFINE, (1, skew, -h * skew, 0, 1, 0), Image.BICUBIC)
    img.paste(Image.new("RGB", layer.size, fill), (xy[0] - 10, xy[1]), layer)
    return r - l


def _fit(text, name, size, max_w, min_size=48):
    while size > min_size and _font(name, size).getlength(text) > max_w:
        size -= 4
    return _font(name, size)


def _track(img, slug, box, colour):
    p = os.path.join(ROOT, "data", "tracks", f"{slug}.json")
    if not slug or not os.path.exists(p):
        return
    pts = [(q[0], -q[1]) for q in json.load(open(p))["pts"]]
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    x0, y0, x1, y1 = box
    sc = min((x1 - x0) / (max(xs) - min(xs)), (y1 - y0) / (max(ys) - min(ys)))
    ox = x0 + ((x1 - x0) - (max(xs) - min(xs)) * sc) / 2 - min(xs) * sc
    oy = y0 + ((y1 - y0) - (max(ys) - min(ys)) * sc) / 2 - min(ys) * sc
    line = [(ox + x * sc, oy + y * sc) for x, y in pts] + [(ox + pts[0][0] * sc, oy + pts[0][1] * sc)]
    glow = Image.new("RGB", (W, H), (0, 0, 0))
    ImageDraw.Draw(glow).line(line, fill=colour, width=22, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    img.paste(Image.blend(img, Image.composite(glow, img, glow.convert("L")), 0.55))
    d = ImageDraw.Draw(img)
    d.line(line, fill=(30, 34, 44), width=16, joint="curve")
    d.line(line, fill=colour, width=7, joint="curve")
    sx, sy = line[0]
    d.rectangle([sx - 9, sy - 9, sx + 9, sy + 9], fill=FG)


def render(spec, path):
    acc = _rgb(spec.get("accent", "#E10600"))
    img = Image.new("RGB", (W, H), BG)
    # soft glow in the accent colour on the right, faint speed stripes
    glow = Image.new("RGB", (W, H), BG)
    ImageDraw.Draw(glow).ellipse([700, 40, 1260, 600], fill=tuple(int(c * 0.45) for c in acc))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(120)), 0.9)
    d = ImageDraw.Draw(img)
    for x in range(-400, W, 60):
        d.line([(x, H), (x + 170, 0)], fill=(16, 19, 26), width=2)
    d.rectangle([0, 0, 13, H], fill=acc)
    # brand
    for i in range(4):
        for j in range(4):
            if (i + j) % 2 == 0:
                d.rectangle([72 + i * 9, 58 + j * 9, 80 + i * 9, 66 + j * 9], fill=FG)
    d.rectangle([71, 57, 108, 94], outline=FG, width=2)
    bf = _font("SairaCondensed-ExtraBold.ttf", 46)
    _italic_text(img, (126, 46), "PIT WALL", bf, FG)
    _italic_text(img, (126 + int(bf.getlength("PIT WALL ")), 46), "F1", bf, RED)
    d = ImageDraw.Draw(img)
    right = spec.get("track") or spec.get("number")
    max_w = 640 if right else 1060
    y = 140
    if spec.get("kicker"):
        d.text((72, y), spec["kicker"].upper(), font=_font("Barlow-SemiBold.ttf", 26), fill=acc if spec.get("accent") else MUTED)
        y += 34
    lines = spec["title"][:2]
    size = min(_fit(l.upper(), "SairaCondensed-ExtraBold.ttf", 92 if len(lines) > 1 else 104, max_w).size for l in lines)
    f = _font("SairaCondensed-ExtraBold.ttf", size)
    for line in lines:
        _italic_text(img, (70, y - int(size * 0.12)), line.upper(), f, FG)
        y += int(size * 0.98)
    d = ImageDraw.Draw(img)
    if spec.get("sub"):
        d.text((72, y + 12), spec["sub"], font=_font("Barlow-Medium.ttf", 30), fill=MUTED)
        y += 56
    if spec.get("podium"):
        x = 72
        for i, (code, col) in enumerate(spec["podium"][:3]):
            d.rounded_rectangle([x, y + 18, x + 190, y + 118], radius=6, fill=(22, 26, 35))
            d.rectangle([x, y + 18, x + 8, y + 118], fill=_rgb(col))
            d.text((x + 24, y + 26), f"P{i + 1}", font=_font("Barlow-SemiBold.ttf", 24), fill=MUTED)
            d.text((x + 24, y + 52), code, font=_font("SairaCondensed-ExtraBold.ttf", 52), fill=FG)
            x += 206
    elif spec.get("stats"):
        x = 72
        for label, val in spec["stats"][:4]:
            fv = _font("SairaCondensed-ExtraBold.ttf", 54)
            wv = max(fv.getlength(str(val)), _font("Barlow-SemiBold.ttf", 22).getlength(label.upper())) + 44
            d.rounded_rectangle([x, y + 18, x + wv, y + 118], radius=6, fill=(22, 26, 35))
            d.text((x + 20, y + 28), label.upper(), font=_font("Barlow-SemiBold.ttf", 22), fill=MUTED)
            d.text((x + 20, y + 52), str(val), font=fv, fill=FG)
            x += wv + 14
    if spec.get("track"):
        _track(img, spec["track"], (780, 120, 1140, 520), acc)
    elif spec.get("number"):
        f = _font("SairaCondensed-ExtraBold.ttf", 330)
        _italic_text(img, (820, 110), str(spec["number"]), f, acc)
    d = ImageDraw.Draw(img)
    uf = _font("SairaCondensed-Bold.ttf", 34)
    ux = W - 70 - uf.getlength("pitwallf1.in")
    d.text((ux, 52), "pitwallf1", font=uf, fill=FG)
    d.text((ux + uf.getlength("pitwallf1"), 52), ".in", font=uf, fill=RED)
    tag = "The unofficial Formula 1 fan hub"
    tf = _font("Barlow-Medium.ttf", 22)
    d.text((W - 70 - tf.getlength(tag), H - 60), tag, font=tf, fill=MUTED)
    img.save(path, "JPEG", quality=84, optimize=True, progressive=True)


def build(specs):
    """specs: {key: spec}. Writes assets/og/pages/<key>.jpg for new or changed specs; returns the keys available."""
    if Image is None:
        return set(k for k in specs if os.path.exists(os.path.join(OUT, f"{k}.jpg")))
    os.makedirs(OUT, exist_ok=True)
    mf = os.path.join(OUT, "manifest.json")
    old = json.load(open(mf)) if os.path.exists(mf) else {}
    font_ver = sum(os.path.getsize(os.path.join(FONTS, f)) for f in os.listdir(FONTS))
    new, drawn = {}, 0
    for key, spec in specs.items():
        hsh = hashlib.sha1((json.dumps(spec, sort_keys=True) + str(font_ver) + "v1").encode()).hexdigest()[:12]
        out = os.path.join(OUT, f"{key}.jpg")
        if old.get(key) != hsh or not os.path.exists(out):
            render(spec, out); drawn += 1
        new[key] = hsh
    for key in set(old) - set(new):
        try: os.remove(os.path.join(OUT, f"{key}.jpg"))
        except OSError: pass
    if new != old:
        json.dump(new, open(mf, "w"), indent=0, sort_keys=True)
    if drawn:
        print(f"  share images: drew {drawn}, {len(new)} in total")
    return set(new)


_STATE = {"old": None, "new": {}, "drawn": 0}


def ensure(key, spec):
    """Make sure assets/og/pages/<key>.jpg matches spec; returns the og key ("pages/<key>") or None."""
    if Image is None:
        return f"pages/{key}" if os.path.exists(os.path.join(OUT, f"{key}.jpg")) else None
    if _STATE["old"] is None:
        os.makedirs(OUT, exist_ok=True)
        mf = os.path.join(OUT, "manifest.json")
        _STATE["old"] = json.load(open(mf)) if os.path.exists(mf) else {}
    font_ver = sum(os.path.getsize(os.path.join(FONTS, f)) for f in os.listdir(FONTS))
    hsh = hashlib.sha1((json.dumps(spec, sort_keys=True) + str(font_ver) + "v2").encode()).hexdigest()[:12]
    out = os.path.join(OUT, f"{key}.jpg")
    if _STATE["old"].get(key) != hsh or not os.path.exists(out):
        render(spec, out); _STATE["drawn"] += 1
    _STATE["new"][key] = hsh
    return f"pages/{key}"


def finish():
    """Write the manifest and delete images no page uses any more."""
    if Image is None or _STATE["old"] is None:
        return
    for key in set(_STATE["old"]) - set(_STATE["new"]):
        try: os.remove(os.path.join(OUT, f"{key}.jpg"))
        except OSError: pass
    if _STATE["new"] != _STATE["old"]:
        json.dump(_STATE["new"], open(os.path.join(OUT, "manifest.json"), "w"), indent=0, sort_keys=True)
    if _STATE["drawn"]:
        print(f"  share images: drew {_STATE['drawn']}, {len(_STATE['new'])} in total")
