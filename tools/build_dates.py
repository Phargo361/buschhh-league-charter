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
MONDAY = 0

# Section 6 retires a player from the taxi squad once he has more than 3 years
# of NFL experience. At a League Year opening in year Y, the class drafted in
# Y-4 has four seasons behind it and is the one that must be activated: the
# Y-3 class has exactly three, which is not "more than".
TAXI_GRADUATION_LAG = 4

# The first overall pick is only a memory hook, so managers can place the
# expiring class without doing arithmetic. Unknown years fall back to the bare
# draft year, which is what actually governs.
FIRST_PICKS = {
    2022: "Travon Walker",
    2023: "Bryce Young",
    2024: "Caleb Williams",
    2025: "Cam Ward",
}


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
    """Return (label, date, note) triples, dates as date objects.

    The caller renders each date twice: once for people, once as ISO for the
    add-to-calendar buttons.
    """
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

    graduating = league_year.year - TAXI_GRADUATION_LAG
    taxi_note = "Players drafted in %d must be activated." % graduating
    if graduating in FIRST_PICKS:
        taxi_note += " That is the %s draft class." % FIRST_PICKS[graduating]

    return [
        ("NFL draft ends", draft_end, ""),
        ("League Year starts", league_year, "Offseason opens."),
        ("Bench goes up to 23", league_year,
         "The Commissioner raises the bench from 16 to 23 spots, for 32 "
         "players in all."),
        ("Taxi graduation", league_year, taxi_note),
        ("Buy-ins due", buy_ins, "$200 per team. An unpaid team is locked."),
        ("New rule pitch", league_year + dt.timedelta(days=7), ""),
        ("New rule voting", league_year + dt.timedelta(days=14),
         "One week to vote. No vote counts as a no."),
        ("Rookie draft", rookie_draft, "Four rounds, rookies only."),
        ("Last preseason game", last_pre, ""),
        ("Regular Season starts", reg_season, "$350 FAAB added."),
        ("Bench goes down to 16", reg_season,
         "The Commissioner cuts the bench from 23 to 16 spots. Teams must be "
         "at 25 players that day."),
        ("First NFL game", first_game,
         "Taxi squad closes. No player may be added to it after this."),
        ("Trade deadline", week_sunday(first_game, 14),
         "End of Week 14. No trades during the playoffs."),
        ("Playoffs start", week_sunday(first_game, 15),
         "Weeks 15, 16, and 17. Toilet Bowl runs alongside."),
        ("Championship", week_sunday(first_game, 17), ""),
        ("Trading reopens",
         week_sunday(first_game, 18) + dt.timedelta(days=1), "After Week 18."),
    ]


def section_for(year, anchors):
    events = derive(anchors)
    return {
        "num": 0,  # renumbered below
        "name": SECTION_NAME,
        "blocks": [
            {
                "type": "table",
                "header": ["%s Season" % year, "Date", "Note"],
                "rows": [[label, fmt(date), note]
                         for label, date, note in events],
                # Parallel to rows. Only the HTML build reads it, to hang an
                # add-to-calendar button off each date; the other renderers
                # ignore keys they do not know.
                "ics_dates": [date.isoformat() for _, date, _ in events],
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
