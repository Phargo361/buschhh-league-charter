#!/usr/bin/env bash
# Rebuild every format from charter_spec.json and push the changes.
#   ./update.sh ["commit message"]

set -euo pipefail
MSG="${1:-Amend charter}"

say() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }

command -v python3 >/dev/null || { echo "python3 required"; exit 1; }
[ -f charter_spec.json ] || { echo "Run this from the repo folder."; exit 1; }

# reuse whatever base URL is already baked into the page
BASE="$(grep -o 'property="og:image" content="[^"]*card.png"' index.html 2>/dev/null \
        | sed 's/.*content="//; s/card\.png"//' || true)"

say "Rebuilding the web page"
python3 tools/build_charter_html.py charter_spec.json index.html "$BASE"

say "Rebuilding the plain-text copy"
python3 tools/build_charter_md.py charter_spec.json charter.md

if python3 -c "import reportlab" 2>/dev/null; then
  say "Rebuilding PDFs and the preview card"
  python3 tools/build_charter_ps2.py charter_spec.json pdf/charter-ps2.pdf
  python3 tools/build_charter.py     charter_spec.json pdf/charter-greek.pdf
  python3 tools/make_card.py         charter_spec.json card.png
else
  say "reportlab not installed, skipping PDFs (pip install reportlab to include them)"
fi

git add -A
if git diff --cached --quiet 2>/dev/null; then
  say "No changes"
  exit 0
fi
git commit -q -m "$MSG"
git push -q
say "Pushed. The site updates in about a minute."
