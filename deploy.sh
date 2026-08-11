#!/usr/bin/env bash
# Create the GitHub repo, push this folder, turn on Pages, and wait for it
# to go live. Safe to run more than once: it reuses whatever already exists.
#
#   ./deploy.sh [repo-name] [public|private]

set -euo pipefail

REPO="${1:-buschhh-league-charter}"
VIS="${2:-public}"
DESC="Buschhhhhhhhhhhh League dynasty charter"

say()  { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
fail() { printf '\n\033[1;31mFAILED:\033[0m %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------- checks

for tool in git gh python3 curl; do
  command -v "$tool" >/dev/null 2>&1 || fail "$tool is not installed.
  git:     https://git-scm.com/downloads
  gh:      https://cli.github.com
  python3: https://python.org/downloads"
done

gh auth status >/dev/null 2>&1 || fail "Not signed in to GitHub.
  Run:  gh auth login
  Choose HTTPS and 'Login with a web browser' when prompted, then rerun this."

[ -f index.html ] && [ -f charter_spec.json ] \
  || fail "Run this from the folder that contains index.html and charter_spec.json."

OWNER="$(gh api user --jq .login)"
say "Signed in as $OWNER"

# ---------------------------------------------------------------- repo

if gh repo view "$OWNER/$REPO" >/dev/null 2>&1; then
  say "Repo $OWNER/$REPO already exists, reusing it"
else
  say "Creating $OWNER/$REPO ($VIS)"
  gh repo create "$OWNER/$REPO" "--$VIS" --description "$DESC" >/dev/null
fi

# ---------------------------------------------------------------- push

[ -d .git ] || { say "Initializing git"; git init -q -b main; }

git config user.name  >/dev/null 2>&1 || git config user.name  "$OWNER"
git config user.email >/dev/null 2>&1 || git config user.email "$OWNER@users.noreply.github.com"

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "https://github.com/$OWNER/$REPO.git"
else
  git remote add origin "https://github.com/$OWNER/$REPO.git"
fi

git add -A
if git diff --cached --quiet 2>/dev/null; then
  say "Nothing new to commit"
else
  git commit -q -m "Publish league charter"
fi
git branch -M main

say "Pushing to GitHub"
git push -q -u origin main

# ---------------------------------------------------------------- pages

say "Enabling GitHub Pages"
PAGES_BODY='{"source":{"branch":"main","path":"/"}}'

if gh api "repos/$OWNER/$REPO/pages" >/dev/null 2>&1; then
  echo "    Pages already on, confirming the source branch"
  gh api --method PUT "repos/$OWNER/$REPO/pages" \
    --input - <<<"$PAGES_BODY" >/dev/null 2>&1 || true
else
  gh api --method POST "repos/$OWNER/$REPO/pages" \
    --input - <<<"$PAGES_BODY" >/dev/null \
    || fail "Could not enable Pages. If this repo is private, GitHub Pages
  needs a paid plan. Rerun as public:  ./deploy.sh $REPO public"
fi

URL="$(gh api "repos/$OWNER/$REPO/pages" --jq .html_url)"
[ -n "$URL" ] || fail "Pages is on but GitHub has not reported a URL yet. Wait a minute and rerun."

# ---------------------------------------------------------------- previews

say "Baking the absolute URL into the link-preview tags"
python3 tools/build_charter_html.py charter_spec.json index.html "$URL"
git add index.html
if git diff --cached --quiet 2>/dev/null; then
  echo "    Already correct"
else
  git commit -q -m "Absolute URLs for link previews"
  git push -q
fi

# ---------------------------------------------------------------- wait

say "Waiting for the first deploy (up to 5 minutes)"
for _ in $(seq 1 30); do
  CODE="$(curl -s -o /dev/null -w '%{http_code}' "$URL" || echo 000)"
  if [ "$CODE" = "200" ]; then
    printf '\n\033[1;32mLive:\033[0m %s\n\n' "$URL"
    echo "Try these:"
    echo "  ${URL}#trades"
    echo "  ${URL}#toilet-bowl"
    echo
    echo "To amend later: edit charter_spec.json, then run ./update.sh"
    exit 0
  fi
  printf '.'
  sleep 10
done

printf '\n'
say "Still building. This is normal on a brand new repo."
echo "It should appear within a few minutes at: $URL"
echo "Check progress: https://github.com/$OWNER/$REPO/actions"
