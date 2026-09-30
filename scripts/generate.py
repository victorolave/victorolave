"""Generates the GitHub profile README assets (banner, project cards, stack map).

Fonts are the portfolio's own (Fraunces, Inter, JetBrains Mono), instanced at
the site's variation settings, subset per SVG and embedded as base64 — GitHub
renders SVGs as <img>, which cannot load external fonts.

Usage (from the repo root):

    python3 -m venv .venv && .venv/bin/pip install fonttools brotli
    .venv/bin/python scripts/generate.py

FONTS_DIR defaults to the portfolio checkout next to this repo
(../victorolave/public/fonts). The banner decoration is picked with DECOR
(halftone by default; also blur, diagram, topo, dots, ripple, mono, ridge).
"""
import base64, io, os, sys
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset
from xml.sax.saxutils import escape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.environ.get("FONTS_DIR", os.path.join(ROOT, "..", "victorolave", "public", "fonts"))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "assets")
os.makedirs(OUT, exist_ok=True)

SPECS = {
    "serif":  ("fraunces-latin-full-normal.7e744849.woff2", {"opsz": 144, "SOFT": 50, "wght": 340}),
    "italic": ("fraunces-latin-full-italic.04a14ea3.woff2", {"opsz": 144, "SOFT": 100, "wght": 340}),
    "sans":   ("inter-latin-wght-normal.3100e775.woff2", {"wght": 400}),
    "sansm":  ("inter-latin-wght-normal.3100e775.woff2", {"wght": 500}),
    "mono":   ("jetbrains-mono-latin-wght-normal.18be4527.woff2", {"wght": 400}),
}
FAMILY = {
    "serif": "'VO Serif', Georgia, serif",
    "italic": "'VO Italic', Georgia, serif",
    "sans": "'VO Sans', system-ui, sans-serif",
    "sansm": "'VO SansM', system-ui, sans-serif",
    "mono": "'VO Mono', ui-monospace, monospace",
}
FACE = {"serif": "VO Serif", "italic": "VO Italic", "sans": "VO Sans", "sansm": "VO SansM", "mono": "VO Mono"}

_static = {}
def static(key):
    if key not in _static:
        f, loc = SPECS[key]
        font = TTFont(os.path.join(FONTS_DIR, f), recalcTimestamp=False)
        font.flavor = None
        _static[key] = instancer.instantiateVariableFont(font, loc)
    return _static[key]

def width(key, text, size, tracking=0.0):
    """Advance width in px, including kerning-free advances and tracking (em)."""
    font = static(key)
    cmap = font.getBestCmap(); hmtx = font["hmtx"]; upm = font["head"].unitsPerEm
    w = sum(hmtx[cmap.get(ord(c), cmap[ord("?")])][0] for c in text)
    return w * size / upm + tracking * size * len(text)

def embed(key, chars):
    buf = io.BytesIO()
    font = TTFont(io.BytesIO(_to_bytes(static(key))), recalcTimestamp=False)
    opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["kern", "liga"]
    s = subset.Subsetter(opts); s.populate(text="".join(sorted(set(chars)))); s.subset(font)
    font.flavor = "woff2"; font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()

def _to_bytes(font):
    b = io.BytesIO(); font.save(b); return b.getvalue()

THEMES = {
    "dark": dict(bg="#1A1D24", page="#0d1117", surface="#21252E", grid="#171C24", gridMajor="#1F252E", rule="#3A4051",
                 fg="#E8E4DD", fg2="#9CA0AC", fg3="#5C6172", fg4="#404552",
                 rose="#C04970", roseText="#D87A99", blob="#C04970", blob2="#8C2B4A",
                 ok="#6FA887", warn="#C9A063", info="#7B96B8", blobOpacity=0.42, grain=0.07),
    "light": dict(bg="#FBEFE7", page="#ffffff", surface="#FFF8F3", grid="#F4E8E1", gridMajor="#EDDCD2", rule="#D9BFB0",
                  fg="#1A1D24", fg2="#4A4F5C", fg3="#767B88", fg4="#B4A7A1",
                  rose="#C04970", roseText="#8C2B4A", blob="#F5C9D5", blob2="#D87A99",
                  ok="#3F7A5A", warn="#8F6A2A", info="#44628A", blobOpacity=0.6, grain=0),
}

class Svg:
    def __init__(self, w, h, title):
        self.w, self.h, self.title = w, h, title
        self.body, self.chars = [], {k: set() for k in SPECS}
    def text(self, x, y, runs, size, fill=None, anchor="start", tracking=0.0, cls="", upper=False):
        """runs: list of (fontkey, text, fill|None)."""
        spans = []
        for key, t, f in runs:
            t = t.upper() if upper else t
            self.chars[key].update(t)
            fl = f"fill='{f}'" if f else ""
            spans.append(f"<tspan style=\"font-family:{FAMILY[key]}\" {fl}>{escape(t)}</tspan>")
        ls = f"letter-spacing='{tracking}em'" if tracking else ""
        self.body.append(f"<text x='{x}' y='{y}' font-size='{size}' text-anchor='{anchor}' {ls} "
                         f"fill='{fill or 'currentColor'}' class='{cls}' xml:space='preserve'>{''.join(spans)}</text>")
    def raw(self, s): self.body.append(s)
    def render(self, css):
        faces = "".join(
            f"@font-face{{font-family:'{FACE[k]}';src:url(data:font/woff2;base64,{embed(k, c)}) format('woff2');}}"
            for k, c in self.chars.items() if c)
        return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{self.w}' height='{self.h}' "
                f"viewBox='0 0 {self.w} {self.h}' role='img' aria-label='{escape(self.title)}'>"
                f"<title>{escape(self.title)}</title><style>{faces}{css}</style>{''.join(self.body)}</svg>")

BASE_CSS = """
text{text-rendering:geometricPrecision}
.rise{transform-box:fill-box;animation:rise 1s cubic-bezier(.2,.7,.2,1) backwards}
@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
.fade{animation:fade 1.2s ease backwards}
@keyframes fade{from{opacity:0}}
.draw{animation:draw 1.1s cubic-bezier(.6,0,.2,1) backwards}
@keyframes draw{from{stroke-dashoffset:var(--l)}to{stroke-dashoffset:0}}
.drift{transform-box:fill-box;transform-origin:center;animation:drift 16s ease-in-out infinite alternate}
@keyframes drift{from{transform:translate(0,0) scale(1)}to{transform:translate(-50px,18px) scale(1.06)}}
.drift2{transform-box:fill-box;transform-origin:center;animation:drift2 21s ease-in-out infinite alternate}
@keyframes drift2{from{transform:translate(0,0)}to{transform:translate(40px,-14px) scale(.94)}}
.blink{animation:blink 1.1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.4s ease-out infinite}
@keyframes pulse{from{opacity:.55;transform:scale(1)}to{opacity:0;transform:scale(3.2)}}
.nudge{animation:nudge 2.8s ease-in-out infinite}
@keyframes nudge{0%,60%,100%{transform:translateX(0)}30%{transform:translateX(6px)}}
.flow{animation:flow 3.6s cubic-bezier(.45,0,.55,1) infinite}
@keyframes flow{from{stroke-dashoffset:18}to{stroke-dashoffset:calc(var(--l) * -1)}}
.wave{animation:wave 4.2s ease-in-out infinite}
@keyframes wave{0%,100%{opacity:.22}45%,55%{opacity:1}}
.topo-a{transform-box:view-box;transform-origin:985px 212px;animation:breathe 14s ease-in-out infinite alternate}
@keyframes breathe{from{transform:scale(1) rotate(0deg)}to{transform:scale(1.035) rotate(2.5deg)}}
.glint{animation:glint 3.8s ease-in-out infinite}
@keyframes glint{0%,100%{opacity:.55}40%,60%{opacity:1}}
.scan{animation:scan 3.2s ease-in-out infinite}
@keyframes scan{0%,100%{fill-opacity:.35}50%{fill-opacity:1}}
@media (prefers-reduced-motion:reduce){
 *{animation:none!important}}
"""

# Static profile: no motion anywhere. Every element is drawn in its final
# state, so the keyframes above are simply not shipped.
BASE_CSS = "text{text-rendering:geometricPrecision}"

def defs(t, w, h, gid, fade_from_left=True):
    mask = (f"<linearGradient id='{gid}fg' x1='0' x2='1'><stop offset='0' stop-color='#fff' stop-opacity='.25'/>"
            f"<stop offset='.55' stop-color='#fff' stop-opacity='.9'/><stop offset='1' stop-color='#fff'/></linearGradient>"
            f"<mask id='{gid}m'><rect width='{w}' height='{h}' fill='url(#{gid}fg)'/></mask>")
    return (f"<defs>"
            f"<pattern id='{gid}g' width='32' height='32' patternUnits='userSpaceOnUse'>"
            f"<path d='M32 0H0V32' fill='none' stroke='{t['grid']}' stroke-width='1'/></pattern>"
            f"<pattern id='{gid}G' width='160' height='160' patternUnits='userSpaceOnUse'>"
            f"<path d='M160 0H0V160' fill='none' stroke='{t['gridMajor']}' stroke-width='1'/></pattern>"
            f"<radialGradient id='{gid}b'><stop offset='0' stop-color='{t['blob']}'/><stop offset='.45' stop-color='{t['blob']}' stop-opacity='.45'/>"
            f"<stop offset='1' stop-color='{t['blob']}' stop-opacity='0'/></radialGradient>"
            f"<radialGradient id='{gid}b2'><stop offset='0' stop-color='{t['blob2']}'/><stop offset='.45' stop-color='{t['blob2']}' stop-opacity='.45'/>"
            f"<stop offset='1' stop-color='{t['blob2']}' stop-opacity='0'/></radialGradient>"
            f"<filter id='{gid}n' x='0' y='0' width='100%' height='100%'>"
            f"<feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/>"
            f"<feColorMatrix values='0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 1 0'/></filter>"
            f"<linearGradient id='{gid}ex'><stop offset='0' stop-color='#fff' stop-opacity='0'/><stop offset='.1' stop-color='#fff'/>"
            f"<stop offset='.9' stop-color='#fff'/><stop offset='1' stop-color='#fff' stop-opacity='0'/></linearGradient>"
            f"<linearGradient id='{gid}ey' x2='0' y2='1'><stop offset='0' stop-color='#fff' stop-opacity='0'/><stop offset='.18' stop-color='#fff'/>"
            f"<stop offset='.82' stop-color='#fff'/><stop offset='1' stop-color='#fff' stop-opacity='0'/></linearGradient>"
            f"<mask id='{gid}mx' maskUnits='userSpaceOnUse' x='0' y='0' width='{w}' height='{h}'><rect width='{w}' height='{h}' fill='url(#{gid}ex)'/></mask>"
            f"<mask id='{gid}my' maskUnits='userSpaceOnUse' x='0' y='0' width='{w}' height='{h}'><rect width='{w}' height='{h}' fill='url(#{gid}ey)'/></mask>"
            f"<clipPath id='{gid}clip'><rect x='1' y='1' width='{w - 2}' height='{h - 2}' rx='6'/></clipPath>"
            f"{mask}</defs>")

def marks(t, w, h, inset=20, size=12):
    c = t["fg4"]; p = []
    for x, y, dx, dy in [(inset, inset, 1, 1), (w - inset, inset, -1, 1), (inset, h - inset, 1, -1), (w - inset, h - inset, -1, -1)]:
        p.append(f"M{x} {y + dy * size}V{y}H{x + dx * size}")
    return f"<path d='{' '.join(p)}' fill='none' stroke='{c}' stroke-width='1.2'/>"

DECOR = os.environ.get("DECOR", "halftone")

def diagram(s, t):
    """A small system diagram: ui -> api -> db, api -> agent -> llm / mcp.
    Orthogonal connectors; a rose pulse travels each one like data in flight."""
    NW, NH = 78, 30
    N = {"ui": (720, 104), "api": (860, 176), "db": (860, 292),
         "agent": (1010, 104), "llm": (1130, 176), "mcp": (1130, 292)}
    edges = [("ui", "api"), ("api", "db"), ("api", "agent"), ("agent", "llm"), ("agent", "mcp")]
    def port(n, side):
        x, y = N[n]
        return {"r": (x + NW, y + NH / 2), "l": (x, y + NH / 2), "b": (x + NW / 2, y + NH), "t": (x + NW / 2, y)}[side]
    for i, (a, b) in enumerate(edges):
        ax, ay = N[a]; bx, by = N[b]
        if abs(ax - bx) < 1:                                   # stacked: straight down
            (x1, y1), (x2, y2) = port(a, "b"), port(b, "t")
            pts = [(x1, y1), (x2, y2)]
        elif by > ay:                                           # down-right: right, then down into the top
            (x1, y1), (x2, y2) = port(a, "r"), port(b, "t")
            pts = [(x1, y1), (x2, y1), (x2, y2)]
        else:                                                   # up-right: right, then up into the bottom
            (x1, y1), (x2, y2) = port(a, "r"), port(b, "b")
            pts = [(x1, y1), (x2, y1), (x2, y2)]
        d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
        L = sum(abs(pts[k + 1][0] - pts[k][0]) + abs(pts[k + 1][1] - pts[k][1]) for k in range(len(pts) - 1))
        s.raw(f"<path d='{d}' fill='none' stroke='{t['rule']}' stroke-width='1.2' class='fade' style='animation-delay:{.9 + .1 * i:.1f}s'/>")
        s.raw(f"<path d='{d}' fill='none' stroke='{t['rose']}' stroke-width='2' stroke-linecap='round' "
              f"stroke-dasharray='18 {L + 40:.0f}' class='flow' style='--l:{L:.0f};animation-delay:{1.4 + .55 * i:.2f}s'/>")
        s.raw(f"<circle cx='{x2:.1f}' cy='{y2:.1f}' r='2.6' fill='{t['rose']}'/>")
    for i, (n, (x, y)) in enumerate(N.items()):
        hot = n in ("agent", "llm")
        s.raw(f"<g class='rise' style='animation-delay:{.5 + .08 * i:.2f}s'>")
        s.raw(f"<rect x='{x}' y='{y}' width='{NW}' height='{NH}' rx='3' fill='{t['page']}' "
              f"stroke='{t['rose'] if hot else t['rule']}' stroke-width='1.2'/>")
        s.text(x + NW / 2, y + NH / 2 + 4, [("mono", n, None)], 11, t["roseText"] if hot else t["fg2"], anchor="middle", tracking=0.08)
        s.raw("</g>")

def topo(s, t, cx, cy):
    """Contour lines — a nod to the Aburrá Valley ridges around Envigado."""
    import math
    s.raw("<g class='topo-a'>")
    for k in range(12):
        r = 22 + k * 15
        pts = []
        for a in range(0, 361, 6):
            th = math.radians(a)
            rr = r * (1 + .13 * math.sin(3 * th + k * .35) + .07 * math.sin(5 * th - k * .5) + .04 * math.cos(2 * th + k))
            pts.append(f"{cx + rr * math.cos(th) * 1.2:.1f} {cy + rr * math.sin(th) * .82:.1f}")
        major = k % 4 == 0
        col = t["rose"] if major else t["rule"]
        op = (.9 if major else .75) * (1 - k / 15)
        s.raw(f"<path d='M{' L'.join(pts)}Z' fill='none' stroke='{col}' stroke-width='{1.3 if major else 1}' opacity='{op:.2f}'/>")
    s.raw(f"<circle cx='{cx}' cy='{cy}' r='3' fill='{t['rose']}'/>")
    s.raw("</g>")

def dots(s, t, x0, x1, y0, y1):
    """A dot field with a rose wave passing through it, like a signal."""
    import math
    step = 16; cx, cy = (x0 + x1) / 2 + 40, (y0 + y1) / 2
    for gx in range(x0, x1 + 1, step):
        for gy in range(y0, y1 + 1, step):
            dx, dy = (gx - cx) / (x1 - x0) * 2, (gy - cy) / (y1 - y0) * 2
            d = math.hypot(dx * 1.1, dy)
            if d > 1.05: continue
            r = 1.1 + 1.5 * max(0, 1 - d)
            delay = (gx - x0) / (x1 - x0) * 2.2 + d * .6
            s.raw(f"<circle cx='{gx}' cy='{gy}' r='{r:.2f}' fill='{t['rose'] if d < .55 else t['fg3']}' "
                  f"class='wave' style='animation-delay:{delay:.2f}s'/>")

def ripple(s, t, x0, x1, y0, y1):
    """Concentric pulses leaving one point, like a drop on still water."""
    import math
    step = 16; cx, cy = (x0 + x1) / 2 + 30, (y0 + y1) / 2
    R = min(x1 - x0, (y1 - y0) * 1.9) / 2
    for gx in range(x0, x1 + 1, step):
        for gy in range(y0, y1 + 1, step):
            d = math.hypot((gx - cx) / 1.25, gy - cy) / (R / 1.25)
            if d > 1: continue
            r = 1 + 1.6 * (1 - d) ** .7
            ring = abs(math.sin(d * 9)) > .8
            fill = t["rose"] if ring and d < .8 else t["fg3"]
            s.raw(f"<circle cx='{gx}' cy='{gy}' r='{r:.2f}' fill='{fill}' class='wave' style='animation-delay:{d * 2.6:.2f}s'/>")
    s.raw(f"<circle cx='{cx:.0f}' cy='{cy:.0f}' r='3.4' fill='{t['rose']}'/>")

MONO = {"V": ["X...X", "X...X", "X...X", "X...X", ".X.X.", ".X.X.", "..X.."],
        "O": [".XXX.", "X...X", "X...X", "X...X", "X...X", "X...X", ".XXX."]}

def mono(s, t, x0, x1, y0, y1):
    """The VO monogram set in the dot field, like an LED sign; a glint runs across it."""
    step = 16; cell = 2                                   # one bitmap pixel = 2x2 dots
    cols = (5 + 1 + 5) * cell; rows = 7 * cell
    gx0 = x0 + ((x1 - x0) // step - cols) // 2 * step + 24
    gy0 = y0 + ((y1 - y0) // step - rows) // 2 * step + 8
    lit = set()
    for li, ch in enumerate("VO"):
        for r, line in enumerate(MONO[ch]):
            for c, px in enumerate(line):
                if px == "X":
                    for a in range(cell):
                        for b in range(cell):
                            lit.add(((li * 6 + c) * cell + a, r * cell + b))
    for i, gx in enumerate(range(x0, x1 + 1, step)):
        for j, gy in enumerate(range(y0, y1 + 1, step)):
            ci, cj = (gx - gx0) // step, (gy - gy0) // step
            on = (ci, cj) in lit and gx >= gx0 and gy >= gy0
            delay = (gx - x0) / (x1 - x0) * 1.8
            if on:
                s.raw(f"<circle cx='{gx}' cy='{gy}' r='3.1' fill='{t['rose']}' class='glint' style='animation-delay:{delay:.2f}s'/>")
            else:
                s.raw(f"<circle cx='{gx}' cy='{gy}' r='1.1' fill='{t['fg4']}' opacity='.7'/>")

def halftone(s, t, x0, x1, y0, y1):
    """A print halftone growing along the diagonal, with a scan line sweeping it."""
    import math
    step = 14
    for gx in range(x0, x1 + 1, step):
        for gy in range(y0, y1 + 1, step):
            u = (gx - x0) / (x1 - x0); v = (gy - y0) / (y1 - y0)
            k = (u * .75 + (1 - v) * .45) / 1.2 + .08 * math.sin(u * 7 + v * 5)
            if k < .12: continue
            r = .6 + 3.6 * min(1, k) ** 1.6
            s.raw(f"<circle cx='{gx}' cy='{gy}' r='{r:.2f}' fill='{t['fg3']}' class='scan' style='animation-delay:{u * 2.4:.2f}s'/>")

def ridge(s, t, x0, x1, y0, y1):
    """Rows of dots lifted by mountain profiles — Unknown Pleasures, by way of the Aburrá Valley."""
    import math, random
    rnd = random.Random(1131)
    rows = 12; step = 9
    for ri in range(rows):
        base = y0 + 84 + ri * (y1 - y0 - 84) / (rows - 1)
        peaks = [(rnd.uniform(.3, .7), rnd.uniform(.04, .12), rnd.uniform(.4, 1)) for _ in range(4)]
        for gx in range(x0, x1 + 1, step):
            u = (gx - x0) / (x1 - x0)
            env = math.exp(-((u - .52) / .22) ** 2)                       # the valley sits mid-canvas
            h = sum(a * math.exp(-((u - c) / w) ** 2) for c, w, a in peaks) * env
            h += .04 * math.sin(u * 40 + ri) * env
            y = base - h * 44
            fill = t["rose"] if h > .45 else t["fg3"]
            r = 1.1 + 1.1 * min(1, h * 1.5)
            s.raw(f"<circle cx='{gx}' cy='{y:.1f}' r='{r:.2f}' fill='{fill}' class='wave' style='animation-delay:{u * 2 + ri * .12:.2f}s'/>")

def subtle(s, t, start):
    """Quiet pass over a dot pattern: static, smaller dots, lower contrast,
    rose kept as an accent rather than a fill."""
    import re
    out = []
    for el in s.body[start:]:
        el = re.sub(r" class='(wave|glint|scan)' style='animation-delay:[0-9.]+s'", "", el)
        el = re.sub(r"r='([0-9.]+)'", lambda m: f"r='{float(m.group(1)) * .72:.2f}'", el)
        out.append(el)
    s.body[start:] = [f"<g opacity='{.42 if t is THEMES['dark'] else .5}'>"] + out + ["</g>"]

# ---------------------------------------------------------------- banner
def banner(theme):
    t = THEMES[theme]; W, H = 1280, 456; X = 72
    s = Svg(W, H, "Victor Olave — Software is just opinions, encoded. I try to encode good ones.")
    s.raw(defs(t, W, H, "k"))
    s.raw(f"<rect width='{W}' height='{H}' fill='{t['page']}'/>")
    s.raw("<g mask='url(#kmx)'><g mask='url(#kmy)'>")
    s.raw(f"<g mask='url(#km)'><rect width='{W}' height='{H}' fill='url(#kg)'/><rect width='{W}' height='{H}' fill='url(#kG)'/></g>")
    if DECOR == "blur":
        s.raw(f"<circle class='drift' cx='990' cy='215' r='235' fill='url(#kb)' opacity='{t['blobOpacity']}'/>")
        s.raw(f"<circle class='drift2' cx='770' cy='300' r='150' fill='url(#kb2)' opacity='{t['blobOpacity'] * .7}'/>")
    elif DECOR == "topo":
        topo(s, t, cx=985, cy=212)
    s.raw(f"<rect width='{W}' height='{H}' filter='url(#kn)' opacity='{t['grain']}'/>")
    s.raw("</g></g>")
    if DECOR == "diagram":
        diagram(s, t)
    elif DECOR in ("dots", "ripple", "mono", "halftone", "ridge"):
        start = len(s.body)
        globals()[DECOR](s, t, x0=690, x1=1208, y0=96, y1=340)
        subtle(s, t, start)
    s.raw(marks(t, W, H))

    # sheet marks
    s.text(X, 58, [("mono", "VO / 00 — PROFILE", None)], 12, t["fg3"], tracking=0.1, cls="fade")
    s.text(W - X, 58, [("mono", "6.17° N  75.58° W  ·  GMT-5", None)], 12, t["fg3"], anchor="end", tracking=0.1, cls="fade")

    # eyebrow
    ey = 138
    s.raw(f"<line x1='{X}' y1='{ey - 4.5}' x2='{X + 32}' y2='{ey - 4.5}' stroke='{t['rose']}' stroke-width='1.2' "
          f"stroke-dasharray='32' class='draw' style='--l:32;animation-delay:.1s'/>")
    s.text(X + 46, ey, [("sansm", "Senior fullstack engineer  ·  AI product engineering", None)], 13,
           t["roseText"], tracking=0.22, upper=True, cls="rise", )
    s.body[-1] = s.body[-1].replace("class='rise'", "class='rise' style='animation-delay:.15s'")

    # name
    ny, ns = 246, 112
    s.text(X - 4, ny, [("serif", "Victor ", None), ("italic", "Olave", None), ("serif", ".", t["rose"])], ns, t["fg"], cls="rise")
    s.body[-1] = s.body[-1].replace("class='rise'", "class='rise' style='animation-delay:.3s'")

    # manifesto
    my, ms = 310, 30
    runs = [("serif", "Software ", None), ("italic", "is just", None), ("serif", " opinions, ", None), ("serif", "encoded.", t["roseText"])]
    s.text(X, my, runs, ms, t["fg2"], cls="rise")
    s.body[-1] = s.body[-1].replace("class='rise'", "class='rise' style='animation-delay:.55s'")
    pre = width("serif", "Software ", ms) + width("italic", "is just", ms) + width("serif", " opinions, ", ms)
    enc = width("serif", "encoded.", ms)
    ux = X + pre
    s.raw(f"<line x1='{ux:.1f}' y1='{my + 9}' x2='{ux + enc - 6:.1f}' y2='{my + 9}' stroke='{t['rose']}' stroke-width='1.6' "
          f"stroke-dasharray='{enc:.0f}' class='draw' style='--l:{enc:.0f};animation-delay:1.3s'/>")
    runs2 = [("serif", "I try ", None), ("italic", "to encode", None), ("serif", " good ", None), ("serif", "ones.", None)]
    s.text(X, my + 42, runs2, ms, t["fg3"], cls="rise")
    s.body[-1] = s.body[-1].replace("class='rise'", "class='rise' style='animation-delay:.75s'")
    cx = X + sum(width(k, tx, ms) for k, tx, _ in runs2) + 6
    s.raw(f"<rect x='{cx:.1f}' y='{my + 42 - 22}' width='3' height='26' fill='{t['rose']}' class='blink'/>")

    # footer rule
    fy = 420
    s.raw(f"<line x1='{X}' y1='{fy - 22}' x2='{W - X}' y2='{fy - 22}' stroke='{t['rule']}' stroke-width='1' "
          f"stroke-dasharray='{W - 2 * X}' class='draw' style='--l:{W - 2 * X};animation-delay:.9s'/>")
    s.text(X, fy, [("mono", "victorolave.dev", t["fg2"])], 12, t["fg3"], tracking=0.08, cls="fade")
    s.text(W - X, fy, [("mono", "9 yrs end-to-end  ·  React  ·  TypeScript  ·  Node  ·  NestJS  ·  LLMs & MCP", None)],
           12, t["fg3"], anchor="end", tracking=0.08, cls="fade")
    for i in (-2, -1):
        s.body[i] = s.body[i].replace("class='fade'", "class='fade' style='animation-delay:1.1s'")
    return s.render(BASE_CSS)

# ---------------------------------------------------------------- cards
PROJECTS = [
    dict(slug="pactjoy", n="01", name=[("serif", "Pact"), ("italic", "Joy")],
         status=("Pre-alpha", "warn", False),
         desc="A social habits app where everyone pursues different goals and competes on a fair, shared score.",
         stack="React · Vite · PWA · Supabase · Hexagonal"),
    dict(slug="plinto", n="02", name=[("serif", "Plinto")],
         status=("Self-hosted · AGPL-3.0", "info", False),
         desc="Household finance without the spreadsheet: accounts, recurring rules, debts and credit cards, for one or more households.",
         stack="NestJS · Next.js · PostgreSQL · Docker"),
    dict(slug="acopio-colombia", n="03", name=[("serif", "Acopio "), ("italic", "Colombia")],
         status=("Live · Civic tech", "ok", True),
         desc="Nearest relief drop-off points after the 10 August 2026 earthquake. Every centre shows what it takes, and its source.",
         stack="Next.js · Supabase · MapLibre · Open data"),
    dict(slug="dadiva", n="04", name=[("italic", "Dádiva")],
         status=("Live", "ok", True),
         desc="Secret Santa with Bible-verse promise cards. The draw runs server-side, hidden by RLS even from the organiser.",
         stack="React · Tailwind · Supabase · Clean architecture"),
]

def wrap(key, text, size, maxw):
    lines, cur = [], ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if width(key, cand, size) <= maxw: cur = cand
        else: lines.append(cur); cur = word
    return lines + [cur]

def card(p, theme):
    t = THEMES[theme]; W, H = 620, 330; X = 40
    name = "".join(tx for _, tx in p["name"])
    s = Svg(W, H, f"{name} — {p['desc']}")
    gid = f"c{p['n']}"
    s.raw(defs(t, W, H, gid))
    # Same sheet treatment as the banner: GitHub canvas, edge-faded grid,
    # glow and grain, framed only by the corner marks.
    s.raw(f"<rect width='{W}' height='{H}' fill='{t['page']}'/>")
    s.raw(f"<g mask='url(#{gid}mx)'><g mask='url(#{gid}my)'>")
    s.raw(f"<g mask='url(#{gid}m)'><rect width='{W}' height='{H}' fill='url(#{gid}g)'/><rect width='{W}' height='{H}' fill='url(#{gid}G)'/></g>")
    s.raw(f"<rect width='{W}' height='{H}' filter='url(#{gid}n)' opacity='{t['grain']}'/>")
    s.raw("</g></g>")
    start = len(s.body)
    halftone(s, t, x0=372, x1=W - 40, y0=80, y1=160)
    subtle(s, t, start)
    s.raw(marks(t, W, H, inset=14, size=12))

    s.text(X, 56, [("mono", f"{p['n']} / 04", None)], 12, t["fg3"], tracking=0.1)
    label, tone, live = p["status"]
    lw = width("mono", label.upper(), 11, 0.12)
    dx = W - X - lw - 16
    s.raw(f"<circle cx='{dx:.1f}' cy='52' r='3.5' fill='{t[tone]}'/>")
    s.text(W - X, 56, [("mono", label, None)], 11, t[tone], anchor="end", tracking=0.12, upper=True)

    s.raw(f"<line x1='{X}' y1='96' x2='{X + 28}' y2='96' stroke='{t['rose']}' stroke-width='2'/>")
    s.text(X - 2, 152, [(k, tx, None) for k, tx in p["name"]], 50, t["fg"])

    lines = wrap("sans", p["desc"], 17, W - 2 * X)
    for i, ln in enumerate(lines[:3]):
        s.text(X, 196 + i * 26, [("sans", ln, None)], 17, t["fg2"])

    s.raw(f"<line x1='{X}' y1='{H - 64}' x2='{W - X}' y2='{H - 64}' stroke='{t['rule']}' stroke-width='1'/>")
    s.text(X, H - 34, [("mono", p["stack"], None)], 12, t["fg3"], tracking=0.04)
    s.raw(f"<g class='nudge'>")
    s.text(W - X, H - 32, [("mono", "view repo →", None)], 12, t["roseText"], anchor="end", tracking=0.06)
    s.raw("</g>")
    return s.render(BASE_CSS)

# ---------------------------------------------------------------- stack map
# Mirrors the "Skills" section of victorolave.dev (src/i18n/en.ts) verbatim.
STACK = [
    ("AI engineering", ["LLM integration (Claude, OpenAI)", "Agentic systems & MCP", "RAG architectures", "Prompt engineering", "Responsible AI"]),
    ("Frontend", ["React", "TypeScript", "Next.js", "Angular", "Astro", "Tailwind CSS"]),
    ("Animation & 3D", ["Motion One", "GSAP", "Three.js", "WebGL", "Lenis", "Canvas"]),
    ("Backend", ["Node.js", "NestJS", "Express", "REST", "GraphQL", "WebSockets"]),
    ("Databases", ["PostgreSQL", "MongoDB", "Redis", "Prisma", "Drizzle"]),
    ("DevOps & Tools", ["Docker", "GitHub Actions", "Vercel", "Railway", "AWS", "Git"]),
    ("System & Security", ["OAuth / JWT", "Hexagonal Arch.", "Testing", "CI/CD", "Observability"]),
    ("Design", ["Figma", "Design Systems", "Atomic Design", "Accessibility"]),
]

def stack(theme):
    t = THEMES[theme]; W = 1280; M = 48; G = 14; COLS = 4
    PW = (W - 2 * M - (COLS - 1) * G) / COLS; PH = 250; TOP = 124
    H = TOP + 2 * PH + G + M
    total = sum(len(i) for _, i in STACK)
    s = Svg(W, H, "Stack — " + "; ".join(f"{c}: {', '.join(i)}" for c, i in STACK))
    s.raw(defs(t, W, H, "s"))
    s.raw(f"<rect width='{W}' height='{H}' fill='{t['page']}'/>")
    s.raw("<g mask='url(#smx)'><g mask='url(#smy)'>")
    s.raw(f"<g mask='url(#sm)' opacity='.7'><rect width='{W}' height='{H}' fill='url(#sg)'/></g>")
    s.raw(f"<rect width='{W}' height='{H}' filter='url(#sn)' opacity='{t['grain']}'/>")
    s.raw("</g></g>")
    s.raw(marks(t, W, H))

    s.raw(f"<line x1='{M}' y1='{58 - 4.5}' x2='{M + 32}' y2='{58 - 4.5}' stroke='{t['rose']}' stroke-width='1.2'/>")
    s.text(M + 46, 58, [("sansm", "Stack", None)], 13, t["roseText"], tracking=0.22, upper=True)
    s.text(M - 2, 100, [("serif", "What I ", None), ("italic", "reach for", None), ("serif", ".", t["rose"])], 38, t["fg"])
    s.text(W - M, 58, [("mono", f"{len(STACK):02d} layers  ·  {total} tools", None)], 12, t["fg3"], anchor="end", tracking=0.1)
    s.text(W - M, 100, [("mono", "Same list as victorolave.dev/#skills", None)], 12, t["fg4"], anchor="end", tracking=0.06)

    for i, (cat, items) in enumerate(STACK):
        r, c = divmod(i, COLS)
        x = M + c * (PW + G); y = TOP + r * (PH + G)
        hero = i == 0
        delay = f"animation-delay:{.08 * i:.2f}s"
        s.raw(f"<g class='rise' style='{delay}'>")
        s.raw(f"<rect x='{x + .5:.1f}' y='{y + .5:.1f}' width='{PW - 1:.1f}' height='{PH - 1}' rx='6' "
              f"fill='{t['surface']}' stroke='{t['rose'] if hero else t['rule']}' stroke-opacity='{.7 if hero else 1}'/>")
        px = x + 22
        s.text(px, y + 34, [("mono", f"{i + 1:02d}", None)], 11, t["roseText"] if hero else t["fg3"], tracking=0.1)
        if hero:
            s.text(x + PW - 22, y + 34, [("mono", "Current focus", None)], 10, t["roseText"], anchor="end", tracking=0.12, upper=True)
        s.text(px, y + 72, [("italic", cat, None)], 25, t["fg"])
        s.raw(f"<line x1='{px}' y1='{y + 90}' x2='{x + PW - 22:.1f}' y2='{y + 90}' stroke='{t['rule']}'/>")
        size = 14
        while max(width("sans", it, size) for it in items) > PW - 44 - 14 and size > 11:
            size -= .5
        for j, it in enumerate(items):
            iy = y + 120 + j * 23
            s.raw(f"<rect x='{px}' y='{iy - 5}' width='5' height='1.4' fill='{t['rose']}'/>")
            s.text(px + 14, iy, [("sans", it, None)], size, t["fg2"])
        s.raw("</g>")
    return s.render(BASE_CSS)

for theme in THEMES:
    open(f"{OUT}/stack-{theme}.svg", "w").write(stack(theme))
    open(f"{OUT}/banner-{theme}.svg", "w").write(banner(theme))
    for p in PROJECTS:
        open(f"{OUT}/card-{p['slug']}-{theme}.svg", "w").write(card(p, theme))
for f in sorted(os.listdir(OUT)):
    print(f"{os.path.getsize(os.path.join(OUT, f)) / 1024:7.1f} KB  {f}")
