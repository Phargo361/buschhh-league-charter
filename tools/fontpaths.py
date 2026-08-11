#!/usr/bin/env python3
"""Locate TrueType fonts across Linux, macOS, and Windows.

The PDF builders originally hardcoded Linux paths, so they crashed anywhere
else. update.sh runs under `set -e`, which meant an amendment made on a
Windows machine aborted before it could commit or push. Standard library only.
"""

import os

WIN_FONTS = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
MAC_DIRS = ("/Library/Fonts", "/System/Library/Fonts/Supplemental",
            os.path.expanduser("~/Library/Fonts"))
LINUX_DIRS = ("/usr/share/fonts/truetype/dejavu",
              "/usr/share/fonts/truetype/freefont",
              "/usr/share/fonts/TTF",
              "/usr/local/share/fonts")


def candidates(*names):
    """Every plausible absolute path for the given font file names, in the
    order given, searched across each platform's font directories."""
    out = []
    for name in names:
        out.append(os.path.join(WIN_FONTS, name))
        for d in MAC_DIRS + LINUX_DIRS:
            out.append(os.path.join(d, name))
    return out


def find(*names):
    """The first font file among `names` that exists on this machine, or None.

    Names are tried in order, so list the preferred face first and the
    acceptable substitutes after it.
    """
    for path in candidates(*names):
        if os.path.isfile(path):
            return path
    return None


def require(label, *names):
    """Like find(), but fail with an explanation instead of a bare TTFError."""
    path = find(*names)
    if path:
        return path
    raise SystemExit(
        "Could not find a font for %s.\n"
        "Looked for: %s\n"
        "Install the DejaVu and FreeFont families, or run the PDF builders on\n"
        "a machine that has them. The web page and charter.md do not need "
        "fonts and build fine without this." % (label, ", ".join(names))
    )
