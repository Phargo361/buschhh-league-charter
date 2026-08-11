#!/usr/bin/env python3
"""Render the league charter as an ancient Greek text.

Single source of truth: charter_spec.json
Usage: python3 build_charter.py charter_spec.json out.pdf
"""

import json
import random
import sys

from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageTemplate,
    CondPageBreak, Paragraph, Spacer, Table, TableStyle,
)

# ---------------------------------------------------------------- palette

PARCHMENT = Color(0.906, 0.859, 0.749)
PARCH_DK = Color(0.847, 0.784, 0.655)
INK = Color(0.153, 0.118, 0.086)
INK_SOFT = Color(0.365, 0.298, 0.227)
OXBLOOD = Color(0.494, 0.176, 0.129)
RULE = Color(0.545, 0.463, 0.353)

PAGE_W, PAGE_H = letter
MARGIN = 1.02 * inch

# ---------------------------------------------------------------- fonts

FONTS = {
    "Serif": "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
    "Serif-Bold": "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    "Serif-Italic": "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf",
}
for name, path in FONTS.items():
    pdfmetrics.registerFont(TTFont(name, path))
pdfmetrics.registerFontFamily(
    "Serif", normal="Serif", bold="Serif-Bold", italic="Serif-Italic"
)

GREEK_NUM = {
    1: "Α", 2: "Β", 3: "Γ", 4: "Δ", 5: "Ε", 6: "Ϛ",
    7: "Ζ", 8: "Η", 9: "Θ", 10: "Ι", 11: "ΙΑ", 12: "ΙΒ",
}


def track(text, spaces=1):
    """Letterspace a string for inscriptional display type.

    ReportLab's paragraph parser collapses runs of en/thin spaces, so word
    gaps use non-breaking spaces, which survive intact.
    """
    gap = "\u2009" * spaces
    wordgap = "\u00a0" * (3 + spaces)
    return wordgap.join(gap.join(list(w)) for w in text.split(" ") if w)


def track_dotted(text, spaces=2):
    """Letterspaced with interpuncts between words, as on Greek inscriptions."""
    gap = "\u2009" * spaces
    sep = "\u00a0\u00b7\u00a0"
    return sep.join(gap.join(list(w)) for w in text.split(" ") if w)


# ---------------------------------------------------------------- page furniture


def draw_parchment(canv):
    """Aged papyrus ground: base tone, mottling, edge burn."""
    canv.saveState()
    canv.setFillColor(PARCHMENT)
    canv.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    rng = random.Random(20260810)
    for _ in range(340):
        x = rng.uniform(0, PAGE_W)
        y = rng.uniform(0, PAGE_H)
        r = rng.uniform(6, 58)
        a = rng.uniform(0.012, 0.05)
        canv.setFillColor(Color(0.62, 0.53, 0.38, alpha=a))
        canv.circle(x, y, r, stroke=0, fill=1)

    # darker burn toward the edges
    for i in range(26):
        t = i / 26.0
        inset = t * 0.62 * inch
        canv.setFillColor(Color(0.55, 0.45, 0.30, alpha=0.016))
        canv.rect(inset, inset, PAGE_W - 2 * inset, PAGE_H - 2 * inset,
                  stroke=0, fill=1)
    canv.restoreState()


def meander_run(canv, x, y, length, unit, thickness, color, flip=False):
    """Horizontal Greek key (meander) band, drawn left to right."""
    canv.saveState()
    canv.setStrokeColor(color)
    canv.setLineWidth(thickness)
    canv.setLineCap(0)
    canv.setLineJoin(0)

    s = unit / 6.0
    n = int(length // unit)
    sign = -1 if flip else 1

    canv.line(x, y, x + n * unit, y)
    for i in range(n):
        x0 = x + i * unit
        pts = [(0, 0), (0, 5), (4, 5), (4, 1), (2, 1), (2, 3)]
        p = canv.beginPath()
        p.moveTo(x0 + pts[0][0] * s, y + sign * pts[0][1] * s)
        for px, py in pts[1:]:
            p.lineTo(x0 + px * s, y + sign * py * s)
        canv.drawPath(p, stroke=1, fill=0)
    canv.restoreState()


def meander_column(canv, x, y, height, unit, thickness, color, flip=False):
    """Vertical meander band, drawn bottom to top."""
    canv.saveState()
    canv.translate(x, y)
    canv.rotate(90)
    meander_run(canv, 0, 0, height, unit, thickness, color, flip=flip)
    canv.restoreState()


def draw_border(canv, unit=9.0):
    """Meander frame on all four sides plus a hairline inner rule."""
    m = 0.50 * inch
    w = PAGE_W - 2 * m
    h = PAGE_H - 2 * m

    meander_run(canv, m, m, w, unit, 0.9, INK_SOFT, flip=False)
    meander_run(canv, m, PAGE_H - m, w, unit, 0.9, INK_SOFT, flip=True)
    meander_column(canv, m, m, h, unit, 0.9, INK_SOFT, flip=True)
    meander_column(canv, PAGE_W - m, m, h, unit, 0.9, INK_SOFT, flip=False)

    canv.saveState()
    canv.setStrokeColor(RULE)
    canv.setLineWidth(0.5)
    inset = m + 0.24 * inch
    canv.rect(inset, inset, PAGE_W - 2 * inset, PAGE_H - 2 * inset,
              stroke=1, fill=0)
    canv.restoreState()


def draw_folio(canv, doc):
    """Page number as a Greek numeral between two dots."""
    n = canv.getPageNumber()
    if n == 1:
        return
    label = GREEK_NUM.get(n, str(n))
    canv.saveState()
    canv.setFont("Serif", 9.5)
    canv.setFillColor(INK_SOFT)
    canv.drawCentredString(PAGE_W / 2, 0.90 * inch, "\u00b7 %s \u00b7" % label)
    canv.restoreState()


def on_page(canv, doc):
    draw_parchment(canv)
    draw_border(canv)
    draw_folio(canv, doc)


def on_title_page(canv, doc):
    draw_parchment(canv)
    draw_border(canv, unit=11.0)


# ---------------------------------------------------------------- flowables


class Rule(Flowable):
    """Thin horizontal rule, optionally with a centered diamond."""

    def __init__(self, width, thickness=0.6, color=RULE, diamond=False,
                 align="CENTER"):
        Flowable.__init__(self)
        self.hAlign = align
        self.width = width
        self.thickness = thickness
        self.color = color
        self.diamond = diamond
        self.height = 6 if diamond else thickness

    def draw(self):
        c = self.canv
        c.setStrokeColor(self.color)
        c.setLineWidth(self.thickness)
        y = self.height / 2.0
        if self.diamond:
            gap = 9
            mid = self.width / 2.0
            c.line(0, y, mid - gap, y)
            c.line(mid + gap, y, self.width, y)
            c.setFillColor(self.color)
            p = c.beginPath()
            p.moveTo(mid, y + 3.2)
            p.lineTo(mid + 3.2, y)
            p.lineTo(mid, y - 3.2)
            p.lineTo(mid - 3.2, y)
            p.close()
            c.drawPath(p, stroke=0, fill=1)
        else:
            c.line(0, y, self.width, y)


class SectionHead(Flowable):
    """Greek numeral, tracked English title, Greek subtitle, closing rule."""

    def __init__(self, width, num, name, greek):
        Flowable.__init__(self)
        self.width = width
        self.num = num
        self.name = name
        self.greek = greek
        self.height = 54

    def draw(self):
        c = self.canv
        top = self.height

        if self.num:
            numeral = GREEK_NUM.get(self.num, str(self.num)) + "\u0384"
            c.setFont("Serif-Bold", 15)
            c.setFillColor(OXBLOOD)
            c.drawString(0, top - 20, numeral)
            offset = c.stringWidth(numeral, "Serif-Bold", 15) + 13
        else:
            offset = 0

        c.setFont("Serif-Bold", 15.5)
        c.setFillColor(INK)
        c.drawString(offset, top - 20, track(self.name.upper(), 2))

        c.setFont("Serif", 9)
        c.setFillColor(INK_SOFT)
        c.drawString(offset, top - 34, track(self.greek, 1))

        c.setStrokeColor(RULE)
        c.setLineWidth(0.7)
        c.line(0, top - 45, self.width, top - 45)
        c.setLineWidth(0.4)
        c.line(0, top - 48, self.width, top - 48)


# ---------------------------------------------------------------- styles

CONTENT_W = PAGE_W - 2 * MARGIN

body = ParagraphStyle(
    "body", fontName="Serif", fontSize=10.4, leading=15.6,
    textColor=INK, alignment=TA_JUSTIFY, spaceAfter=7,
)
bullet = ParagraphStyle(
    "bullet", parent=body, leftIndent=18, bulletIndent=5, spaceAfter=5,
    bulletFontName="Serif-Bold", bulletFontSize=8.5, bulletColor=OXBLOOD,
)
sub = ParagraphStyle(
    "sub", fontName="Serif-Bold", fontSize=10.2, leading=14,
    textColor=OXBLOOD, spaceBefore=6, spaceAfter=4,
)
note = ParagraphStyle(
    "note", fontName="Serif-Italic", fontSize=10.2, leading=15.2,
    textColor=INK, alignment=TA_JUSTIFY,
    leftIndent=14, rightIndent=14, spaceBefore=5, spaceAfter=7,
)
preamble = ParagraphStyle(
    "preamble", fontName="Serif-Italic", fontSize=11.6, leading=18,
    textColor=INK, alignment=TA_CENTER,
)
colophon = ParagraphStyle(
    "colophon", fontName="Serif-Italic", fontSize=9.6, leading=14,
    textColor=INK_SOFT, alignment=TA_CENTER,
)


def table_style(header=True):
    cmds = [
        ("FONTNAME", (0, 0), (-1, -1), "Serif"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.8),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, RULE),
    ]
    if header:
        cmds += [
            ("FONTNAME", (0, 0), (-1, 0), "Serif-Bold"),
            ("TEXTCOLOR", (0, 0), (-1, 0), OXBLOOD),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK_SOFT),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [PARCHMENT, Color(0.87, 0.81, 0.69, alpha=0.45)]),
        ]
    else:
        cmds += [("ROWBACKGROUNDS", (0, 0), (-1, -1),
                  [PARCHMENT, Color(0.87, 0.81, 0.69, alpha=0.45)])]
    cmds += [("LINEABOVE", (0, 0), (-1, 0), 0.8, INK_SOFT),
             ("LINEBELOW", (0, -1), (-1, -1), 0.8, INK_SOFT)]
    return TableStyle(cmds)


def cell(text, bold=False, color=None):
    st = ParagraphStyle(
        "cell", fontName="Serif-Bold" if bold else "Serif",
        fontSize=9.8, leading=13.2, textColor=color or INK,
    )
    return Paragraph(text, st)


# ---------------------------------------------------------------- build


def build_blocks(blocks):
    out = []
    for b in blocks:
        kind = b["type"]
        if kind == "para":
            out.append(Paragraph(b["text"], body))
        elif kind == "sub":
            out.append(Paragraph(track(b["text"].upper(), 1), sub))
        elif kind == "note":
            out.append(Rule(CONTENT_W * 0.26, 0.5, RULE))
            out.append(Paragraph(b["text"], note))
            out.append(Rule(CONTENT_W * 0.26, 0.5, RULE))
            out.append(Spacer(1, 4))
        elif kind == "bullets":
            for item in b["items"]:
                out.append(Paragraph(item, bullet, bulletText="\u2022"))
            out.append(Spacer(1, 4))
        elif kind == "kv":
            data = [[cell(k, bold=True), cell(v)] for k, v in b["rows"]]
            t = Table(data, colWidths=[CONTENT_W * 0.34, CONTENT_W * 0.66])
            t.setStyle(table_style(header=False))
            out.append(t)
            out.append(Spacer(1, 8))
        elif kind == "table":
            widths = [CONTENT_W * w for w in b["widths"]]
            data = [[cell(h, bold=True, color=OXBLOOD) for h in b["header"]]]
            data += [[cell(c) for c in row] for row in b["rows"]]
            t = Table(data, colWidths=widths, repeatRows=1)
            t.setStyle(table_style(header=True))
            out.append(t)
            out.append(Spacer(1, 9))
    return out


def title_page(spec):
    story = [Spacer(1, 1.55 * inch)]

    st_greek = ParagraphStyle(
        "tg", fontName="Serif", fontSize=13, leading=20,
        textColor=OXBLOOD, alignment=TA_CENTER,
    )
    story.append(Paragraph(track_dotted(spec["greek_title"], 2), st_greek))
    story.append(Spacer(1, 20))
    story.append(Rule(CONTENT_W, 0.8, INK_SOFT, diamond=True))
    story.append(Spacer(1, 26))

    st_title = ParagraphStyle(
        "tt", fontName="Serif-Bold", fontSize=25, leading=34,
        textColor=INK, alignment=TA_CENTER,
    )
    for word in spec["title"].upper().split(" "):
        story.append(Paragraph(track(word, 1), st_title))
    story.append(Spacer(1, 12))

    st_sub = ParagraphStyle(
        "ts", fontName="Serif", fontSize=17, leading=24,
        textColor=INK_SOFT, alignment=TA_CENTER,
    )
    story.append(Paragraph(track(spec["subtitle"].upper(), 4), st_sub))
    story.append(Spacer(1, 26))
    story.append(Rule(CONTENT_W, 0.8, INK_SOFT, diamond=True))
    story.append(Spacer(1, 38))

    story.append(Paragraph(spec["preamble"], preamble))
    story.append(Spacer(1, 46))
    story.append(Rule(CONTENT_W * 0.42, 0.5, RULE))
    story.append(Spacer(1, 10))
    story.append(Paragraph(spec["colophon"], colophon))
    return story


def main(spec_path, out_path):
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)

    doc = BaseDocTemplate(
        out_path, pagesize=letter,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=1.12 * inch,
        title="%s %s" % (spec["title"], spec["subtitle"]),
        author="League Commissioner",
    )
    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height, id="main",
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([
        PageTemplate(id="title", frames=[frame], onPage=on_title_page),
        PageTemplate(id="body", frames=[frame], onPage=on_page),
    ])

    story = title_page(spec)
    story.append(NextPageTemplateHack())

    for i, sec in enumerate(spec["sections"]):
        head = SectionHead(CONTENT_W, sec["num"], sec["name"], sec["greek"])
        # never strand a heading near the foot of a page
        story.append(CondPageBreak(1.7 * inch))
        story.append(head)
        story.append(Spacer(1, 3))
        story.extend(build_blocks(sec["blocks"]))
        if i < len(spec["sections"]) - 1:
            story.append(Spacer(1, 15))

    story.append(Spacer(1, 20))
    story.append(Rule(CONTENT_W * 0.42, 0.5, RULE))
    story.append(Spacer(1, 9))
    story.append(Paragraph(track("ΤΕΛΟΣ", 3), colophon))

    doc.build(story)
    print("wrote", out_path)


from reportlab.platypus import NextPageTemplate


def NextPageTemplateHack():
    return NextPageTemplate("body")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
