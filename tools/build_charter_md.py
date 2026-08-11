#!/usr/bin/env python3
"""Render the league charter as plain markdown, for group chats and Sleeper.

Reads the same charter_spec.json as the HTML and PDF renderers, so the copy
managers paste into a chat says exactly what the published page says. Standard
library only.

Usage: python3 build_charter_md.py charter_spec.json charter.md
"""

import json
import sys

# Section 0 holds the cheat-sheet numbers and is unnumbered in prose.
NUMBERS_HEADING = "Quick Numbers"


def para_text(b):
    """Paragraph text, with an optional `link` phrase as a markdown link."""
    text = b["text"]
    link = b.get("link")
    if not link:
        return text
    phrase = link["phrase"]
    if phrase not in text:
        raise SystemExit("link phrase %r is not in the paragraph text" % phrase)
    return text.replace(phrase, "[%s](%s)" % (phrase, link["url"]), 1)


def cell(text):
    """A pipe inside a value would end the column early, so escape it.
    The Payouts row ("1st $1,200 | 2nd $600 | 3rd $200") is why."""
    return text.replace("|", "\\|")


def render_rows(header, rows):
    """A markdown table. An empty header renders as a headerless two-column
    table, which is how the numbers cheat sheet reads best."""
    width = max(len(r) for r in rows)
    head = list(header) + [""] * (width - len(header))
    out = ["| %s |" % " | ".join(cell(h) for h in head),
           "|%s|" % "|".join(["---"] * width)]
    for r in rows:
        cells = list(r) + [""] * (width - len(r))
        out.append("| %s |" % " | ".join(cell(c) for c in cells))
    return out


def render_block(b):
    kind = b["type"]

    if kind == "para":
        return [para_text(b)]

    if kind == "sub":
        return ["**%s**" % b["text"]]

    if kind == "note":
        # Bold, so a rule with consequences still reads as one in plain text.
        return ["**%s**" % b["text"]]

    if kind == "bullets":
        return ["- %s" % i for i in b["items"]]

    if kind == "kv":
        return render_rows([], b["rows"])

    if kind == "table":
        return render_rows(b["header"], b["rows"])

    return []


def build(spec):
    out = ["# %s %s" % (spec["title"], spec["subtitle"]), "", spec["preamble"]]

    for sec in spec["sections"]:
        out += ["", "---", ""]
        if sec["num"] == 0:
            out.append("## %s" % NUMBERS_HEADING)
        else:
            out.append("## %d. %s" % (sec["num"], sec["name"]))
        for b in sec["blocks"]:
            lines = render_block(b)
            if lines:
                out.append("")
                out += lines

    out += ["", "---", "", "*%s*" % spec["colophon"], ""]
    return "\n".join(out)


def main(spec_path, out_path):
    # Never the platform default: Windows reads UTF-8 files as cp1252 and
    # fails on the first character outside that set.
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build(spec))
    print("wrote", out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
