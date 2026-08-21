# Buschhhhhhhhhhhh League Charter

The league charter, published as a navigable web page.

**Live:** `https://YOUR-USERNAME.github.io/REPO-NAME/`

---

## Publishing this

```bash
gh auth login      # once, if you have not already
./deploy.sh
```

That creates the repo, pushes this folder, turns on GitHub Pages, and prints
the live URL. Safe to rerun.

See `START-HERE.md` for the version with no assumed terminal knowledge, and
for how to hand the job to Claude Code instead.

---

## Card Lookup

`cards/index.html` is a second page on this site, at `/cards/`. It prices 2025
Panini Score football cards against the SportsCardsPro API: search a player,
pick the card, pick the version pulled.

It is **not** generated from `charter_spec.json`, and `update.sh` does not touch
it. Edit it directly.

The league's SportsCardsPro token is embedded in the page so it works with
nothing typed in. **That token is therefore public**: this is a public repo and
a public site, so anyone who views source can read it and spend the league's API
quota against it. That trade was made on purpose. Rotate the token on the
SportsCardsPro subscription page if it starts getting abused, and update
`BAKED` in `cards/index.html`.

A reader may paste their own token to use that instead. It is kept in their
browser and overrides the embedded one.

---

## Amending the charter

`charter_spec.json` is the single source of truth. Every format is generated
from it. Never hand-edit the HTML, the markdown, or the PDFs, because the
next build overwrites them.

1. Edit `charter_spec.json`.
2. Rebuild and publish:

```bash
./update.sh "what changed"
```

That regenerates the page, the PDF, and the preview card, then pushes.

Requires Python 3 and `reportlab` (`pip install reportlab`) for the PDF
builder. The HTML and markdown builders need only the standard library.

### Spec structure

Each entry in `sections` has a number, a name, and a list of content
blocks. Block types:

| Type | Renders as |
|---|---|
| `para` | A paragraph |
| `sub` | A small cyan caption bar |
| `bullets` | A bulleted list |
| `kv` | Config rows: label, dotted leader, value |
| `table` | A caption plus config rows |
| `note` | An amber callout, for rules with teeth |

---

## What's in here

| Path | What it is |
|---|---|
| `index.html` | The charter. One file, no dependencies, works offline. |
| `charter_spec.json` | Source of truth. Edit this. |
| `charter.md` | Generated. Plain markdown, for pasting into Sleeper or a group chat. |
| `pdf/charter-ps2.pdf` | Print/archive copy, PS2 config menu styling. |
| `card.png` | Link preview image. |
| `tools/` | The generators. |

## Using the page

- Click a category, or use the arrow keys.
- Press `/` to search the full text of every section.
- On a phone, swipe left or right to change sections.
- Every section has its own link. Copy the address bar to send someone a
  specific rule, for example `#trades` or `#toilet-bowl`.
- Print, or save as PDF from the browser, to get all sections as one plain
  black-on-white document.

## Settled questions

Both of the charter's long-standing gaps are now written into the spec:

- **Taxi squad deadline.** A rookie must be on the taxi squad before the
  third NFL preseason game. Section 6.
- **Playoff draft slot tiebreak.** Teams knocked out in the same playoff
  round are ordered by playoff seed. The better seed takes the lower slot
  number and picks later. Section 7.
