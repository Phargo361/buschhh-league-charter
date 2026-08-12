#!/usr/bin/env python3
"""Render the league charter as a single self-contained HTML file.

Reads the same charter_spec.json as the PDF renderers. No external assets,
no network calls: the output opens offline from a phone, laptop, or Drive.

Usage: python3 build_charter_html.py charter_spec.json out.html
"""

import html
import json
import re
import sys


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def esc(text):
    return html.escape(text, quote=False)


# ---------------------------------------------------------------- blocks


def render_menu_row(label, value, cal=None):
    """One config row. `cal` is (iso_date, title, note) for an optional
    add-to-calendar button, which the League Dates section uses."""
    button = ""
    if cal and cal[0]:
        button = (
            '<button class="cal" type="button" data-date="%s" data-title="%s" '
            'data-note="%s" title="Add to calendar" '
            'aria-label="Add %s to calendar">+</button>'
            % (html.escape(cal[0], quote=True), html.escape(cal[1], quote=True),
               html.escape(cal[2] or "", quote=True),
               html.escape(cal[1], quote=True))
        )
    return (
        '<div class="row">'
        '<span class="row-label">%s</span>'
        '<span class="row-dots" aria-hidden="true"></span>'
        '<span class="row-value">%s</span>%s'
        "</div>" % (esc(label), esc(value), button)
    )


def render_caption(text):
    return '<div class="caption"><span>%s</span></div>' % esc(text)


def render_para_text(b):
    """Escaped paragraph text, with an optional `link` phrase anchored.

    A `para` may carry {"link": {"phrase": ..., "url": ...}}. The phrase must
    appear in `text`; the first occurrence becomes the anchor. The PDF
    builders ignore the key and render the phrase as plain words.
    """
    out = esc(b["text"])
    link = b.get("link")
    if not link:
        return out
    phrase = esc(link["phrase"])
    if phrase not in out:
        raise SystemExit(
            "link phrase %r is not in the paragraph text" % link["phrase"]
        )
    anchor = '<a href="%s" target="_blank" rel="noopener">%s</a>' % (
        html.escape(link["url"], quote=True),
        phrase,
    )
    return out.replace(phrase, anchor, 1)


def render_block(b):
    kind = b["type"]

    if kind == "para":
        return "<p>%s</p>" % render_para_text(b)

    if kind == "sub":
        return render_caption(b["text"])

    if kind == "note":
        return (
            '<div class="callout" role="note">'
            '<span class="callout-mark" aria-hidden="true">!</span>'
            "<p>%s</p></div>" % esc(b["text"])
        )

    if kind == "bullets":
        items = "".join("<li>%s</li>" % esc(i) for i in b["items"])
        return "<ul>%s</ul>" % items

    if kind == "kv":
        rows = "".join(render_menu_row(k, v) for k, v in b["rows"])
        return '<div class="rows">%s</div>' % rows

    if kind == "table":
        hdr = b["header"]
        # Parallel to rows when present; see build_dates.py.
        ics = b.get("ics_dates") or []
        out = []
        if len(hdr) == 2:
            out.append(render_caption("%s  /  %s" % (hdr[0], hdr[1])))
            rows = "".join(render_menu_row(r[0], r[1]) for r in b["rows"])
        else:
            out.append(render_caption(hdr[0]))
            if ics:
                out.append(
                    '<button class="cal-all" type="button">'
                    "Add all %d dates to a calendar</button>" % len(ics)
                )
            parts = []
            for i, r in enumerate(b["rows"]):
                note = r[2] if len(r) > 2 else ""
                date = ics[i] if i < len(ics) else ""
                parts.append(render_menu_row(
                    r[0], r[1], cal=(date, r[0], note) if date else None))
                if note:
                    parts.append('<p class="row-note">%s</p>' % esc(note))
            rows = "".join(parts)
        out.append('<div class="rows">%s</div>' % rows)
        return "".join(out)

    return ""


# ---------------------------------------------------------------- shell

CSS = """
:root{
  --bg-deep:#04081a; --bg-mid:#0d1e48; --glow:#1b3f86;
  --panel:rgba(14,32,74,.86); --panel-2:rgba(8,18,46,.86);
  --cyan:#7cdcf7; --cyan-dim:#3e7fc4; --edge:#28518f;
  --text:#eaf2ff; --dim:#8fa8d6; --amber:#ffc94a; --sel:rgba(46,102,194,.55);
  --ui:"Segoe UI",Roboto,"Helvetica Neue",Arial,system-ui,sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;padding:0;overflow-x:hidden;max-width:100%}
body{
  background:var(--bg-deep); color:var(--text); font-family:var(--ui);
  font-size:15px; line-height:1.55; min-height:100vh;
  -webkit-font-smoothing:antialiased;
}
/* CRT atmosphere: radial glow under scanlines */
body::before,body::after{content:"";position:fixed;inset:0;pointer-events:none}
body::before{
  background:
    radial-gradient(60% 55% at 62% 45%,rgba(27,63,134,.55),transparent 70%),
    linear-gradient(180deg,#04081a 0%,#0d1e48 45%,#04081a 100%);
  z-index:-2;
}
body::after{
  background:repeating-linear-gradient(
    180deg,rgba(0,0,0,.17) 0 1px,transparent 1px 3px);
  z-index:3; opacity:.55;
}
.wrap{max-width:1180px;margin:0 auto;padding:18px 16px 90px;position:relative;z-index:1;width:100%}

/* window chrome */
.win{
  background:var(--panel); border:1.5px solid var(--cyan); border-radius:8px;
  box-shadow:inset 0 0 0 3px rgba(40,81,143,.9),0 0 26px rgba(20,60,140,.35);
}
header.bar{display:flex;align-items:center;gap:16px;padding:12px 18px;margin-bottom:16px}
.bar .kicker{
  color:var(--cyan); font-weight:700; font-size:17px; letter-spacing:.22em;
}
.bar .divider{width:1px;align-self:stretch;background:var(--edge)}
.bar .current{font-weight:700;font-size:15px;letter-spacing:.04em}

.layout{display:grid;grid-template-columns:250px minmax(0,1fr);gap:16px;align-items:start}

/* sidebar */
nav.side{padding:10px}
.search{
  width:100%;margin:2px 0 8px;padding:8px 10px;border-radius:5px;
  background:rgba(4,10,28,.75);border:1px solid var(--edge);
  color:var(--text);font-family:inherit;font-size:13px;
}
.search::placeholder{color:#6f88b6}
.search:focus{outline:2px solid var(--cyan);outline-offset:1px}
nav.side ul{list-style:none;margin:0;padding:0}
nav.side button{
  display:flex;align-items:center;gap:9px;width:100%;
  background:none;border:0;border-radius:4px;cursor:pointer;
  padding:7px 9px;color:var(--dim);font-family:inherit;font-size:13px;
  font-weight:600;letter-spacing:.06em;text-align:left;text-transform:uppercase;
}
nav.side button .cursor{color:var(--amber);opacity:0;font-size:11px}
nav.side button:hover{color:var(--text);background:rgba(46,102,194,.22)}
nav.side button[aria-selected="true"]{background:var(--sel);color:#fff}
nav.side button[aria-selected="true"] .cursor{opacity:1}
nav.side button:focus-visible{outline:2px solid var(--cyan);outline-offset:-2px}
nav.side li.hidden{display:none}
.no-match{color:var(--dim);font-size:12px;padding:8px 9px}

/* panel */
main.panel{padding:18px 22px 24px;min-height:66vh}
.panel-head{
  display:flex;align-items:baseline;gap:12px;
  padding-bottom:10px;margin-bottom:14px;border-bottom:1px solid var(--edge);
}
.panel-head .tag{color:var(--amber);font-weight:700;font-size:14px}
.panel-head h1{margin:0;font-size:21px;letter-spacing:.14em;font-weight:700}
.sect[hidden]{display:none}
.sect{animation:slide-in .19s ease-out}
@keyframes slide-in{
  from{opacity:0;transform:translateX(var(--from,14px))}
  to{opacity:1;transform:none}
}
.sect p{margin:0 0 11px}
.sect p a{color:var(--cyan);text-decoration:none;border-bottom:1px dotted var(--cyan-dim)}
.sect p a:hover,.sect p a:focus-visible{color:#fff;border-bottom-color:#fff}

/* the signature: dotted-leader config rows */
.rows{margin:6px 0 14px}
.row{display:flex;align-items:baseline;gap:8px;padding:4px 6px;border-radius:4px}
.row:hover{background:rgba(46,102,194,.18)}
.row-label{flex:0 1 auto}
.row-dots{
  flex:1 1 auto;min-width:20px;transform:translateY(-4px);
  border-bottom:1.5px dotted rgba(110,142,196,.6);
}
.row-value{
  flex:0 0 auto;color:var(--amber);font-weight:700;
  font-variant-numeric:tabular-nums;text-align:right;
}
.row-note{margin:-2px 0 8px 14px;color:var(--dim);font-size:13.5px}

/* add-to-calendar */
.row .cal{
  flex:0 0 auto;margin-left:9px;width:21px;height:21px;padding:0;line-height:1;
  background:transparent;border:1px solid var(--edge);border-radius:3px;
  color:var(--cyan);font-family:inherit;font-size:14px;font-weight:700;
  cursor:pointer;
}
.row .cal:hover{background:var(--sel);color:#fff;border-color:var(--cyan)}
.row .cal:focus-visible{outline:2px solid var(--cyan);outline-offset:1px}
.row .cal.done{color:var(--amber);border-color:var(--amber)}
.cal-all{
  display:inline-block;margin:2px 0 10px;padding:6px 11px;
  background:transparent;border:1px solid var(--edge);border-radius:4px;
  color:var(--cyan);font-family:inherit;font-size:12px;font-weight:600;
  letter-spacing:.06em;text-transform:uppercase;cursor:pointer;
}
.cal-all:hover{background:var(--sel);color:#fff;border-color:var(--cyan)}
.cal-all:focus-visible{outline:2px solid var(--cyan);outline-offset:1px}

.caption{display:flex;align-items:center;gap:10px;margin:16px 0 6px}
.caption span{
  color:var(--cyan);font-size:11.5px;font-weight:700;
  letter-spacing:.16em;text-transform:uppercase;white-space:nowrap;
}
.caption::after{content:"";flex:1;height:1px;background:var(--edge)}

.sect ul{margin:4px 0 12px;padding-left:18px;list-style:none}
.sect ul li{position:relative;padding-left:14px;margin-bottom:6px}
.sect ul li::before{
  content:"\\25B8";position:absolute;left:0;color:var(--cyan);font-size:12px;
}

.callout{
  display:flex;gap:11px;margin:14px 0;padding:12px 14px;border-radius:5px;
  background:rgba(92,66,15,.62);border:1px solid var(--amber);
}
.callout p{margin:0;color:#ffe9b0}
.callout-mark{color:var(--amber);font-weight:700}

/* footer status bar */
footer.hud{
  position:fixed;left:0;right:0;bottom:0;z-index:4;
  display:flex;align-items:center;gap:14px;
  padding:9px 20px;font-size:12px;color:var(--dim);
  background:linear-gradient(180deg,rgba(4,8,26,0),rgba(4,8,26,.94) 42%);
}
footer .count{margin:0 auto;font-variant-numeric:tabular-nums}
footer .hints{display:flex;gap:14px}
footer .hints.touch{display:none}
footer .glyph{color:var(--cyan);font-weight:700}
footer kbd{
  background:rgba(46,102,194,.3);border:1px solid var(--edge);border-radius:3px;
  padding:0 5px;font:inherit;font-size:11px;color:var(--text);
}

@media (max-width:820px){
  .layout{grid-template-columns:minmax(0,1fr)}
  nav.side{position:sticky;top:8px;z-index:2}
  nav.side ul{display:flex;gap:6px;overflow-x:auto;padding-bottom:4px}
  nav.side li{flex:0 0 auto}
  nav.side button{white-space:nowrap;font-size:12px}
  nav.side button .cursor{display:none}
  main.panel{padding:16px 15px 20px}
  footer .hints{display:none}
  footer .hints.touch{display:flex}
  footer.hud>span:first-child{display:none}
  footer .hints.touch span{white-space:nowrap}
  footer.hud{justify-content:space-between;padding:9px 16px}
  .row{flex-wrap:wrap}
  .row-dots{min-width:12px}
  .row-value{margin-left:auto}
  /* League Dates pairs a long label with a long date, and adds a button.
     Let a label wrap rather than push a row wider than the screen. */
  .row-label{min-width:0;overflow-wrap:anywhere}
  .rows{min-width:0}
  .layout{min-width:0}
  nav.side{min-width:0}
  nav.side ul{min-width:0}
  main.panel{min-width:0;overflow-wrap:break-word}
}

@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}

/* printing falls back to a plain, complete document */
@media print{
  body{background:#fff;color:#000}
  body::before,body::after{display:none}
  nav.side,footer.hud,.search,header.bar{display:none}
  .layout{display:block}
  .win{border:0;box-shadow:none;background:#fff}
  .sect[hidden]{display:block!important}
  .sect{break-inside:avoid;margin-bottom:22px}
  .panel-head h1,.panel-head .tag{color:#000}
  .row-value{color:#000}
  .caption span{color:#000}
  .callout{background:#f4f4f4;border:1px solid #999}
  .callout p{color:#000}
  .row-dots{border-bottom:1px dotted #999}
  .cal,.cal-all{display:none}
  .sect p a{color:#000;border-bottom:1px solid #999}
  .sect p a::after{content:" (" attr(href) ")";font-size:.85em;color:#444}
}
"""

JS = """
/* Add to calendar. The .ics is built here rather than linking out to a
   calendar service, so the page keeps working offline and sends nobody's
   league schedule to a third party. All-day events, per RFC 5545: DTEND is
   exclusive, so it is the day after DTSTART. */
(function(){
  var LEAGUE = 'Buschhhhhhhhhhhh League';

  function fold(line){
    /* RFC 5545 caps a content line at 75 octets; continuations start with a
       space. Plain ASCII here, so characters and octets are the same. */
    if(line.length <= 75) return line;
    var out = [line.slice(0, 75)];
    for(var i = 75; i < line.length; i += 74){
      out.push(' ' + line.slice(i, i + 74));
    }
    return out.join('\\r\\n');
  }

  function esc(text){
    return String(text || '')
      .replace(/\\\\/g, '\\\\\\\\')
      .replace(/;/g, '\\\\;')
      .replace(/,/g, '\\\\,')
      .replace(/\\r?\\n/g, '\\\\n');
  }

  function compact(iso){ return iso.replace(/-/g, ''); }

  function dayAfter(iso){
    var d = new Date(iso + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + 1);
    return compact(d.toISOString().slice(0, 10));
  }

  function stamp(){
    return new Date().toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';
  }

  function build(events){
    var now = stamp();
    var lines = ['BEGIN:VCALENDAR', 'VERSION:2.0',
                 'PRODID:-//' + LEAGUE + '//Charter//EN',
                 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH'];
    events.forEach(function(e, i){
      lines.push('BEGIN:VEVENT');
      lines.push('UID:' + compact(e.date) + '-' + i + '@buschhh-league');
      lines.push('DTSTAMP:' + now);
      lines.push('DTSTART;VALUE=DATE:' + compact(e.date));
      lines.push('DTEND;VALUE=DATE:' + dayAfter(e.date));
      lines.push('SUMMARY:' + esc(LEAGUE + ': ' + e.title));
      if(e.note) lines.push('DESCRIPTION:' + esc(e.note));
      lines.push('TRANSP:TRANSPARENT');
      lines.push('END:VEVENT');
    });
    lines.push('END:VCALENDAR');
    return lines.map(fold).join('\\r\\n') + '\\r\\n';
  }

  function save(name, text){
    var blob = new Blob([text], {type: 'text/calendar;charset=utf-8'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function(){ URL.revokeObjectURL(url); a.remove(); }, 0);
  }

  function slugify(text){
    return text.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(
      /^-|-$/g, '');
  }

  function read(btn){
    return {date: btn.dataset.date, title: btn.dataset.title,
            note: btn.dataset.note};
  }

  document.addEventListener('click', function(ev){
    var one = ev.target.closest && ev.target.closest('.cal');
    if(one){
      var e = read(one);
      save(slugify(e.title) + '.ics', build([e]));
      one.classList.add('done');
      return;
    }
    var all = ev.target.closest && ev.target.closest('.cal-all');
    if(all){
      var section = all.closest('.sect');
      var events = Array.prototype.slice.call(
        section.querySelectorAll('.cal')).map(read);
      if(events.length) save('league-dates.ics', build(events));
    }
  });
})();

(function(){
  var buttons = Array.prototype.slice.call(
    document.querySelectorAll('nav.side button'));
  var panels = Array.prototype.slice.call(
    document.querySelectorAll('.sect'));
  var current = document.getElementById('current');
  var count = document.getElementById('count');
  var search = document.getElementById('search');
  var idx = 0;

  function show(i, push){
    if(i < 0 || i >= panels.length) return;
    var dir = i > idx ? 1 : -1;
    idx = i;
    panels[i].style.setProperty('--from', dir > 0 ? '16px' : '-16px');
    buttons.forEach(function(b, n){
      b.setAttribute('aria-selected', n === i ? 'true' : 'false');
    });
    panels.forEach(function(p, n){ p.hidden = n !== i; });
    var sec = panels[i];
    current.textContent = sec.dataset.name.toUpperCase();
    count.textContent = (i + 1) + ' / ' + panels.length;
    if(push && location.hash !== '#' + sec.id){
      try { history.replaceState(null, '', '#' + sec.id); }
      catch(err) { /* some browsers block this on file:// */ }
    }
    var list = buttons[i].parentNode.parentNode;
    if(list.scrollWidth > list.clientWidth + 2){
      list.scrollLeft = buttons[i].offsetLeft
        - (list.clientWidth - buttons[i].offsetWidth) / 2;
    } else {
      buttons[i].scrollIntoView({block:'nearest'});
    }
    window.scrollTo({top:0});
  }

  buttons.forEach(function(b, n){
    b.addEventListener('click', function(){ show(n, true); });
  });

  document.addEventListener('keydown', function(e){
    if(e.target === search){
      if(e.key === 'Escape'){ search.value=''; filter(''); search.blur(); }
      if(e.key === 'Enter'){
        var first = buttons.findIndex(function(b){
          return !b.parentNode.classList.contains('hidden'); });
        if(first > -1){ show(first, true); search.blur(); }
      }
      return;
    }
    if(e.key === 'ArrowDown' || e.key === 'j'){ e.preventDefault(); show(idx+1,true); }
    else if(e.key === 'ArrowUp' || e.key === 'k'){ e.preventDefault(); show(idx-1,true); }
    else if(e.key === 'Home'){ e.preventDefault(); show(0,true); }
    else if(e.key === 'End'){ e.preventDefault(); show(panels.length-1,true); }
    else if(e.key === '/'){ e.preventDefault(); search.focus(); search.select(); }
  });

  // Swipe left for the next section, right for the previous. Ignores
  // gestures that start in the nav strip, which scrolls horizontally itself,
  // and gestures that are mostly vertical, which are page scrolls.
  var sx = 0, sy = 0, st = 0, tracking = false;
  document.addEventListener('touchstart', function(e){
    if(e.touches.length !== 1 || (e.target.closest &&
       (e.target.closest('nav.side') || e.target.closest('input')))){
      tracking = false; return;
    }
    sx = e.touches[0].clientX; sy = e.touches[0].clientY;
    st = Date.now(); tracking = true;
  }, {passive:true});

  document.addEventListener('touchend', function(e){
    if(!tracking) return;
    tracking = false;
    var t = e.changedTouches[0];
    var dx = t.clientX - sx, dy = t.clientY - sy;
    if(Date.now() - st > 700) return;
    if(Math.abs(dx) < 55) return;
    if(Math.abs(dx) < Math.abs(dy) * 1.6) return;
    var next = dx < 0 ? idx + 1 : idx - 1;
    if(next < 0 || next >= panels.length) return;
    show(next, true);
  }, {passive:true});

  function filter(q){
    q = q.trim().toLowerCase();
    var any = false;
    buttons.forEach(function(b, n){
      var hay = (b.textContent + ' ' + panels[n].textContent).toLowerCase();
      var hit = !q || hay.indexOf(q) > -1;
      b.parentNode.classList.toggle('hidden', !hit);
      if(hit) any = true;
    });
    document.getElementById('nomatch').hidden = any;
  }
  search.addEventListener('input', function(){ filter(search.value); });

  function fromHash(){
    var id = location.hash.replace('#','');
    var n = panels.findIndex(function(p){ return p.id === id; });
    show(n > -1 ? n : 0, false);
  }
  window.addEventListener('hashchange', fromHash);
  fromHash();
})();
"""


def build(spec, base=""):
    secs = spec["sections"]

    nav = []
    for s in secs:
        nav.append(
            '<li><button role="tab" aria-controls="%s" aria-selected="false">'
            '<span class="cursor" aria-hidden="true">&#9654;</span>'
            "<span>%s</span></button></li>" % (slug(s["name"]), esc(s["name"]))
        )

    panels = []
    for s in secs:
        tag = "%02d" % s["num"] if s["num"] else "&#9670;"
        body = "".join(render_block(b) for b in s["blocks"])
        panels.append(
            '<section class="sect" id="%s" role="tabpanel" data-name="%s" '
            "hidden>"
            '<div class="panel-head"><span class="tag">%s</span>'
            "<h1>%s</h1></div>%s</section>"
            % (slug(s["name"]), esc(s["name"]), tag,
               esc(s["name"].upper()), body)
        )

    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s Charter</title>
<meta name="description" content="%(preamble)s">
<meta name="theme-color" content="#0d1e48">
<meta property="og:type" content="website">
<meta property="og:title" content="%(title)s Charter">
<meta property="og:description" content="%(preamble)s">
<meta property="og:image" content="%(base)scard.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="%(title)s Charter">
<meta name="twitter:description" content="%(preamble)s">
<meta name="twitter:image" content="%(base)scard.png">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='6' fill='%%230d1e48'/><path d='M11 8l10 8-10 8z' fill='%%23ffc94a'/></svg>">
<style>%(css)s</style>
</head>
<body>
<div class="wrap">

  <header class="bar win">
    <span class="kicker">CONFIG</span>
    <span class="divider"></span>
    <span class="current" id="current">THE NUMBERS</span>
  </header>

  <div class="layout">
    <nav class="side win" role="tablist" aria-label="Charter sections">
      <input class="search" id="search" type="search"
             placeholder="Search the charter" aria-label="Search the charter">
      <ul>%(nav)s</ul>
      <p class="no-match" id="nomatch" hidden>Nothing matches. Try fewer words.</p>
    </nav>

    <main class="panel win">%(panels)s</main>
  </div>
</div>

<footer class="hud">
  <span>%(title)s &middot; CHARTER</span>
  <span class="count" id="count"></span>
  <span class="hints">
    <span><kbd>&uarr;</kbd><kbd>&darr;</kbd> Move</span>
    <span><kbd>/</kbd> Search</span>
    <span><span class="glyph">&#9675;</span> Confirm</span>
  </span>
  <span class="hints touch"><span>&#8592; Swipe to change &#8594;</span></span>
</footer>

<script>%(js)s</script>
</body>
</html>
""" % {
        "base": base,
        "title": esc(spec["title"]),
        "preamble": esc(spec["preamble"]),
        "css": CSS,
        "js": JS,
        "nav": "".join(nav),
        "panels": "".join(panels),
    }


def main(spec_path, out_path, base=""):
    """base: optional absolute site URL, e.g. https://user.github.io/repo/

    Chat apps and social scrapers need absolute URLs for preview images.
    Left empty, the page still works; the preview image just may not resolve.
    """
    if base and not base.endswith("/"):
        base += "/"
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(build(spec, base))
    print("wrote", out_path, ("(base: %s)" % base) if base else "(relative URLs)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2],
         sys.argv[3] if len(sys.argv) > 3 else "")
