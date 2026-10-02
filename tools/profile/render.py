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
    for name, t in used.items():
        assert has_glyphs(name, t) == t, f"{name} font lacks glyphs in {t!r}"
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
    body = f"""<g>{"".join(chars)}<rect class="cursor" x="{xs[0] + 5:.1f}" y="46" width="3" height="30"/></g>
<path d="M{tx + 34} {cy - 12}C{tx - 40} {cy - 80} {tx - 60} 40 {tx - 120} 0" fill="none" stroke="{SILVER}" stroke-width="5" stroke-linecap="round" stroke-dasharray="0 8"/>
<rect x="{tx - 6}" y="{ty - 6}" width="{tw + 12}" height="{th + 12}" rx="46" fill="{WHITE}" opacity=".12"/>
<rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="40" fill="{WHITE}" stroke="{SILVER}" stroke-width="2"/>
<rect x="{tx + 10}" y="{ty + 10}" width="{tw - 20}" height="{th - 20}" rx="32" fill="none" stroke="{SILVER}" stroke-width="2"/>
<circle cx="{tx + 34}" cy="{cy}" r="10" fill="{NAVY}" stroke="{SILVER}" stroke-width="2"/>
{tag}"""
    return slice_svg(h, body, css, top=True)


def footer():
    """The GIF is its own <img> (GIFs inside an SVG <img> don't reliably animate), so the
    footer is four pieces: text, a navy slice either side of the 320x240 GIF, and the end."""
    gw, side = 320, (W - 320) // 2
    frame = f'fill="{WHITE}"'
    top = f"""<path d="M{RAIL + 40} 40H{W - RAIL - 40}" stroke="{RED}" stroke-width="2"/>
{text(W / 2, 84, "Impact Over Interference.", "type", 20, SILVER, ' text-anchor="middle"')}
{text(W / 2, 130, "END OF BRIEF", "stencil", 30, WHITE, ' text-anchor="middle" letter-spacing="4"')}
<rect x="{side - 8}" y="152" width="{gw + 16}" height="8" {frame}/>"""
    return {
        "footer.svg": slice_svg(160, top),
        "footer-left.svg": slice_svg(240, f'<rect x="{side - 8}" width="8" height="240" {frame}/>', w=side, right=False),
        "footer-right.svg": slice_svg(240, f'<rect width="8" height="240" {frame}/>', w=side, left=False),
        "footer-end.svg": slice_svg(40, f'<rect x="{side - 8}" width="{gw + 16}" height="8" {frame}/>', bottom=True),
    }


# ---------- link buttons: one SVG each so each can sit in its own <a> ----------

def links():
    """5 equal 168px cells (each img is width=20%, so the row scales as one). Buttons are
    128px with even 33px gaps across the page; each one still sits inside its own cell."""
    cell, bw, gap, edge = W // len(LINKS), 128, 33, 34
    out = {}
    for i, (name, label, _) in enumerate(LINKS):
        x = edge + i * (bw + gap) - i * cell  # page position -> cell position
        assert 0 <= x and x + bw <= cell
        size = fit("stencil", label, 15, bw - 24)
        body = f"""<rect x="{x}" y="20" width="{bw}" height="40" rx="4" fill="{WHITE}"/>
<rect x="{x}" y="20" width="6" height="40" rx="2" fill="{RED}"/>
{text(x + bw / 2 + 3, 46, label, "stencil", size, extra=' text-anchor="middle" letter-spacing="1"')}"""
        out[f"{name}.svg"] = slice_svg(80, body, w=cell, left=i == 0, right=i == len(LINKS) - 1)
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


# Operations without a fetched repo: (title, brief, meta, url or None for no link)
EXTRA_OPS = [
    ("J0DI3", "VWC's AI career intelligence platform for veterans.", "CLOSED SOURCE", None),
    ("OPEN SOURCE BOARD", "The Vets Who Code open source project board.", "CONTRIBUTIONS WELCOME",
     "https://github.com/orgs/Vets-Who-Code/projects/82"),
]

REPORTS = [  # (title, source, url)
    ("JUNIOR TO SENIOR", "GITHUB README", "https://github.com/readme/guides/engineering-career-success"),
    ("TEACHING IN PUBLIC", "GITHUB README", "https://github.com/readme/guides/teaching-with-github"),
    ("LEARN HOW TO LEARN", "STACK OVERFLOW BLOG",
     "https://stackoverflow.blog/2020/01/11/hello-world-want-to-be-a-developer-learn-how-to-learn/"),
    ("EMBRACE THE SUCK", "STACK OVERFLOW BLOG",
     "https://stackoverflow.blog/2020/02/10/hello-world-curing-imposter-syndrome-by-embracing-the-suck/"),
]

STACK = [
    ("LANGUAGES", "Python, TypeScript/JavaScript, SQL"),
    ("AI/ML", "LangChain, LangGraph, LangSmith, RAG, agentic systems, MCP, Hugging Face, T5, "
              "Transformers.js, PyTorch, DeepSpeed"),
    ("BACKEND", "FastAPI, Node.js, Pydantic"),
    ("FRONTEND", "React, Next.js, TypeScript, Tailwind CSS, Framer Motion"),
    ("CLOUD", "AWS, Azure, GCP (Vertex AI, BigQuery), Firebase"),
    ("INFRA", "Terraform, Docker, Kubernetes, GitHub Actions"),
    ("DATA", "PostgreSQL, Redis, BigQuery, Delta Lake"),
]

COMMENDATIONS = [
    "Google Developer Expert",
    "GitHub Star (alum)",
    "White House workforce development recognition",
    "Microsoft Global Hackathon winner",
    "Master.dev (Frontend Masters) instructor: Getting a Software Engineering Job",
    "LinkedIn Learning instructor",
    "Stack Overflow Blog contributor",
]
FEATURED = "Wired · Business Insider · HuffPost · Black Enterprise · GitHub ReadME · Stack Overflow"

TITLE_LINE = "FOUNDER & LEAD ENGINEER, VETS WHO CODE | AIR FORCE VETERAN | GOOGLE DEVELOPER EXPERT"
BIO = "I engineer the platforms, AI systems, and curriculum that turn veterans into software engineers."


def situation():
    body = f"""{caption(40, 20, "SITUATION")}
{text(40, 112, TITLE_LINE, "stencil", fit("stencil", TITLE_LINE, 17, W - 80), WHITE)}
{text(40, 140, BIO, "type", fit("type", BIO, 15, W - 80), SILVER)}"""
    return slice_svg(160, body)


def unit():
    tiles = [("300+", "VETERANS TRAINED"), ("$20M+", "COLLECTIVE ALUMNI EARNINGS"), ("100%", "REMOTE AND FREE TO VETERANS")]
    body = caption(40, 20, "UNIT: VETS WHO CODE", "EST. 2014 · VETERAN-LED 501(C)(3) SOFTWARE ENGINEERING ACCELERATOR")
    for i, (value, label) in enumerate(tiles):
        x = 40 + i * 260
        body += f"""<rect x="{x}" y="100" width="240" height="80" fill="{WHITE}"/>
<rect x="{x}" y="100" width="240" height="4" fill="{RED}"/>
<rect x="{x + 180}" y="104" width="60" height="76" fill="url(#dots)"/>
{text(x + 20, 146, value, "stencil", 30)}
{text(x + 20, 168, label, "type", 12)}"""
    ship = "TROOPS NOW SHIP CODE AT MICROSOFT, GOOGLE, AMAZON, AND HOME DEPOT"
    body += text(40, 218, ship, "stencil", fit("stencil", ship, 16, W - 80), WHITE)
    body += text(40, 246, "I lead the org and engineer the systems that run it.", "type", 15, SILVER)
    return slice_svg(280, body)


def tech_stack():
    rows, y = "", 128
    for label, value in STACK:
        rows += text(64, y, label, "stencil", 13, RED, ' letter-spacing="1"')
        for line in wrap("type", value, 14, W - 64 - 190 - 24, 3):
            rows += text(190, y, line, "type", 14)
            y += 22
        y += 6
    panel_h = y - 96 + 4
    h = math.ceil((96 + panel_h + 24) / 40) * 40
    body = f"""{caption(40, 20, "TECH STACK")}
<rect x="40" y="96" width="{W - 80}" height="{panel_h}" fill="{WHITE}"/>
<rect x="40" y="96" width="6" height="{panel_h}" fill="{RED}"/>
<rect x="{W - 120}" y="96" width="80" height="{panel_h}" fill="url(#dots)"/>
{rows}"""
    return slice_svg(h, body)


def commendations():
    body = caption(40, 20, "COMMENDATIONS")
    for i, item in enumerate(COMMENDATIONS):
        y = 112 + i * 28
        body += f'<path d="M48 {y - 5}l5-5 5 5-5 5z" fill="{RED}"/>'
        body += text(68, y, item, "type", fit("type", item, 15, W - 108), WHITE)
    body += text(40, 320, "FEATURED IN", "stencil", 13, RED, ' letter-spacing="1"')
    body += text(150, 320, FEATURED, "type", fit("type", FEATURED, 14, W - 190), SILVER)
    return slice_svg(360, body)


def ops(stats):
    """Operations cards: (title, brief, meta, url or None). Repos are picked in fetch.OPS."""
    out = []
    for r in stats["ops"]:
        meta = f"{r['stars']:,} STARS · {r['forks']:,} FORKS"
        if r["languages"]:
            meta += " · " + " / ".join(r["languages"][:3]).upper()
        out.append((r.get("title") or r["name"].upper(), r["description"], meta, r["url"]))
    return out + EXTRA_OPS


def half(side):
    """(panel x, panel width) for a half-width card; panels mirror around the page center."""
    return (34, 376) if side == "left" else (10, 376)


def op_card(title, desc, meta, side):
    px, pw = half(side)
    title = f"OP: {title}"
    size = fit("stencil", title, 18, pw - 40)
    lines = wrap("type", has_glyphs("type", desc), 12, pw - 40, 3)
    meta_size = fit("type", meta, 11, pw - 40)
    body = f"""<rect x="{px}" y="16" width="{pw}" height="128" fill="{WHITE}"/>
<rect x="{px}" y="16" width="{pw}" height="6" fill="{RED}"/>
<rect x="{px + pw - 60}" y="22" width="60" height="122" fill="url(#dots)"/>
{text(px + 20, 52, title, "stencil", size)}
{"".join(text(px + 20, 76 + i * 17, s, "type", 12) for i, s in enumerate(lines))}
<path d="M{px + 20} 120H{px + pw - 20}" stroke="{NAVY}" stroke-opacity=".25"/>
{text(px + 20, 136, meta, "type", meta_size, RED)}"""
    return slice_svg(160, body, w=W // 2, left=side == "left", right=side == "right")


def report_card(title, source, side):
    px, pw = half(side)
    body = f"""<rect x="{px}" y="12" width="{pw}" height="96" fill="{WHITE}"/>
<rect x="{px}" y="12" width="6" height="96" fill="{RED}"/>
<rect x="{px + pw - 60}" y="12" width="60" height="96" fill="url(#dots)"/>
{text(px + 24, 52, title, "stencil", fit("stencil", title, 20, pw - 48), extra=' letter-spacing="1"')}
{text(px + 24, 82, f"{source} · READ THE REPORT", "type", 12, RED)}"""
    return slice_svg(120, body, w=W // 2, left=side == "left", right=side == "right")


def render(stats):
    """{filename: svg} for every slice."""
    out = {
        "header.svg": header(),
        "situation.svg": situation(),
        "unit.svg": unit(),
        "record.svg": record(stats),
        "city.svg": city(stats),
        "operations.svg": slice_svg(80, caption(40, 20, "OPERATIONS")),
        "stack.svg": tech_stack(),
        "commendations.svg": commendations(),
        "reports.svg": slice_svg(80, caption(40, 20, "FIELD REPORTS")),
    }
    out.update(footer())
    out.update(links())
    sides = ("left", "right")
    for i, (title, desc, meta, _) in enumerate(ops(stats)):
        out[f"op-{i + 1}.svg"] = op_card(title, desc, meta, sides[i % 2])
    for i, (title, source, _) in enumerate(REPORTS):
        out[f"report-{i + 1}.svg"] = report_card(title, source, sides[i % 2])
    return out


def main():
    stats = json.loads(STATS.read_text())
    ASSETS.mkdir(exist_ok=True)
    for name, svg in render(stats).items():
        (ASSETS / name).write_text(svg)


if __name__ == "__main__":
    main()
