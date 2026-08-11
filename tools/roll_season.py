#!/usr/bin/env python3
"""Decide whether the next season can be rolled into the charter, and do it.

Run by .github/workflows/roll-season.yml. Writes `status` and `year` to
$GITHUB_OUTPUT so the workflow knows whether to open a pull request, open an
issue, or do nothing.

The two halves of a league year become knowable at different times:

  * nfl_draft_end is announced long before the season and is the only anchor
    a human has to supply. Everything in the offseason half of the calendar
    hangs off it.
  * last_preseason_game and first_nfl_game are not published until the NFL
    releases the schedule, around May. fetch_anchors.py pulls those.

So a February run can usually fill the offseason half and asks for the draft
date; a May run completes the rest on its own.

Outputs:
    status             `updated` if the spec changed, else `nothing`
    needs_draft_date   `true` when the draft date still has to be typed in
    year               the season being rolled

These are independent. A May run often sets both: it fetches the schedule
anchors, which is worth committing, while the draft date is still missing.
"""

import datetime as dt
import json
import os
import subprocess
import sys

SPEC = "charter_spec.json"
NEEDED = {"nfl_draft_end", "last_preseason_game", "first_nfl_game"}
TOOLS = os.path.dirname(os.path.abspath(__file__))


def output(**kw):
    path = os.environ.get("GITHUB_OUTPUT")
    for key, value in kw.items():
        print("%s=%s" % (key, value))
        if path:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("%s=%s\n" % (key, value))


def load():
    with open(SPEC, encoding="utf-8") as fh:
        return json.load(fh)


def run(*args):
    """Run a tool, returning True on success. Never raises: a scheduled job
    that cannot reach ESPN should stay quiet and try again next week."""
    proc = subprocess.run([sys.executable] + list(args),
                          capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    return proc.returncode == 0


def main():
    spec = load()
    seasons = spec.get("seasons") or {}
    if not seasons:
        output(status="nothing", needs_draft_date="false", year="")
        return

    # Stay on the newest season until it is both complete and published, and
    # only then look ahead. Moving on too early strands a half-filled year:
    # once its schedule anchors are written it becomes the newest, and a later
    # run would skip past it. Staying too long is harmless, because building
    # an already-built calendar changes nothing.
    newest = max(int(y) for y in seasons)
    today = dt.date.today()
    target = newest + 1 if (NEEDED <= set(seasons[str(newest)])
                            and today.year > newest) else newest

    if today.year < target:
        # ESPN has nothing for a season that has not begun its calendar year.
        print("Next season is %d; it is only %d. Nothing to do."
              % (target, today.year))
        output(status="nothing", needs_draft_date="false", year=target)
        return

    # Compared over the whole spec, so an unchanged rebuild reports nothing
    # rather than opening an identical pull request every week.
    before = json.dumps(spec, sort_keys=True)

    # Schedule anchors. Failure here is normal before the May release.
    if run(os.path.join(TOOLS, "fetch_anchors.py"), str(target), SPEC):
        print("Fetched schedule anchors for %d." % target)
    else:
        print("Schedule anchors for %d are not available yet." % target)

    have = set((load().get("seasons") or {}).get(str(target), {}))
    if NEEDED <= have:
        run(os.path.join(TOOLS, "build_dates.py"), SPEC, str(target))

    changed = json.dumps(load(), sort_keys=True) != before
    output(status="updated" if changed else "nothing",
           needs_draft_date=str("nfl_draft_end" not in have).lower(),
           year=target)


if __name__ == "__main__":
    main()
