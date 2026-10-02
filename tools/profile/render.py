"""Render data/stats.json into SVG slices under assets/. Same data -> byte-identical output."""

import base64
import io
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
FONTS = Path(__file__).parent / "fonts"

# Brand: docs/brand-style-guide.md in Vets-Who-Code/vets-who-code-app
NAVY, RED, WHITE = "#091F40", "#C5203E", "#FFFFFF"
W = 840  # slice width; every slice height is a multiple of 40
RAIL = 14  # keyline inset from the slice side

FONT_FILES = {"stencil": "AllertaStencil-Regular.ttf", "type": "SpecialElite-Regular.ttf"}


def font_face(name, text):
    """@font-face rule with a woff2 subset holding only the glyphs in text."""
    font = TTFont(FONTS / FONT_FILES[name], recalcTimestamp=False)
    opts = Options()
    opts.flavor = "woff2"
    opts.drop_tables += ["FFTM"]
    sub = Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:{name};src:url(data:font/woff2;base64,{b64})}}"


def advances(name, text, size):
    """Per-character advance widths in px (no kerning; each char is drawn on its own)."""
    font = TTFont(FONTS / FONT_FILES[name])
    cmap, hmtx, upem = font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm
    return [hmtx[cmap[ord(c)]][0] * size / upem for c in text]


def slice_svg(h, body, texts=None, css="", top=False, bottom=False):
    """One horizontal slice of the brief page: navy, topo grid, red rails. Only the
    header draws the top edge and only the footer draws the bottom edge."""
    texts = texts or {}
    faces = "".join(font_face(n, t) for n, t in sorted(texts.items()))
    y0 = RAIL if top else 0
    y1 = h - RAIL if bottom else h
    x0, x1 = RAIL, W - RAIL
    edges = ""
    if top:
        edges += f'<path d="M{x0} {y1}V{y0 + 10}q0-10 10-10H{x1 - 10}q10 0 10 10V{y1}" class="rail"/>'
    if bottom:
        edges += f'<path d="M{x0} {y0}V{y1 - 10}q0 10 10 10H{x1 - 10}q10 0 10-10V{y0}" class="rail"/>'
    if not (top or bottom):
        edges = f'<path d="M{x0} 0V{h}M{x1} 0V{h}" class="rail"/>'
    inner = f'<path d="M{x0 + 7} {y0 + (8 if top else 0)}V{y1 - (8 if bottom else 0)}M{x1 - 7} {y0 + (8 if top else 0)}V{y1 - (8 if bottom else 0)}" class="rail2"/>'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}">
<style>{faces}
.rail{{fill:none;stroke:{RED};stroke-width:3}}
.rail2{{fill:none;stroke:{RED};stroke-width:1;opacity:.55}}
.stencil{{font-family:stencil}}.type{{font-family:type}}
{css}</style>
<defs>
<!-- lines sit inside pixel rows, never on a slice edge -->
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
<path d="M0 20.5H40M20.5 0V40" fill="none" stroke="{WHITE}" stroke-opacity=".07"/>
<path d="M0 0.5H40M0.5 0V40" fill="none" stroke="{WHITE}" stroke-opacity=".03"/>
</pattern>
</defs>
<rect width="{W}" height="{h}" fill="{NAVY}"/>
<rect width="{W}" height="{h}" fill="url(#grid)"/>
{edges}{inner}
{body}
</svg>
"""


def header():
    h = 320
    title, size = "MISSION BRIEF", 30
    adv = advances("type", title, size)
    x = (W - sum(adv)) / 2
    start, step = 0.6, 0.14
    chars, xs = [], []
    for i, (c, a) in enumerate(zip(title, adv)):
        xs.append(x)
        if c != " ":
            chars.append(f'<text x="{x:.1f}" y="70" class="type ch" style="animation-delay:{start + i * step:.2f}s">{c}</text>')
        x += a
    xs.append(x)
    n = len(title)
    frames = "".join(f"{i / n * 100:.2f}%{{transform:translateX({xs[i] - xs[0]:.1f}px)}}" for i in range(n + 1))
    css = f"""
.ch{{font-size:{size}px;fill:{WHITE};opacity:0;animation:on .01s {start}s forwards}}
@keyframes on{{to{{opacity:1}}}}
.cursor{{fill:{RED};animation:type {n * step:.2f}s steps(1,end) {start}s forwards,blink 1s steps(1,end) infinite}}
@keyframes type{{{frames}}}
@keyframes blink{{50%{{opacity:0}}}}
.tag{{fill:{NAVY}}}
.emb{{fill:#AEB6C0}}"""

    # Dog tag: 440x190, hole on the left, beaded chain running up off the page.
    tx, ty, tw, th = 200, 106, 440, 190
    lines = [("JEROME HARDAWAY", 32), ("@MAVERICK", 22), ("USAF VETERAN", 22), ("FOUNDER, VETS WHO CODE", 22)]
    text, y = "", ty + 58
    for s, sz in lines:
        for cls, dx, dy in (("emb", 1, 1), ("tag", 0, 0)):  # gray offset shadow = raised/embossed
            text += f'<text x="{tx + 80 + dx}" y="{y + dy}" class="stencil {cls}" font-size="{sz}">{s}</text>'
        y += 40 if sz > 22 else 34
    cy = ty + th / 2
    body = f"""<g>{"".join(chars)}<rect class="cursor" x="{xs[0]:.1f}" y="46" width="3" height="30"/></g>
<path d="M{tx + 34} {cy - 12}C{tx - 40} {cy - 80} {tx - 60} 40 {tx - 120} 0" fill="none" stroke="#DEE2E6" stroke-width="5" stroke-linecap="round" stroke-dasharray="0 8"/>
<rect x="{tx - 6}" y="{ty - 6}" width="{tw + 12}" height="{th + 12}" rx="46" fill="{WHITE}" opacity=".12"/>
<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="40" fill="{WHITE}" stroke="#DEE2E6" stroke-width="2"/>
<rect x="{tx + 10}" y="{ty + 10}" width="{tw - 20}" height="{th - 20}" rx="32" fill="none" stroke="#DEE2E6" stroke-width="2"/>
<circle cx="{tx + 34}" cy="{cy}" r="10" fill="{NAVY}" stroke="#DEE2E6" stroke-width="2"/>
{text}"""
    used = "".join(s for s, _ in lines)
    return slice_svg(h, body, {"type": title.replace(" ", ""), "stencil": used}, css, top=True)


def footer():
    h = 360
    gif = base64.b64encode((ASSETS / "vwc.gif").read_bytes()).decode()
    gw, gh = 280, 210  # 800x600 scaled proportionally
    label = "END OF BRIEF"
    body = f"""<path d="M{RAIL + 40} 40H{W - RAIL - 40}" stroke="{RED}" stroke-width="2"/>
<text x="{W / 2}" y="90" text-anchor="middle" class="stencil" font-size="30" fill="{WHITE}" letter-spacing="4">{label}</text>
<rect x="{(W - gw) / 2 - 10}" y="100" width="{gw + 20}" height="{gh + 20}" fill="{WHITE}" stroke="{RED}" stroke-width="2"/>
<image x="{(W - gw) / 2}" y="110" width="{gw}" height="{gh}" href="data:image/gif;base64,{gif}"/>"""
    return slice_svg(h, body, {"stencil": label.replace(" ", "")}, bottom=True)


def main():
    ASSETS.mkdir(exist_ok=True)
    slices = {"header.svg": header(), "spacer.svg": slice_svg(120, ""), "footer.svg": footer()}
    for name, svg in slices.items():
        (ASSETS / name).write_text(svg)


if __name__ == "__main__":
    main()
