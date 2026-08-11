#!/usr/bin/env python3
"""Render the league charter as a PS2-era JRPG config menu.

Reads the same charter_spec.json as the other renderers.
Usage: python3 build_charter_ps2.py charter_spec.json out.pdf
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontpaths

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer,
)

# ---------------------------------------------------------------- screen

PAGE_W, PAGE_H = 10 * inch, 7.5 * inch          # 4:3, like a CRT

SIDEBAR_X = 0.42 * inch
SIDEBAR_W = 2.45 * inch
PANEL_X = 3.05 * inch
PANEL_W = PAGE_W - PANEL_X - 0.42 * inch
PANEL_TOP = PAGE_H - 1.18 * inch
PANEL_BOT = 0.88 * inch
TITLE_BAND = 0.62 * inch                         # section title inside panel

FRAME_X = PANEL_X + 0.28 * inch
FRAME_W = PANEL_W - 0.56 * inch
FRAME_TOP = PANEL_TOP - TITLE_BAND
FRAME_BOT = PANEL_BOT + 0.26 * inch
FRAME_H = FRAME_TOP - FRAME_BOT

# ---------------------------------------------------------------- palette

BG_DEEP = HexColor("#04081A")
BG_MID = HexColor("#0D1E48")
BG_GLOW = HexColor("#1B3F86")
PANEL_FILL = Color(0.055, 0.125, 0.290, alpha=0.86)
PANEL_FILL2 = Color(0.031, 0.070, 0.180, alpha=0.86)
CYAN = HexColor("#7CDCF7")
CYAN_DIM = HexColor("#3E7FC4")
EDGE = HexColor("#28518F")
TEXT = HexColor("#EAF2FF")
TEXT_DIM = HexColor("#8FA8D6")
AMBER = HexColor("#FFC94A")
SEL_FILL = Color(0.180, 0.400, 0.760, alpha=0.55)
WHITE = HexColor("#FFFFFF")

# DejaVu first, then whatever sans the platform ships.
# Condensed faces fall back to regular when unavailable.
FONTS = {
    "UI": fontpaths.require(
        "the body face", "DejaVuSans.ttf", "verdana.ttf", "arial.ttf",
        "segoeui.ttf", "Arial Unicode.ttf"),
    "UI-Bold": fontpaths.require(
        "the bold face", "DejaVuSans-Bold.ttf", "verdanab.ttf", "arialbd.ttf",
        "segoeuib.ttf"),
    "UI-Cond": fontpaths.require(
        "the condensed face", "DejaVuSansCondensed.ttf", "arialn.ttf",
        "DejaVuSans.ttf", "verdana.ttf", "arial.ttf", "segoeui.ttf"),
    "UI-CondBold": fontpaths.require(
        "the condensed bold face", "DejaVuSansCondensed-Bold.ttf",
        "arialnb.ttf", "DejaVuSans-Bold.ttf", "verdanab.ttf", "arialbd.ttf",
        "segoeuib.ttf"),
}
for name, path in FONTS.items():
    pdfmetrics.registerFont(TTFont(name, path))
pdfmetrics.registerFontFamily("UI", normal="UI", bold="UI-Bold")


def track(text, gap=1):
    return ("\u2009" * gap).join(list(text))


# ---------------------------------------------------------------- chrome


def draw_background(canv):
    """CRT-ish gradient, glow, scanlines, vignette."""
    canv.saveState()
    canv.setFillColor(BG_DEEP)
    canv.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)

    # vertical gradient band
    steps = 90
    for i in range(steps):
        t = i / float(steps - 1)
        y = PAGE_H * t
        f = 1.0 - abs(t - 0.42) / 0.72
        f = max(f, 0.0)
        canv.setFillColor(Color(BG_MID.red, BG_MID.green, BG_MID.blue,
                                alpha=0.85 * f))
        canv.rect(0, y, PAGE_W, PAGE_H / steps + 1, stroke=0, fill=1)

    # soft glow behind the main panel
    for i in range(26):
        t = i / 26.0
        r = (1.0 - t) * 3.7 * inch
        canv.setFillColor(Color(BG_GLOW.red, BG_GLOW.green, BG_GLOW.blue,
                                alpha=0.030))
        canv.circle(PAGE_W * 0.63, PAGE_H * 0.52, r, stroke=0, fill=1)

    # scanlines
    canv.setStrokeColor(Color(0, 0, 0, alpha=0.16))
    canv.setLineWidth(0.9)
    y = 0
    while y < PAGE_H:
        canv.line(0, y, PAGE_W, y)
        y += 3.0

    # vignette
    for i in range(20):
        t = i / 20.0
        inset = t * 1.5 * inch
        canv.setFillColor(Color(0, 0, 0, alpha=0.018))
        canv.rect(-inset, -inset, PAGE_W + 2 * inset, PAGE_H + 2 * inset,
                  stroke=0, fill=1)
    canv.restoreState()


def bevel_box(canv, x, y, w, h, r=6, fill=PANEL_FILL, edge=CYAN,
              inner=True, lw=1.4):
    """Translucent window with a bright outer edge and dim inner rule."""
    canv.saveState()
    canv.setFillColor(fill)
    canv.setStrokeColor(edge)
    canv.setLineWidth(lw)
    canv.roundRect(x, y, w, h, r, stroke=1, fill=1)
    if inner:
        canv.setStrokeColor(Color(EDGE.red, EDGE.green, EDGE.blue, alpha=0.9))
        canv.setLineWidth(0.7)
        canv.roundRect(x + 3, y + 3, w - 6, h - 6, max(r - 2, 1),
                       stroke=1, fill=0)
    canv.restoreState()


def draw_header(canv, section_name):
    """Top status bar: CONFIG label plus current category."""
    x, y = 0.42 * inch, PAGE_H - 0.98 * inch
    w, h = PAGE_W - 0.84 * inch, 0.60 * inch
    bevel_box(canv, x, y, w, h, r=5, fill=Color(0.043, 0.098, 0.235, alpha=0.92))

    canv.saveState()
    label = track("CONFIG", 2)
    canv.setFont("UI-Bold", 15)
    canv.setFillColor(CYAN)
    canv.drawString(x + 16, y + h / 2 - 6, label)
    div = x + 16 + pdfmetrics.stringWidth(label, "UI-Bold", 15) + 18

    canv.setStrokeColor(EDGE)
    canv.setLineWidth(1)
    canv.line(div, y + 10, div, y + h - 10)

    canv.setFont("UI-Bold", 13)
    canv.setFillColor(TEXT)
    canv.drawString(div + 16, y + h / 2 - 5, section_name.upper())

    canv.restoreState()


def draw_sidebar(canv, items, current):
    """Category list with the active row highlighted and a cursor."""
    top = PANEL_TOP
    row_h = 0.315 * inch
    h = row_h * len(items) + 0.30 * inch
    y0 = top - h
    bevel_box(canv, SIDEBAR_X, y0, SIDEBAR_W, h, r=5, fill=PANEL_FILL2)

    canv.saveState()
    for i, label in enumerate(items):
        ry = top - 0.15 * inch - (i + 1) * row_h
        if i == current:
            canv.setFillColor(SEL_FILL)
            canv.roundRect(SIDEBAR_X + 6, ry + 2, SIDEBAR_W - 12,
                           row_h - 3, 3, stroke=0, fill=1)
            canv.setFillColor(AMBER)
            canv.setFont("UI-Bold", 9)
            canv.drawString(SIDEBAR_X + 12, ry + 7.5, "\u25b6")
            canv.setFillColor(WHITE)
            canv.setFont("UI-Bold", 9.6)
        else:
            canv.setFillColor(TEXT_DIM)
            canv.setFont("UI", 9.4)
        canv.drawString(SIDEBAR_X + 26, ry + 7.5, label.upper())
    canv.restoreState()


def draw_panel(canv, section_name, num):
    bevel_box(canv, PANEL_X, PANEL_BOT, PANEL_W, PANEL_TOP - PANEL_BOT,
              r=7, fill=PANEL_FILL)
    canv.saveState()
    ty = PANEL_TOP - 0.40 * inch
    canv.setFillColor(AMBER)
    canv.setFont("UI-Bold", 11)
    tag = "%02d" % num if num else "\u25c6"
    canv.drawString(PANEL_X + 0.28 * inch, ty, tag)

    canv.setFillColor(WHITE)
    canv.setFont("UI-Bold", 15)
    canv.drawString(PANEL_X + 0.62 * inch, ty, track(section_name.upper(), 1))

    canv.setStrokeColor(EDGE)
    canv.setLineWidth(0.8)
    canv.line(PANEL_X + 0.26 * inch, ty - 12,
              PANEL_X + PANEL_W - 0.26 * inch, ty - 12)
    canv.restoreState()


def draw_footer(canv, page, total):
    canv.saveState()
    y = 0.34 * inch
    canv.setFont("UI", 9.2)
    canv.setFillColor(TEXT_DIM)
    canv.drawString(0.46 * inch, y, "MEMORY CARD (8MB)  \u00b7  SLOT 1  \u00b7  SAVED")

    hints = [("\u25cb", "CONFIRM"), ("\u2715", "BACK"), ("\u25b3", "RULES")]
    x = PAGE_W - 0.46 * inch
    for glyph, label in reversed(hints):
        canv.setFont("UI", 9.2)
        canv.setFillColor(TEXT_DIM)
        canv.drawRightString(x, y, label)
        x -= pdfmetrics.stringWidth(label, "UI", 9.2) + 7
        canv.setFont("UI-Bold", 10)
        canv.setFillColor(CYAN)
        canv.drawRightString(x, y - 0.5, glyph)
        x -= 20

    canv.setFont("UI", 9.2)
    canv.setFillColor(TEXT_DIM)
    canv.drawCentredString(PAGE_W / 2, y, "%d / %d" % (page, total))
    canv.restoreState()


# ---------------------------------------------------------------- flowables


class MenuRow(Flowable):
    """Label, dotted leader, right-aligned value. The signature config look."""

    def __init__(self, width, label, value, selected=False):
        Flowable.__init__(self)
        self.width = width
        self.label = label
        self.value = value
        self.selected = selected
        self.height = 17.5

    def draw(self):
        c = self.canv
        y = 5.0
        if self.selected:
            c.setFillColor(SEL_FILL)
            c.roundRect(-4, 1, self.width + 8, self.height - 3, 3,
                        stroke=0, fill=1)

        c.setFont("UI", 9.8)
        c.setFillColor(TEXT)
        c.drawString(0, y, self.label)
        lw = pdfmetrics.stringWidth(self.label, "UI", 9.8)

        c.setFont("UI-Bold", 9.8)
        vw = pdfmetrics.stringWidth(self.value, "UI-Bold", 9.8)

        x0 = lw + 8
        x1 = self.width - vw - 8
        if x1 > x0:
            c.setStrokeColor(Color(0.42, 0.55, 0.78, alpha=0.55))
            c.setLineWidth(0.9)
            c.setDash(0.9, 3.4)
            c.line(x0, y + 2.6, x1, y + 2.6)
            c.setDash()

        c.setFillColor(AMBER)
        c.drawRightString(self.width, y, self.value)


class GroupCaption(Flowable):
    """Small cyan caption bar above a group of menu rows."""

    def __init__(self, width, text):
        Flowable.__init__(self)
        self.width = width
        self.text = text
        self.height = 16

    def draw(self):
        c = self.canv
        c.setFillColor(CYAN)
        c.setFont("UI-Bold", 8.4)
        label = track(self.text.upper(), 1)
        c.drawString(0, 5, label)
        w = pdfmetrics.stringWidth(label, "UI-Bold", 8.4)
        c.setStrokeColor(Color(EDGE.red, EDGE.green, EDGE.blue, alpha=0.85))
        c.setLineWidth(0.7)
        c.line(w + 8, 8, self.width, 8)


class Callout(Flowable):
    """Amber warning box, for the rules that carry teeth."""

    def __init__(self, width, text, style):
        Flowable.__init__(self)
        self.width = width
        self.para = Paragraph(text, style)
        self.pad = 9
        self.height = 0

    def wrap(self, aw, ah):
        w, h = self.para.wrap(self.width - 2 * self.pad - 16, ah)
        self.height = h + 2 * self.pad
        return self.width, self.height

    def draw(self):
        c = self.canv
        c.setFillColor(Color(0.36, 0.26, 0.06, alpha=0.62))
        c.setStrokeColor(AMBER)
        c.setLineWidth(1.0)
        c.roundRect(0, 0, self.width, self.height, 4, stroke=1, fill=1)
        c.setFillColor(AMBER)
        c.setFont("UI-Bold", 11)
        c.drawString(self.pad + 1, self.height - self.pad - 9, "!")
        self.para.drawOn(c, self.pad + 16, self.pad)


class SectionMark(Flowable):
    """Zero-height marker: records which section owns which page."""

    def __init__(self, index, registry):
        Flowable.__init__(self)
        self.index = index
        self.registry = registry
        self.width = 0
        self.height = 0

    def draw(self):
        self.registry.setdefault(self.canv.getPageNumber(), self.index)


# ---------------------------------------------------------------- styles

body = ParagraphStyle(
    "body", fontName="UI", fontSize=9.9, leading=15.2,
    textColor=TEXT, alignment=TA_LEFT, spaceAfter=7,
)
bullet = ParagraphStyle(
    "bullet", parent=body, leftIndent=16, bulletIndent=2, spaceAfter=5,
    bulletFontName="UI-Bold", bulletFontSize=8, bulletColor=CYAN,
)
callout_style = ParagraphStyle(
    "callout", fontName="UI", fontSize=9.6, leading=14.4, textColor=HexColor("#FFE9B0"),
)
sub_style = ParagraphStyle(
    "sub", fontName="UI-Bold", fontSize=9.2, leading=13,
    textColor=CYAN, spaceBefore=5, spaceAfter=3,
)


def build_blocks(blocks):
    out = []
    for b in blocks:
        kind = b["type"]
        if kind == "para":
            out.append(Paragraph(b["text"], body))
        elif kind == "sub":
            out.append(GroupCaption(FRAME_W, b["text"]))
        elif kind == "note":
            out.append(Spacer(1, 3))
            out.append(Callout(FRAME_W, b["text"], callout_style))
            out.append(Spacer(1, 8))
        elif kind == "bullets":
            for item in b["items"]:
                out.append(Paragraph(item, bullet, bulletText="\u25b8"))
            out.append(Spacer(1, 4))
        elif kind == "kv":
            for i, (k, v) in enumerate(b["rows"]):
                out.append(MenuRow(FRAME_W, k, v, selected=(i == 0)))
            out.append(Spacer(1, 7))
        elif kind == "table":
            hdr = b["header"]
            if len(hdr) == 2:
                out.append(GroupCaption(FRAME_W, "%s  /  %s" % (hdr[0], hdr[1])))
                for i, row in enumerate(b["rows"]):
                    out.append(MenuRow(FRAME_W, row[0], row[1],
                                       selected=(i == 0)))
            else:
                out.append(GroupCaption(FRAME_W, hdr[0]))
                for i, row in enumerate(b["rows"]):
                    out.append(MenuRow(FRAME_W, row[0], row[1],
                                       selected=(i == 0)))
                    if len(row) > 2 and row[2]:
                        out.append(Paragraph(
                            '<font color="#8FA8D6">%s</font>' % row[2],
                            ParagraphStyle("eff", parent=body, fontSize=9.0,
                                           leading=12.6, leftIndent=14,
                                           spaceAfter=4)))
            out.append(Spacer(1, 7))
    return out


# ---------------------------------------------------------------- title screen


def draw_title_screen(canv, spec):
    draw_background(canv)

    cx = PAGE_W / 2
    # glow behind the wordmark
    for i in range(18):
        t = i / 18.0
        canv.setFillColor(Color(0.16, 0.42, 0.82, alpha=0.035))
        canv.circle(cx, PAGE_H * 0.66, (1 - t) * 3.4 * inch, stroke=0, fill=1)

    words = spec["title"].upper().split(" ")
    avail = PAGE_W - 1.4 * inch
    size = 30.0
    while size > 12 and max(
            pdfmetrics.stringWidth(track(w, 1), "UI-Bold", size)
            for w in words) > avail:
        size -= 0.5

    ty = PAGE_H * 0.78
    for w in words:
        canv.setFillColor(Color(0, 0, 0, alpha=0.55))
        canv.setFont("UI-Bold", size)
        canv.drawCentredString(cx + 2.0, ty - 2.0, track(w, 1))
        canv.setFillColor(WHITE)
        canv.drawCentredString(cx, ty, track(w, 1))
        ty -= size * 1.28

    canv.setFont("UI-Bold", 15)
    canv.setFillColor(CYAN)
    canv.drawCentredString(cx, ty - 6, track(spec["subtitle"].upper(), 5))

    canv.setStrokeColor(EDGE)
    canv.setLineWidth(1.1)
    canv.line(cx - 3.1 * inch, ty - 24, cx + 3.1 * inch, ty - 24)

    menu = [("START SEASON", False), ("LOAD ROSTER", False),
            ("CONFIG", True), ("EXIT LEAGUE", False)]
    y = PAGE_H * 0.38
    for label, sel in menu:
        if sel:
            canv.setFillColor(SEL_FILL)
            canv.roundRect(cx - 1.5 * inch, y - 5, 3.0 * inch, 22, 4,
                           stroke=0, fill=1)
            canv.setFillColor(AMBER)
            canv.setFont("UI-Bold", 11)
            canv.drawString(cx - 1.38 * inch, y + 1, "\u25b6")
            canv.setFillColor(WHITE)
            canv.setFont("UI-Bold", 12)
        else:
            canv.setFillColor(TEXT_DIM)
            canv.setFont("UI", 12)
        canv.drawCentredString(cx + 8, y + 1, track(label, 1))
        y -= 30

    canv.setFont("UI", 9.6)
    canv.setFillColor(TEXT_DIM)
    canv.drawCentredString(cx, 1.02 * inch, spec["preamble"])
    canv.setFillColor(CYAN)
    canv.setFont("UI-Bold", 10)
    canv.drawCentredString(cx, 0.66 * inch, track("PRESS  START", 1))


# ---------------------------------------------------------------- build


def make_doc(spec, out_path, registry, total_pages):
    labels = [s["name"] for s in spec["sections"]]

    def on_body(canv, doc):
        page = canv.getPageNumber()
        idx = registry.get(page, 0)
        sec = spec["sections"][idx]
        draw_background(canv)
        draw_header(canv, sec["name"])
        draw_sidebar(canv, labels, idx)
        draw_panel(canv, sec["name"], sec["num"])
        draw_footer(canv, page, total_pages or page)

    def on_title(canv, doc):
        draw_title_screen(canv, spec)

    doc = BaseDocTemplate(
        out_path, pagesize=(PAGE_W, PAGE_H),
        leftMargin=FRAME_X, rightMargin=PAGE_W - FRAME_X - FRAME_W,
        topMargin=PAGE_H - FRAME_TOP, bottomMargin=FRAME_BOT,
        title="%s %s" % (spec["title"], spec["subtitle"]),
        author="League Commissioner",
    )
    frame = Frame(FRAME_X, FRAME_BOT, FRAME_W, FRAME_H, id="main",
                  leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)
    doc.addPageTemplates([
        PageTemplate(id="title", frames=[frame], onPage=on_title),
        PageTemplate(id="body", frames=[frame], onPage=on_body),
    ])

    story = [NextPageTemplate("body"), PageBreak()]
    for i, sec in enumerate(spec["sections"]):
        story.append(SectionMark(i, registry))
        story.extend(build_blocks(sec["blocks"]))
        if i < len(spec["sections"]) - 1:
            story.append(PageBreak())
    doc.build(story)
    return doc.page


def main(spec_path, out_path):
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)

    # pass 1 discovers page -> section mapping and the page count
    registry = {}
    total = make_doc(spec, "/tmp/_ps2_pass1.pdf", registry, 0)
    # pass 2 renders with an accurate sidebar and footer counter
    make_doc(spec, out_path, registry, total)
    print("wrote", out_path, "pages:", total)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
