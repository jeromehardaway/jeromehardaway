"""Render data/stats.json into SVG slices under assets/. Same data -> byte-identical output."""

import base64
import io
import json
import math
import random
import re
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
FONTS = Path(__file__).parent / "fonts"
STATS = Path(__file__).parent / "data" / "stats.json"

# Brand: docs/brand-style-guide.md in Vets-Who-Code/vets-who-code-app
NAVY, RED, WHITE = "#091F40", "#C5203E", "#FFFFFF"
SILVER = "#DEE2E6"
W = 840  # page width; every slice height is a multiple of 40
RAIL = 14  # keyline inset from the page side

FONT_FILES = {"stencil": "AllertaStencil-Regular.ttf", "type": "SpecialElite-Regular.ttf"}

LINKS = [  # (file, label, url)
    ("link-vwc", "VETSWHOCODE.IO", "https://vetswhocode.io"),
    ("link-github", "VWC GITHUB", "https://github.com/Vets-Who-Code"),
    ("link-linkedin", "LINKEDIN", "https://www.linkedin.com/in/jeromehardaway"),
    ("link-youtube", "YOUTUBE", "https://www.youtube.com/@vetswhocode"),
    ("link-portfolio", "PORTFOLIO", "https://jerome.codes"),
]
N_OPS = 6  # even, so every card row is two half-width cards


@cache
def font(name):
    return TTFont(FONTS / FONT_FILES[name], recalcTimestamp=False)


def font_face(name, text):
    """@font-face rule with a woff2 subset holding only the glyphs in text."""
    f = TTFont(FONTS / FONT_FILES[name], recalcTimestamp=False)
    opts = Options()
    opts.flavor = "woff2"
    opts.drop_tables += ["FFTM"]
    sub = Subsetter(opts)
    sub.populate(text=text)
    sub.subset(f)
    buf = io.BytesIO()
    f.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"@font-face{{font-family:{name};src:url(data:font/woff2;base64,{b64})}}"


def advances(name, text, size):
    """Per-character advance widths in px, no kerning."""
    f = font(name)
    cmap, hmtx, upem = f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm
    return [hmtx[cmap[ord(c)]][0] * size / upem if ord(c) in cmap else size * 0.6 for c in text]


def has_glyphs(name, text):
    cmap = font(name).getBestCmap()
    return "".join(c for c in text if ord(c) in cmap)


def wrap(name, text, size, width, max_lines):
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if sum(advances(name, trial, size)) <= width:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = word
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip(".,;:") + "..."
    return lines


def fit(name, text, size, width):
    """Largest font size <= size that fits text in width."""
    return min(size, size * width / sum(advances(name, text, size)))


def text(x, y, s, font_name, size, fill=NAVY, extra=""):
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{font_name}" font-size="{size:.1f}" fill="{fill}"{extra}>{escape(s)}</text>'


TEXT_RE = re.compile(r'<text[^>]*class="(stencil|type)[^"]*"[^>]*>(.*?)</text>')


def slice_svg(h, body, css="", w=W, left=True, right=True, top=False, bottom=False):
    """One piece of the brief page: navy, topo grid, red rails. Only the header draws
    the top edge and only the footer draws the bottom edge. Half-width pieces draw
    only the rail on their own side. Fonts are subset to the text the body uses."""
    used = {}
    for name, s in TEXT_RE.findall(body):
        used[name] = used.get(name, "") + s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    faces = "".join(font_face(n, t) for n, t in sorted(used.items()))
    y0, y1 = (RAIL if top else 0), (h - RAIL if bottom else h)
    x0, x1 = RAIL, w - RAIL
    if top:
        edges = f'<path d="M{x0} {y1}V{y0 + 10}q0-10 10-10H{x1 - 10}q10 0 10 10V{y1}" class="rail"/>'
    elif bottom:
        edges = f'<path d="M{x0} {y0}V{y1 - 10}q0 10 10 10H{x1 - 10}q10 0 10-10V{y0}" class="rail"/>'
    else:
        edges = (f'<path d="M{x0} 0V{h}" class="rail"/>' if left else "") + (
            f'<path d="M{x1} 0V{h}" class="rail"/>' if right else "")
    i0, i1 = y0 + (8 if top else 0), y1 - (8 if bottom else 0)
    inner = (f'<path d="M{x0 + 7} {i0}V{i1}" class="rail2"/>' if left else "") + (
        f'<path d="M{x1 - 7} {i0}V{i1}" class="rail2"/>' if right else "")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<style>{faces}
.rail{{fill:none;stroke:{RED};stroke-width:3}}
.rail2{{fill:none;stroke:{RED};stroke-width:1;opacity:.55}}
.stencil{{font-family:stencil}}.type{{font-family:type}}
{css}</style>
<defs>
<!-- grid lines sit inside pixel rows, never on a slice edge -->
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
<path d="M0 20.5H40M20.5 0V40" fill="none" stroke="{WHITE}" stroke-opacity=".07"/>
<path d="M0 0.5H40M0.5 0V40" fill="none" stroke="{WHITE}" stroke-opacity=".03"/>
</pattern>
<pattern id="dots" width="6" height="6" patternUnits="userSpaceOnUse">
<circle cx="3" cy="3" r="1.1" fill="{NAVY}" opacity=".18"/>
</pattern>
</defs>
<rect width="{w}" height="{h}" fill="{NAVY}"/>
<rect width="{w}" height="{h}" fill="url(#grid)"/>
{edges}{inner}
{body}
</svg>
"""


def caption(x, y, title, sub=""):
    """White caption box: red tab, stencil title, typewriter subtitle, halftone tail."""
    size = 22
    tw = sum(advances("stencil", title, size))
    sw = sum(advances("type", sub, 13)) if sub else 0
    w = max(tw, sw) + 44 + 60
    return f"""<rect x="{x}" y="{y}" width="{w:.0f}" height="{56 if sub else 40}" fill="{WHITE}"/>
<rect x="{x + w - 70:.0f}" y="{y}" width="70" height="{56 if sub else 40}" fill="url(#dots)"/>
<rect x="{x}" y="{y}" width="8" height="{56 if sub else 40}" fill="{RED}"/>
{text(x + 22, y + 29, title, "stencil", size, extra=' letter-spacing="2"')}
{text(x + 22, y + 48, sub, "type", 13) if sub else ""}"""


def data_end(stats):
    """The last day in the data stands in for 'today', so output never depends on the clock."""
    return date.fromisoformat(max(stats["contributions"]))


# ---------- header / footer ----------

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
@keyframes blink{{50%{{opacity:0}}}}"""

    # Dog tag: hole on the left, beaded chain running up off the page.
    tx, ty, tw, th = 200, 106, 440, 190
    lines = [("JEROME HARDAWAY", 32), ("@MAVERICK", 22), ("USAF VETERAN", 22), ("FOUNDER, VETS WHO CODE", 22)]
    tag, y = "", ty + 58
    for s, sz in lines:
        tag += text(tx + 81, y + 1, s, "stencil", sz, "#AEB6C0")  # gray offset shadow = embossed
        tag += text(tx + 80, y, s, "stencil", sz)
        y += 40 if sz > 22 else 34
    cy = ty + th / 2
    body = f"""<g>{"".join(chars)}<rect class="cursor" x="{xs[0]:.1f}" y="46" width="3" height="30"/></g>
<path d="M{tx + 34} {cy - 12}C{tx - 40} {cy - 80} {tx - 60} 40 {tx - 120} 0" fill="none" stroke="{SILVER}" stroke-width="5" stroke-linecap="round" stroke-dasharray="0 8"/>
<rect x="{tx - 6}" y="{ty - 6}" width="{tw + 12}" height="{th + 12}" rx="46" fill="{WHITE}" opacity=".12"/>
<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="40" fill="{WHITE}" stroke="{SILVER}" stroke-width="2"/>
<rect x="{tx + 10}" y="{ty + 10}" width="{tw - 20}" height="{th - 20}" rx="32" fill="none" stroke="{SILVER}" stroke-width="2"/>
<circle cx="{tx + 34}" cy="{cy}" r="10" fill="{NAVY}" stroke="{SILVER}" stroke-width="2"/>
{tag}"""
    return slice_svg(h, body, css, top=True)


def footer():
    h = 360
    gif = base64.b64encode((ASSETS / "vwc.gif").read_bytes()).decode()
    gw, gh = 280, 210  # 800x600 scaled proportionally
    body = f"""<path d="M{RAIL + 40} 40H{W - RAIL - 40}" stroke="{RED}" stroke-width="2"/>
{text(W / 2, 90, "END OF BRIEF", "stencil", 30, WHITE, ' text-anchor="middle" letter-spacing="4"')}
<rect x="{(W - gw) / 2 - 10}" y="100" width="{gw + 20}" height="{gh + 20}" fill="{WHITE}" stroke="{RED}" stroke-width="2"/>
<image x="{(W - gw) / 2}" y="110" width="{gw}" height="{gh}" href="data:image/gif;base64,{gif}"/>"""
    return slice_svg(h, body, bottom=True)


# ---------- link buttons: one SVG each so each can sit in its own <a> ----------

def link_cells():
    """Widths of the 5 link cells: 140px buttons, 18px gaps, outer cells carry the rails."""
    bw, gap, edge = 140, 18, 34
    outer = edge + bw + gap // 2
    return bw, gap, edge, [outer] + [bw + gap] * 3 + [outer]


def links():
    bw, gap, edge, widths = link_cells()
    assert sum(widths) == W
    out = {}
    for i, ((name, label, _), w) in enumerate(zip(LINKS, widths)):
        x = edge if i == 0 else gap // 2
        size = fit("stencil", label, 15, bw - 24)
        body = f"""<rect x="{x}" y="20" width="{bw}" height="40" rx="4" fill="{WHITE}"/>
<rect x="{x}" y="20" width="6" height="40" rx="2" fill="{RED}"/>
{text(x + bw / 2 + 3, 46, label, "stencil", size, extra=' text-anchor="middle" letter-spacing="1"')}"""
        out[f"{name}.svg"] = slice_svg(80, body, w=w, left=i == 0, right=i == len(LINKS) - 1)
    return out


# ---------- service record: hash marks + ribbon rack ----------

# Original ribbon designs: left half (color, width) mirrored about the center. Each half = 46px.
N, R, Wh = NAVY, RED, WHITE
RIBBONS = [
    [(R, 8), (Wh, 4), (N, 34)],
    [(N, 10), (Wh, 3), (R, 3), (Wh, 3), (N, 27)],
    [(Wh, 6), (R, 14), (Wh, 4), (N, 22)],
    [(R, 4), (N, 16), (Wh, 2), (R, 24)],
    [(N, 6), (R, 6), (N, 6), (Wh, 28)],
    [(Wh, 4), (N, 4), (Wh, 4), (R, 34)],
    [(R, 16), (Wh, 2), (N, 2), (Wh, 2), (N, 24)],
]


def ribbon(x, y, stripes, h=26):
    out, cx = [], x
    for color, sw in stripes + stripes[::-1]:
        out.append(f'<rect x="{cx}" y="{y}" width="{sw}" height="{h}" fill="{color}"/>')
        cx += sw
    out.append(f'<rect x="{x}" y="{y}" width="{cx - x}" height="{h}" fill="none" stroke="{WHITE}" stroke-width="1.5"/>')
    return "".join(out)


def record(stats):
    end = data_end(stats)
    created = date.fromisoformat(stats["created_at"][:10])
    years = end.year - created.year - ((end.month, end.day) < (created.month, created.day))
    # One red hash mark per full year on GitHub, slanted like sleeve service stripes.
    marks = "".join(
        f'<path d="M{60 + i * 18} 132l20-40h9l-20 40z" fill="{RED}" stroke="{WHITE}" stroke-width="1.5"/>'
        for i in range(years))
    mx = 60 + years * 18 + 30
    stats_row = [
        (f"{stats['followers']:,}", "FOLLOWERS", ""),
        (f"{stats['stars']:,}", "TOTAL", "STARS"),
        (f"{stats['prs_merged']:,}", "PRS", "MERGED"),
        (f"{stats['contributions_this_year']:,}", "CONTRIBUTIONS", str(end.year)),
        (f"{stats['contributions_all_time']:,}", "CONTRIBUTIONS", "ALL TIME"),
        (f"{stats['streak_current']:,}", "CURRENT", "STREAK"),
        (f"{stats['streak_longest']:,}", "LONGEST", "STREAK"),
    ]
    rw, gap = 92, 14
    x0 = (W - (len(stats_row) * rw + (len(stats_row) - 1) * gap)) / 2
    rack = ""
    for i, ((value, l1, l2), stripes) in enumerate(zip(stats_row, RIBBONS)):
        x = x0 + i * (rw + gap)
        cx = x + rw / 2
        mid = ' text-anchor="middle"'
        rack += ribbon(x, 176, stripes)
        rack += text(cx, 228, value, "stencil", 22, WHITE, mid)
        rack += text(cx, 248, l1, "type", 11, SILVER, mid)
        if l2:
            rack += text(cx, 262, l2, "type", 11, SILVER, mid)
    body = f"""{caption(40, 20, "SERVICE RECORD")}
{marks}
{text(mx, 108, f"{years} YEARS ON GITHUB", "stencil", 20, WHITE, ' letter-spacing="1"')}
{text(mx, 130, f"ON DUTY SINCE {created.year}", "type", 14, SILVER)}
{rack}"""
    return slice_svg(280, body)


# ---------- Mission Log: isometric contribution city ----------

def city(stats):
    days = stats["contributions"]
    end = data_end(stats)
    first = end - timedelta(days=(end.weekday() + 1) % 7) - timedelta(weeks=52)  # Sunday, 53 weeks
    cells = []
    for w in range(53):
        for d in range(7):
            day = first + timedelta(weeks=w, days=d)
            if day <= end:
                cells.append((w, d, day.isoformat(), days.get(day.isoformat(), 0)))
    counts = sorted(c for *_, c in cells if c)
    top = max(counts, default=1)
    red_from = counts[int(len(counts) * 0.9)] if counts else top + 1  # top 10% days
    flags = {k for _, _, k, _ in sorted((c for c in cells if c[3]), key=lambda c: (-c[3], c[2]))[:5]}

    hw, hh = 12, 6  # half tile
    fw, fh = 10, 5  # half footprint
    ox, oy = (W - 60 * hw) / 2 + 7 * hw, 210
    lots, parts = [], []
    for w, d, key, c in sorted(cells, key=lambda c: (c[0] + c[1], c[0])):  # painter's: back to front
        cx, cy = ox + (w - d) * hw, oy + (w + d) * hh + hh
        if not c:
            lots.append(f"M{cx:g} {cy - fh:g}l{fw} {fh}l{-fw} {fh}l{-fw} {-fh}z")
            continue
        h = 8 + 110 * math.sqrt(c / top)
        roof = RED if c >= red_from else WHITE
        parts.append(
            f'<path d="M{cx - fw:g} {cy:g}l{fw} {fh}v{-h:.1f}l{-fw} {-fh}z" fill="{NAVY}"/>'
            f'<path d="M{cx:g} {cy + fh:g}l{fw} {-fh}v{-h:.1f}l{-fw} {fh}z" fill="#14305A"/>'
            f'<path d="M{cx - fw:g} {cy:g}l{fw} {fh}l{fw} {-fh}M{cx:g} {cy + fh:g}v{-h:.1f}" fill="none" class="edge"/>'
            f'<path d="M{cx:g} {cy - h - fh:.1f}l{fw} {fh}l{-fw} {fh}l{-fw} {-fh}z" fill="{roof}" class="edge"/>'
        )
        rng = random.Random(key)  # seeded per day: same data -> same windows
        windows = []
        for row in range(int((h - 6) // 7)):
            wy = cy - 5 - row * 7
            for t in (0.3, 0.65):
                if rng.random() < 0.4:
                    windows.append(f"M{cx - fw + t * fw:.1f} {wy + t * fh:.1f}l2 1")
                if rng.random() < 0.4:
                    windows.append(f"M{cx + t * fw:.1f} {wy + fh - t * fh:.1f}l2 -1")
        if windows:  # drawn with their own building so nearer buildings cover them
            parts.append(f'<path d="{"".join(windows)}" class="win"/>')
        if key in flags:
            ty = cy - h
            parts.append(
                f'<path d="M{cx:g} {ty:.1f}v-18" stroke="{WHITE}" stroke-width="1.2"/>'
                f'<path d="M{cx:g} {ty - 18:.1f}h11l-3 3.5l3 3.5h-11z" fill="{RED}" stroke="{WHITE}" stroke-width=".8"/>')
    total = sum(c for *_, c in cells)
    css = f".edge{{stroke:{WHITE};stroke-width:.8;stroke-linejoin:round}}.win{{stroke:{WHITE};stroke-width:1.6}}"
    body = f"""{caption(40, 20, "MISSION LOG", f"LAST 53 WEEKS · {total:,} CONTRIBUTIONS")}
<path d="{"".join(lots)}" fill="none" stroke="{WHITE}" stroke-opacity=".18"/>
{"".join(parts)}"""
    return slice_svg(640, body, css)


def ops(stats):
    """Repos shown as Operations cards: top owned repos by stars, minus this profile repo."""
    return [r for r in stats["repos"] if r["name"] != stats["login"]][:N_OPS]


def operations_caption():
    return slice_svg(80, caption(40, 20, "OPERATIONS"))


def op_card(repo, side):
    w, h = W // 2, 160
    px, pw = (34, 376) if side == "left" else (10, 376)
    name = repo["name"].upper()
    title = f"OP: {name}"
    size = fit("stencil", title, 18, pw - 40)
    desc = has_glyphs("type", repo["description"]) or "No brief on file."
    lines = wrap("type", desc, 12, pw - 40, 3)
    meta = f"{repo['stars']:,} STARS · {repo['forks']:,} FORKS"
    if repo["languages"]:
        meta += " · " + " / ".join(repo["languages"][:3]).upper()
    meta_size = fit("type", meta, 11, pw - 40)
    body = f"""<rect x="{px}" y="16" width="{pw}" height="128" fill="{WHITE}"/>
<rect x="{px}" y="16" width="{pw}" height="6" fill="{RED}"/>
<rect x="{px + pw - 60}" y="22" width="60" height="122" fill="url(#dots)"/>
{text(px + 20, 52, title, "stencil", size)}
{"".join(text(px + 20, 76 + i * 17, s, "type", 12) for i, s in enumerate(lines))}
<path d="M{px + 20} 120H{px + pw - 20}" stroke="{NAVY}" stroke-opacity=".25"/>
{text(px + 20, 136, meta, "type", meta_size, RED)}"""
    return slice_svg(h, body, w=w, left=side == "left", right=side == "right")


def render(stats):
    """{filename: svg} for every slice."""
    out = {"header.svg": header(), "record.svg": record(stats), "operations.svg": operations_caption(),
           "footer.svg": footer()}
    out.update(links())
    out["city.svg"] = city(stats)
    for i, repo in enumerate(ops(stats)):
        out[f"op-{i + 1}.svg"] = op_card(repo, "left" if i % 2 == 0 else "right")
    return out


def main():
    stats = json.loads(STATS.read_text())
    ASSETS.mkdir(exist_ok=True)
    for name, svg in render(stats).items():
        (ASSETS / name).write_text(svg)


if __name__ == "__main__":
    main()
