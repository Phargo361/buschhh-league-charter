#!/usr/bin/env python3
"""Render the 1200x630 social preview card from the same spec.

Reuses the PS2 title screen so the shared link looks like the document.
Usage: python3 make_card.py charter_spec.json card.png
"""
import json, subprocess, sys, tempfile, os
from reportlab.pdfgen import canvas
import build_charter_ps2 as ps2

def main(spec_path, out_png):
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    ps2.PAGE_W, ps2.PAGE_H = 1200, 630          # px at 72dpi
    tmp = tempfile.mkdtemp()
    pdf = os.path.join(tmp, "card.pdf")
    c = canvas.Canvas(pdf, pagesize=(ps2.PAGE_W, ps2.PAGE_H))
    ps2.draw_title_screen(c, spec)
    c.save()
    subprocess.run(["pdftoppm", "-png", "-r", "72", "-singlefile",
                    pdf, out_png[:-4]], check=True)
    print("wrote", out_png)

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
