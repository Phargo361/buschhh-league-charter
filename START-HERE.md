# START HERE

This folder publishes the league charter as a website. Two ways to do it.

---

## Option A: hand it to Claude Code

1. Unzip this folder somewhere you can find it, for example your Desktop.

2. Open a terminal in that folder. On a Mac, drag the folder onto the
   Terminal icon, or type `cd ` and drag the folder into the window, then
   press Enter.

3. Start Claude Code:

   ```
   claude
   ```

4. Paste this:

   > Read CLAUDE.md, then publish this repo to GitHub Pages by running
   > ./deploy.sh. Walk me through anything you need from me, and tell me the
   > live URL when it is up.

Claude Code handles the rest, including installing the GitHub CLI and
walking you through signing in if you have not already.

---

## Option B: run it yourself

You need the GitHub CLI once:

- macOS: `brew install gh`
- Windows: `winget install GitHub.cli`
- Linux: https://cli.github.com

Then, from this folder:

```bash
gh auth login          # HTTPS, log in with a web browser
./deploy.sh
```

That is the whole thing. It prints the live URL when the site is up.

To use a different repo name:

```bash
./deploy.sh my-league-rules
```

If the terminal says `permission denied`, the zip dropped the executable
flag. Fix it once:

```bash
chmod +x deploy.sh update.sh
```

Or just run `bash deploy.sh` instead.

---

## After it is live

Share the URL. It works on any phone or computer, no app, no download.

Individual rules have their own links, so you can settle an argument by
sending the exact section:

```
https://YOU.github.io/REPO/#trades
https://YOU.github.io/REPO/#toilet-bowl
```

## Changing a rule later

Edit `charter_spec.json`, then:

```bash
./update.sh "raised the buy-in"
```

That rebuilds the website, both PDFs, and the link preview image, then pushes
everything. The site updates about a minute later.

Or tell Claude Code what changed and let it edit the spec for you.

**Do not edit `index.html` directly.** It is generated from
`charter_spec.json` and your edits would be erased on the next build.
