#!/usr/bin/env python3
"""Derive the League Dates section from a season's NFL anchor dates.

Only three dates per season are real inputs, because only they are set by the
NFL rather than by this charter:

    nfl_draft_end        the last day of the NFL draft
    last_preseason_game  the final preseason game
    first_nfl_game       the first game of the NFL regular season

Everything else follows from the charter and is computed here, so the calendar
can never quietly disagree with the rules it came from. Rewrites the
"League Dates" section of charter_spec.json in place. Standard library only.

Usage: python3 build_dates.py charter_spec.json [year]
"""

import datetime as dt
import json
import sys

SECTION_NAME = "League Dates"
SECTION_GREEK = "ΚΑΙΡΟΙ"
MONDAY = 0


def d(text):
    return dt.date.fromisoformat(text)


def fmt(date):
    # "Mon, Aug 31, 2026" - the weekday matters as much as the date, because
    # several rules are written as "the Monday after" or "Tuesday through
    # Sunday".
    return "%s, %s %d, %d" % (date.strftime("%a"), date.strftime("%b"),
                              date.day, date.year)


def next_weekday(date, weekday):
    """The first given weekday strictly after `date`."""
    ahead = (weekday - date.weekday() - 1) % 7 + 1
    return date + dt.timedelta(days=ahead)


def week_sunday(first_game, n):
    """The Sunday of NFL week `n`, counting the week of the first game as 1."""
    first_sunday = first_game + dt.timedelta(
        days=(6 - first_game.weekday()) % 7)
    return first_sunday + dt.timedelta(days=7 * (n - 1))


def derive(anchors):
    """Return [label, date, note] rows for one season."""
    draft_end = d(anchors["nfl_draft_end"])
    last_pre = d(anchors["last_preseason_game"])
    first_game = d(anchors["first_nfl_game"])

    # Section 1: the League Year opens 3 weeks after the draft ends.
    league_year = draft_end + dt.timedelta(days=21)
    # Section 7: the rookie draft falls within 3 weeks of the League Year.
    rookie_draft = league_year + dt.timedelta(days=21)
    # Section 2: buy-ins are due 3 weeks before the rookie draft, which lands
    # on the first day of the League Year.
    buy_ins = rookie_draft - dt.timedelta(days=21)
    # Section 1: the Regular Season starts the Monday after the last
    # preseason game.
    reg_season = next_weekday(last_pre, MONDAY)

    return [
        ["NFL draft ends", fmt(draft_end), ""],
        ["League Year starts", fmt(league_year),
         "Offseason opens. Rosters go to 23 bench spots. Taxi graduation."],
        ["Buy-ins due", fmt(buy_ins),
         "$200 per team. An unpaid team is locked."],
        ["New rule pitch", fmt(league_year + dt.timedelta(days=7)), ""],
        ["New rule voting", fmt(league_year + dt.timedelta(days=14)),
         "One week to vote. No vote counts as a no."],
        ["Rookie draft", fmt(rookie_draft), "Four rounds, rookies only."],
        ["Last preseason game", fmt(last_pre), ""],
        ["Regular Season starts", fmt(reg_season),
         "Rosters drop to 16 bench spots, 25 players. $350 FAAB added."],
        ["First NFL game", fmt(first_game),
         "Taxi squad closes. No player may be added to it after this."],
        ["Trade deadline", fmt(week_sunday(first_game, 14)),
         "End of Week 14. No trades during the playoffs."],
        ["Playoffs start", fmt(week_sunday(first_game, 15)),
         "Weeks 15, 16, and 17. Toilet Bowl runs alongside."],
        ["Championship", fmt(week_sunday(first_game, 17)), ""],
        ["Trading reopens", fmt(week_sunday(first_game, 18)
                                + dt.timedelta(days=1)),
         "After Week 18."],
    ]


def section_for(year, anchors):
    return {
        "num": 0,  # renumbered below
        "name": SECTION_NAME,
        "greek": SECTION_GREEK,
        "blocks": [
            {
                "type": "table",
                "header": ["%s Season" % year, "Date", "Note"],
                "rows": derive(anchors),
                "widths": [0.34, 0.30, 0.36],
            },
            {
                "type": "para",
                "text": "These dates come from three NFL dates for the "
                        "season: the last day of the draft, the last "
                        "preseason game, and the first game. Every other "
                        "date above is set by the rules in this charter.",
            },
        ],
    }


def main(spec_path, year=None):
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)

    seasons = spec.get("seasons") or {}
    if not seasons:
        raise SystemExit("charter_spec.json has no `seasons` block.")
    year = str(year or max(seasons))
    if year not in seasons:
        raise SystemExit("No anchors for %s. Have: %s"
                         % (year, ", ".join(sorted(seasons))))

    new = section_for(year, seasons[year])
    names = [s["name"] for s in spec["sections"]]
    if SECTION_NAME in names:
        spec["sections"][names.index(SECTION_NAME)] = new
    else:
        # Straight after Calendar, which it expands on.
        at = names.index("Calendar") + 1 if "Calendar" in names else len(names)
        spec["sections"].insert(at, new)

    for i, sec in enumerate(spec["sections"]):
        sec["num"] = i

    with open(spec_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(spec, fh, indent=2, ensure_ascii=False)
    print("wrote %s dates into %s" % (year, spec_path))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
