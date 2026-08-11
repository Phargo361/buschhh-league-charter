#!/usr/bin/env python3
"""Fetch a season's NFL anchor dates from ESPN's public API.

Two of the three anchors build_dates.py needs are published by the NFL only
once the schedule is released, around May:

    last_preseason_game   the last day of preseason
    first_nfl_game        the first day of the regular season

The third, nfl_draft_end, is not in this API and has to be entered by hand.

Two traps this works around, both found by checking the output against the
2026 dates rather than trusting the API:

  * ESPN's season and week `startDate`/`endDate` are administrative padding,
    not games. In 2026 preseason "ends" Sep 6 and regular week 1 "starts"
    Sep 6. Real game dates come from the events in each week.
  * Event stamps are UTC, so a night game lands on the next day. The 2026
    opener kicks off 8:20pm ET Wed Sep 9 and is stamped Sep 10. Everything is
    converted to US Eastern before the date is taken.

Refuses to write anything failing the sanity checks, because a wrong date here
becomes a wrong roster or money deadline for the whole league.

Usage:
    python3 fetch_anchors.py 2027 [charter_spec.json] [--dry-run]
"""

import datetime as dt
import json
import sys
import urllib.request

BASE = ("https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
        "/seasons/%d")
PRESEASON, REGULAR = 1, 2
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "Chrome/124.0 Safari/537.36")
TIMEOUT = 30

# Preseason ends in August and the regular season opens in September every
# year. Anything else means the API changed shape or answered for a different
# season, and we would rather fail loudly than publish it.
EXPECTED = {"last_preseason_game": (8, 9), "first_nfl_game": (9, 9)}

try:
    from zoneinfo import ZoneInfo
    EASTERN = ZoneInfo("America/New_York")
except Exception:                                   # pragma: no cover
    EASTERN = dt.timezone(dt.timedelta(hours=-5))   # EST is close enough


def get(url):
    req = urllib.request.Request(url.replace("http://", "https://"),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as fh:
        return json.load(fh)


def event_dates(year, season_type, week):
    """Eastern-time calendar dates of every game in one week."""
    listing = get("%s/types/%d/weeks/%d/events?limit=100"
                  % (BASE % year, season_type, week))
    out = []
    for item in listing.get("items", []):
        stamp = get(item["$ref"])["date"]
        utc = dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%MZ").replace(
            tzinfo=dt.timezone.utc)
        out.append(utc.astimezone(EASTERN).date())
    if not out:
        raise SystemExit("ESPN returned no games for %d type %d week %d"
                         % (year, season_type, week))
    return sorted(out)


def last_week_number(year, season_type):
    weeks = get("%s/types/%d/weeks?limit=25" % (BASE % year, season_type))
    count = weeks.get("count")
    if not count:
        raise SystemExit("ESPN listed no weeks for %d type %d"
                         % (year, season_type))
    return count


def fetch(year):
    # Preseason week 1 is the Hall of Fame game, so the final week is however
    # many ESPN lists, not a fixed number.
    final_pre = last_week_number(year, PRESEASON)
    return {
        "last_preseason_game": event_dates(year, PRESEASON, final_pre)[-1]
                               .isoformat(),
        "first_nfl_game": event_dates(year, REGULAR, 1)[0].isoformat(),
    }


def validate(year, anchors):
    problems = []
    for key, value in anchors.items():
        date = dt.date.fromisoformat(value)
        if date.year != year:
            problems.append("%s is %s, not in %d" % (key, value, year))
        lo, hi = EXPECTED[key]
        if not lo <= date.month <= hi:
            problems.append("%s is %s, outside months %d-%d"
                            % (key, value, lo, hi))
    pre = dt.date.fromisoformat(anchors["last_preseason_game"])
    first = dt.date.fromisoformat(anchors["first_nfl_game"])
    if pre >= first:
        problems.append("preseason ends %s, on or after the first game %s"
                        % (pre, first))
    elif (first - pre).days > 21:
        problems.append("%d days between the last preseason game and the "
                        "first game" % (first - pre).days)
    if problems:
        raise SystemExit("Refusing to write. ESPN gave:\n  "
                         + "\n  ".join(problems))


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    dry = "--dry-run" in argv
    year = int(args[0])
    spec_path = args[1] if len(args) > 1 else "charter_spec.json"

    anchors = fetch(year)
    validate(year, anchors)
    for key, value in sorted(anchors.items()):
        print("%-22s %s" % (key, value))
    if dry:
        return

    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    season = spec.setdefault("seasons", {}).setdefault(str(year), {})
    season.update(anchors)
    with open(spec_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(spec, fh, indent=2, ensure_ascii=False)

    if "nfl_draft_end" in season:
        print("\nAll three anchors present for %d." % year)
    else:
        print("\nStill missing nfl_draft_end for %d. Add it under seasons.%d "
              "in %s, then run build_dates.py." % (year, year, spec_path))


if __name__ == "__main__":
    main(sys.argv[1:])
