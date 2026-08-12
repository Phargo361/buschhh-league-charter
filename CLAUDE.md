# CLAUDE.md

Context for Claude Code working in this repository.

## What this is

The charter for a 10-team dynasty fantasy football league, published as a
GitHub Pages site. The page is a single self-contained HTML file styled as a
PS2-era RPG config menu.

## Your job on first run

Get this folder onto GitHub and published as a Pages site. `deploy.sh` does
the whole thing. Run it, watch the output, and fix whatever it reports.

```bash
./deploy.sh
```

It is idempotent. If it fails partway, fix the cause and run it again rather
than doing the remaining steps by hand.

### What deploy.sh does

1. Confirms `git`, `gh`, `python3`, and `curl` are present and that `gh` is
   authenticated.
2. Creates the repo, or reuses it if it already exists.
3. Commits and pushes this folder.
4. Turns on GitHub Pages from `main` at the repo root, via the REST API.
5. Reads the live URL, rebuilds `index.html` with that URL baked into the
   Open Graph tags so link previews resolve, then commits and pushes again.
6. Polls the URL until it returns 200, then prints it.

### Likely failure points

- **`gh` not authenticated.** Tell the user to run `gh auth login`, pick
  HTTPS and browser login. Do not try to work around this.
- **Repo name taken.** Rerun with a different name: `./deploy.sh other-name`.
- **Pages 404s for a few minutes.** Normal on a new repo. The script already
  waits five minutes. Beyond that, check
  `https://github.com/OWNER/REPO/actions`.
- **Private repo.** Pages on private repos requires a paid plan. Use public.

## The rule that matters most

`charter_spec.json` is the single source of truth. `index.html`, `charter.md`,
the PDF, and `card.png` are all generated from it.

**Never hand-edit `index.html`, `charter.md`, the PDF, or `card.png`.** The
next build overwrites them. To change the charter, edit `charter_spec.json`
and run:

```bash
./update.sh "what changed"
```

If asked to change how something *looks* rather than what it *says*, edit the
generator in `tools/`, then rebuild.

## Layout

| Path | Role |
|---|---|
| `charter_spec.json` | Source of truth. All content lives here. |
| `index.html` | Generated. The published page. |
| `card.png` | Generated. Link preview image, 1200x630. |
| `charter.md` | Generated. Plain text for group chats and Sleeper. |
| `pdf/` | Generated. Styled archive copy. |
| `tools/build_dates.py` | Derives the League Dates section from a season's anchors. |
| `tools/fetch_anchors.py` | Pulls preseason and Week 1 dates from ESPN. |
| `tools/roll_season.py` | Decides whether the next season can be rolled in. |
| `.github/workflows/roll-season.yml` | Weekly job that opens the rollover PR. |
| `tools/build_charter_html.py` | HTML generator. Standard library only. |
| `tools/build_charter_md.py` | Markdown generator. Standard library only. |
| `tools/build_charter_ps2.py` | PS2-styled PDF. Needs reportlab. |
| `tools/make_card.py` | Preview card. Needs reportlab and poppler. |
| `deploy.sh` | First-time publish. |
| `update.sh` | Rebuild and push after an amendment. |

## Spec format

`sections` is an ordered list. Each has `num`, `name`, and `blocks`.
Block types and what they render as:

| `type` | Renders as |
|---|---|
| `para` | Paragraph. Needs `text`. |
| `sub` | Small cyan caption bar. Needs `text`. |
| `bullets` | Bulleted list. Needs `items`. |
| `kv` | Config rows with dotted leaders. Needs `rows` as `[label, value]` pairs. |
| `table` | Caption plus config rows. Needs `header` and `rows`. |
| `note` | Amber callout, used for rules with consequences. Needs `text`. |

Two- and three-column tables both render as config rows. A third column
becomes a dim sub-line under its row.

A `table` may also carry `ics_dates`, a list of ISO dates parallel to `rows`.
The HTML build hangs an add-to-calendar button off each row and generates the
`.ics` in the browser, so the page still works offline and no one's schedule
leaves the device. The other renderers ignore the key. `build_dates.py` emits
it; nothing else should.

A `para` may also carry an optional `link`:

```json
{"type": "para", "text": "Exact dates are posted in the league Google Sheet.",
 "link": {"phrase": "league Google Sheet", "url": "https://..."}}
```

The phrase must appear in `text`, and its first occurrence becomes the link.
The web page and `charter.md` render it as a link; the two PDFs ignore the key
and print the phrase as plain words, because a raw URL would wreck the
config-menu layout. The page prints the URL in parentheses on paper.

## The League Dates section

Never hand-edit it. `seasons.<year>` in the spec holds three NFL anchor dates
and nothing else; `build_dates.py` derives every league date from them using
the rules in the charter, so the calendar cannot disagree with the rules.

    python3 tools/build_dates.py charter_spec.json 2027

Change a rule that a date depends on, and the derivation in `build_dates.py`
has to change with it. The comments there name the section each rule lives in.

A weekly GitHub Action rolls the next season in on its own. It fetches the
preseason and Week 1 anchors from ESPN once the NFL publishes the schedule
around May, opens a pull request rather than pushing, and files an issue
asking for `nfl_draft_end`, which is the one date no API provides.

## House style for the charter text

- Written at a 7th grade reading level. Short sentences, plain words.
- Third person throughout. Never "you". Use "a team", "a manager", "the
  league".
- No em-dashes.
- Numbers stay in the `Quick Numbers` section as well as in their own
  section, so the top screen works as a cheat sheet. If a number changes,
  change it in both places.

## Open questions

None outstanding. If a new one appears, record it here rather than inventing
an answer, and ask the Commissioner.

### Settled

- **Taxi squad deadline.** A rookie must be on the taxi squad before the
  third NFL preseason game. In section 6.
- **Playoff draft slot tiebreak.** Two teams are knocked out in each playoff
  round; they are ordered by playoff seed, and the better seed takes the
  lower slot number and so picks later. In section 7.
