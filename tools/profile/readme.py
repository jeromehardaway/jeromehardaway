"""Rewrite only the content between <!-- name:start --> / <!-- name:end --> markers in README.md."""

import json
from html import escape
import sys

from render import BIO, COMMENDATIONS, FEATURED, LINKS, REPORTS, ROOT, STACK, STATS, TITLE_LINE, ops

README = ROOT / "README.md"


def img(name, alt, width="100%"):
    # Percent widths: every piece scales by the same factor when the column is narrower than 840px.
    return f'<img src="./assets/{name}.svg" alt="{escape(alt)}" width="{width}" align="top">'


def pairs(items):
    """Half-width pieces two per row. They must touch: whitespace between them shows as a gap."""
    return ["".join(items[i:i + 2]) for i in range(0, len(items), 2)]


def linked(url, image):
    return f'<a href="{url}">{image}</a>' if url else image


def brief(stats):
    links = "".join(linked(url, img(name, label, "20%")) for name, label, url in LINKS)
    cards = [linked(url, img(f"op-{i + 1}", f"OP: {title}. {desc}", "50%")) for i, (title, desc, _, url) in enumerate(ops(stats))]
    reports = [linked(url, img(f"report-{i + 1}", f"{title} ({source})", "50%")) for i, (title, source, url) in enumerate(REPORTS)]
    return "\n".join([
        '<div align="center">',
        img("header", "Mission Brief: Jerome Hardaway, @Maverick, USAF Veteran, Founder of Vets Who Code"),
        links,
        img("situation", f"{TITLE_LINE}. {BIO}"),
        img("unit", "Vets Who Code: est. 2014, 300+ veterans trained, $20M+ collective alumni earnings, "
                    "100% remote and free to veterans"),
        img("record", f"Service record: {stats['followers']:,} followers, {stats['stars']:,} stars, "
                      f"{stats['prs_merged']:,} PRs merged, {stats['contributions_all_time']:,} contributions"),
        img("city", "Mission Log: contribution city for the last 53 weeks"),
        img("operations", "Operations"),
        *pairs(cards),
        img("stack", "Tech stack: " + "; ".join(f"{k}: {v}" for k, v in STACK)),
        img("commendations", "Commendations: " + "; ".join(COMMENDATIONS) + ". Featured in: " + FEATURED),
        img("reports", "Field reports"),
        *pairs(reports),
        img("footer", "Impact Over Interference. End of brief."),
        # ponytail: 30.95 + 38.1 + 30.95 = 100; sides are 260/840, the 320px GIF row is 240 tall
        img("footer-left", "", "30.95%") + '<img src="./assets/vwc.gif" alt="Vets Who Code" width="38.1%" align="top">'
        + img("footer-right", "", "30.95%"),
        img("footer-end", ""),
        "</div>",
    ])


def replace_zone(text, name, content):
    start, end = f"<!-- {name}:start -->", f"<!-- {name}:end -->"
    if text.count(start) != 1 or text.count(end) != 1:
        sys.exit(f"README.md must contain exactly one {start} and one {end}")
    head, rest = text.split(start)
    _, tail = rest.split(end)
    return f"{head}{start}\n{content}\n{end}{tail}"


def main():
    stats = json.loads(STATS.read_text())
    README.write_text(replace_zone(README.read_text(), "brief", brief(stats)))


if __name__ == "__main__":
    main()
