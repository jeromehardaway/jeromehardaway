"""Rewrite only the content between <!-- name:start --> / <!-- name:end --> markers in README.md."""

import json
import sys

from render import LINKS, ROOT, STATS, ops

README = ROOT / "README.md"


def img(name, alt):
    return f'<img src="./assets/{name}.svg" alt="{alt}" align="top">'


def brief(stats):
    # Pieces that share a row must touch: no whitespace between them or GitHub shows a gap.
    links = "".join(f'<a href="{url}">{img(name, label)}</a>' for name, label, url in LINKS)
    cards = [f'<a href="{r["url"]}">{img(f"op-{i + 1}", "OP: " + r["name"])}</a>' for i, r in enumerate(ops(stats))]
    rows = ["".join(cards[i:i + 2]) for i in range(0, len(cards), 2)]
    return "\n".join([
        '<div align="center">',
        img("header", "Mission Brief: Jerome Hardaway, @Maverick, USAF Veteran, Founder of Vets Who Code"),
        links,
        img("record", f"Service record: {stats['followers']:,} followers, {stats['stars']:,} stars, "
                      f"{stats['prs_merged']:,} PRs merged, {stats['contributions_all_time']:,} contributions"),
        img("city", "Mission Log: contribution city for the last 53 weeks"),
        img("operations", "Operations"),
        *rows,
        img("footer", "End of brief"),
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
