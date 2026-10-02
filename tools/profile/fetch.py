"""Fetch GitHub profile data into data/stats.json.

Fail-safe: starts from the existing stats.json and only overwrites what fetched
successfully. Exits nonzero only if every source fails.
"""

import json
import os
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

LOGIN = os.environ.get("GITHUB_REPOSITORY_OWNER", "jeromehardaway")
STATS = Path(__file__).parent / "data" / "stats.json"
TOKEN = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")

# ponytail: first 100 repos by stars; repos past #100 add ~0 stars. Paginate if that changes.
PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    login name createdAt
    followers { totalCount }
    pullRequests { totalCount }
    merged: pullRequests(states: MERGED) { totalCount }
    contributionsCollection { contributionYears }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC,
                 orderBy: {field: STARGAZERS, direction: DESC}) {
      nodes {
        name description url stargazerCount forkCount
        languages(first: 5, orderBy: {field: SIZE, direction: DESC}) { nodes { name } }
      }
    }
  }
}"""


def graphql(query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "User-Agent": "hashflagify"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise RuntimeError(body["errors"])
    return body["data"]["user"]


def fetch_profile():
    u = graphql(PROFILE_QUERY, {"login": LOGIN})
    repos = [
        {
            "name": r["name"],
            "description": r["description"] or "",
            "url": r["url"],
            "stars": r["stargazerCount"],
            "forks": r["forkCount"],
            "languages": [lang["name"] for lang in r["languages"]["nodes"]],
        }
        for r in u["repositories"]["nodes"]
    ]
    return {
        "login": u["login"],
        "name": u["name"],
        "created_at": u["createdAt"],
        "followers": u["followers"]["totalCount"],
        "prs_total": u["pullRequests"]["totalCount"],
        "prs_merged": u["merged"]["totalCount"],
        "years": sorted(u["contributionsCollection"]["contributionYears"]),
        "stars": sum(r["stars"] for r in repos),
        "repos": repos,
    }


def fetch_calendar(years):
    aliases = "\n".join(
        f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") '
        "{ contributionCalendar { weeks { contributionDays { date contributionCount } } } }"
        for y in years
    )
    u = graphql(f"query($login: String!) {{ user(login: $login) {{ {aliases} }} }}", {"login": LOGIN})
    today = date.today().isoformat()
    return {
        d["date"]: d["contributionCount"]
        for c in u.values()
        for w in c["contributionCalendar"]["weeks"]
        for d in w["contributionDays"]
        if d["date"] <= today
    }


def streaks(days, today):
    """(current, longest). Current may end yesterday if today has no contributions yet."""
    day = today if days.get(today.isoformat(), 0) else today - timedelta(days=1)
    current = 0
    while days.get(day.isoformat(), 0):
        current += 1
        day -= timedelta(days=1)
    longest = run = 0
    prev = None
    for d in sorted(k for k, v in days.items() if v):
        cur = date.fromisoformat(d)
        run = run + 1 if prev and cur - prev == timedelta(days=1) else 1
        longest = max(longest, run)
        prev = cur
    return current, longest


def main():
    stats = json.loads(STATS.read_text()) if STATS.exists() else {}
    ok = 0

    try:
        stats.update(fetch_profile())
        ok += 1
    except Exception as e:
        print(f"profile fetch failed, keeping previous: {e}", file=sys.stderr)

    if stats.get("years"):
        try:
            days = fetch_calendar(stats["years"])
            today = date.today()
            current, longest = streaks(days, today)
            stats.update(
                contributions=dict(sorted(days.items())),
                contributions_all_time=sum(days.values()),
                contributions_this_year=sum(v for k, v in days.items() if k.startswith(str(today.year))),
                streak_current=current,
                streak_longest=longest,
            )
            ok += 1
        except Exception as e:
            print(f"calendar fetch failed, keeping previous: {e}", file=sys.stderr)

    if not ok:
        sys.exit("all sources failed")
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=1, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
