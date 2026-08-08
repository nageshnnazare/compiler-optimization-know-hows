#!/usr/bin/env python3
"""Generate the guide's SVG figures, tuned to the htmler blue theme.

The kit's grey/purple house style is re-hued to htmler's blue-forward palette.
Because the figures are inlined as static base64 images (no page CSS reaches
them), every colour is chosen to work on BOTH the dark (#0b0d12) and light
(#ffffff) themes at once. The trick: a mid-slate around luminance ~0.2 gives
roughly 4.3:1 contrast three ways — white text sitting on the fill, and the
same colour used as ink on either background.

  * slate blue  #6B7B94  (neutral boxes, connectors, axes, labels)
  * blue        #3E7CC0  (highlighted / "after" boxes)         + dark #2F5F98
  * teal        #1F918C  (positive "result" accent)
  * amber       #D9922B  (warning / spill; dark text on fill)
  * red         #D65A5F  (problem callouts)
  * muted       #9AA0B4  (captions)
  * white       #FFFFFF  (text inside dark fills)
  * 1.5pt wide rules, Aptos / system sans font stack

Run:  python3 scripts/gen_figures.py
Output: <chapter>/figures/*.svg
"""
import base64
import io
import os
import re

# ── House-style constants (htmler blue theme, dual light/dark legible) ───────
GREY = "#6B7B94"
GREY_D = "#55637A"
PURPLE = "#3E7CC0"
PURPLE_D = "#2F5F98"
TEAL = "#1F918C"
AMBER = "#D9922B"
RED = "#D65A5F"
WHITE = "#FFFFFF"
LIGHT = "#9AA0B4"
INK_DARK = "#1F2433"  # text on light (amber) fills
# Hand-drawn Excalidraw look: Virgil is embedded per-figure (see _font_face);
# 'Segoe Print'/cursive are only fallbacks if the embed ever fails.
FONT = "'Virgil','Segoe Print','Comic Sans MS',cursive"
RULE = 1.5  # pt wide rules

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "fonts", "Virgil.woff2")
_FACE_CACHE = {}


def _font_face(text):
    """Return a <style> block embedding a Virgil subset for `text`.

    The figures are inlined as base64 <img> data URIs, and browsers do not
    fetch external fonts for <img>-loaded SVGs — so the hand-drawn font must
    travel *inside* each SVG. We subset to the glyphs actually used to keep
    each figure tiny (~8-14 KB)."""
    # Subset to exactly the glyphs this figure uses (plus a space) so each
    # embedded font stays as small as possible.
    key = "".join(sorted(set(text) | {" "}))
    if key in _FACE_CACHE:
        return _FACE_CACHE[key]
    try:
        from fontTools import subset as _subset
        opts = _subset.Options()
        opts.flavor = "woff2"
        opts.desubroutinize = True
        opts.ignore_missing_unicodes = True
        font = _subset.load_font(FONT_PATH, opts)
        ss = _subset.Subsetter(options=opts)
        ss.populate(text=key)
        ss.subset(font)
        buf = io.BytesIO()
        font.save(buf)
        b64 = base64.b64encode(buf.getvalue()).decode()
        face = ("<style>@font-face{font-family:'Virgil';font-style:normal;"
                "font-weight:400;src:url(data:font/woff2;base64," + b64 +
                ") format('woff2');}</style>")
    except Exception as exc:  # pragma: no cover - fonttools optional
        print("  ! font embed skipped:", exc)
        face = ""
    _FACE_CACHE[key] = face
    return face


# ── Primitive builders ──────────────────────────────────────────────────────
def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def defs():
    """Arrowhead markers in each ink colour."""
    marks = []
    for name, col in (("g", GREY), ("p", PURPLE), ("t", TEAL),
                      ("r", RED), ("a", AMBER), ("l", LIGHT)):
        marks.append(
            f'<marker id="ah-{name}" viewBox="0 0 10 10" refX="8.5" refY="5" '
            f'markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse">'
            f'<path d="M0 0L10 5L0 10z" fill="{col}"/></marker>')
    return "<defs>" + "".join(marks) + "</defs>"


def rrect(x, y, w, h, fill, rx=9, stroke=None, sw=RULE, dash=None, opacity=None):
    s = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" ry="{rx}" '
         f'fill="{fill}"')
    if stroke:
        s += f' stroke="{stroke}" stroke-width="{sw}"'
    if dash:
        s += f' stroke-dasharray="{dash}"'
    if opacity is not None:
        s += f' opacity="{opacity}"'
    return s + "/>"


def tspan_lines(x, cy, lines, fill, size, weight, lh):
    """Vertically centred multiline <text>."""
    n = len(lines)
    y0 = cy - (n - 1) * lh / 2.0
    out = [f'<text x="{x}" y="{y0}" fill="{fill}" font-family="{FONT}" '
           f'font-size="{size}" font-weight="{weight}" text-anchor="middle" '
           f'dominant-baseline="central">']
    for i, ln in enumerate(lines):
        dy = 0 if i == 0 else lh
        out.append(f'<tspan x="{x}" dy="{dy}">{esc(ln)}</tspan>')
    out.append("</text>")
    return "".join(out)


def box(x, y, w, h, lines, fill=GREY, tcol=WHITE, size=13, weight=600,
        rx=9, lh=16, stroke=None, sw=RULE, dash=None):
    if isinstance(lines, str):
        lines = [lines]
    r = rrect(x, y, w, h, fill, rx=rx, stroke=stroke, sw=sw, dash=dash)
    t = tspan_lines(x + w / 2.0, y + h / 2.0, lines, tcol, size, weight, lh)
    return r + t


def obox(x, y, w, h, lines, stroke=GREY, tcol=GREY, size=13, weight=600,
         rx=9, lh=16, sw=RULE, dash=None, fill="none"):
    """Outlined box (transparent fill) with coloured text."""
    r = rrect(x, y, w, h, fill, rx=rx, stroke=stroke, sw=sw, dash=dash)
    t = tspan_lines(x + w / 2.0, y + h / 2.0, lines if isinstance(lines, list)
                    else [lines], tcol, size, weight, lh)
    return r + t


def text(x, y, s, fill=GREY, size=13, weight=600, anchor="middle",
         italic=False, mono=False):
    fam = ("'SFMono-Regular',ui-monospace,'JetBrains Mono',Consolas,monospace"
           if mono else FONT)
    st = ""  # italics disabled: the hand-drawn font is hard to read slanted
    return (f'<text x="{x}" y="{y}" fill="{fill}" font-family="{fam}" '
            f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"'
            f'{st} dominant-baseline="central">{esc(s)}</text>')


def line(x1, y1, x2, y2, col=GREY, sw=RULE, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" '
            f'stroke-width="{sw}"{d}/>')


def _mk(col):
    return {GREY: "g", PURPLE: "p", TEAL: "t", RED: "r", AMBER: "a",
            LIGHT: "l"}.get(col, "g")


def arrow(x1, y1, x2, y2, col=GREY, sw=RULE, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" '
            f'stroke-width="{sw}" marker-end="url(#ah-{_mk(col)})"{d}/>')


def path(d, col=GREY, sw=RULE, dash=None, arrow_end=False, fill="none"):
    dd = f' stroke-dasharray="{dash}"' if dash else ""
    m = f' marker-end="url(#ah-{_mk(col)})"' if arrow_end else ""
    return (f'<path d="{d}" fill="{fill}" stroke="{col}" stroke-width="{sw}"'
            f'{dd}{m}/>')


def cylinder(x, y, w, h, fill=GREY, tcol=WHITE, lines=None, size=12,
             stroke=None, sw=RULE):
    """Database / memory cylinder."""
    ry = min(h * 0.16, 14)
    st = (f' stroke="{stroke}" stroke-width="{sw}"') if stroke else ""
    body = (f'<path d="M{x} {y+ry} A{w/2} {ry} 0 0 0 {x+w} {y+ry} '
            f'L{x+w} {y+h-ry} A{w/2} {ry} 0 0 1 {x} {y+h-ry} Z" '
            f'fill="{fill}"{st}/>')
    top = (f'<ellipse cx="{x+w/2}" cy="{y+ry}" rx="{w/2}" ry="{ry}" '
           f'fill="{fill}"{st}/>')
    lip = (f'<path d="M{x} {y+ry} A{w/2} {ry} 0 0 0 {x+w} {y+ry}" '
           f'fill="none" stroke="{WHITE}" stroke-width="1" opacity="0.35"/>')
    t = ""
    if lines:
        t = tspan_lines(x + w / 2.0, y + h / 2.0 + ry / 2, lines, tcol, size,
                        600, 15)
    return body + top + lip + t


def svg(w, h, body, title=""):
    t = f"<title>{esc(title)}</title>" if title else ""
    used = "".join(re.findall(r'>([^<]*)<', body)) + title
    face = _font_face(used)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" font-family="{FONT}">{face}{t}{defs()}'
            f'{body}</svg>\n')


def write(rel_path, content):
    full = os.path.join(REPO_ROOT, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w") as f:
        f.write(content)
    print("wrote", rel_path, f"({len(content)} bytes)")


# ── 00 fundamentals ─────────────────────────────────────────────────────────
def fig_pipeline():
    W, H = 900, 300
    b = []
    b.append(text(W / 2, 24, "The compiler pipeline", GREY, 17, 700))
    y, bh = 60, 150
    xs = [30, 330, 630]
    bw = 240
    titles = [
        ("FRONTEND", ["lex \u2192 tokens", "parse \u2192 AST",
                      "sema \u2192 typed AST"], GREY),
        ("MID-END  \u00b7  the optimizer",
         ["high-level IR", "GIMPLE / LLVM IR", "analyses \u21c4 transforms"],
         PURPLE),
        ("BACKEND", ["low-level IR (RTL/MIR)", "instr-select \u00b7 regalloc",
                     "schedule \u2192 emit asm"], GREY),
    ]
    cy = y + bh / 2
    for (x, (ttl, rows, col)) in zip(xs, titles):
        b.append(rrect(x, y, bw, bh, col, rx=12))
        b.append(text(x + bw / 2, y + 26, ttl, WHITE, 13, 700))
        b.append(line(x + 20, y + 44, x + bw - 20, y + 44, WHITE, 1))
        for i, r in enumerate(rows):
            b.append(text(x + bw / 2, y + 70 + i * 24, r, WHITE, 12, 500))
    b.append(arrow(xs[0] + bw, cy, xs[1], cy, GREY, 2))
    b.append(text((xs[0] + bw + xs[1]) / 2, cy - 12, "lowering", GREY, 11, 600))
    b.append(arrow(xs[1] + bw, cy, xs[2], cy, GREY, 2))
    b.append(text((xs[1] + bw + xs[2]) / 2, cy - 12, "instr-sel", GREY, 11, 600))
    # source in / object out
    b.append(box(xs[0] - 0, y + bh + 40, 130, 40, "source.c", GREY_D,
                 size=13, rx=8))
    b.append(arrow(65, y + bh + 40, 65, y + bh + 6, GREY, 2))
    b.append(box(xs[2] + bw - 130, y + bh + 40, 130, 40, "object.o", GREY_D,
                 size=13, rx=8))
    b.append(arrow(xs[2] + bw - 65, y + bh + 6, xs[2] + bw - 65,
                   y + bh + 40, GREY, 2))
    write("00_fundamentals/figures/pipeline.svg",
          svg(W, H, "".join(b), "Compiler pipeline"))


def fig_cfg():
    W, H = 520, 380
    b = [text(W / 2, 24, "Control-flow graph (CFG)", GREY, 16, 700)]
    b.append(box(180, 50, 160, 56, ["BB1", "y = x + 1 ; br y>0"], GREY,
                 size=12, lh=15))
    b.append(box(70, 170, 150, 52, ["BB2", "y = y * 2"], PURPLE, size=12,
                 lh=15))
    b.append(box(300, 170, 150, 52, ["BB3", "y = -y"], PURPLE, size=12, lh=15))
    b.append(box(180, 290, 160, 52, ["BB4", "return y"], GREY, size=12, lh=15))
    # edges
    b.append(arrow(230, 106, 150, 170, GREY, RULE))
    b.append(text(160, 140, "true", GREY, 11, 600, anchor="end"))
    b.append(arrow(290, 106, 372, 170, GREY, RULE))
    b.append(text(360, 140, "false", GREY, 11, 600, anchor="start"))
    b.append(arrow(145, 222, 235, 290, GREY, RULE))
    b.append(arrow(375, 222, 285, 290, GREY, RULE))
    write("00_fundamentals/figures/cfg.svg", svg(W, H, "".join(b), "CFG"))


def fig_ssa():
    W, H = 560, 400
    b = [text(W / 2, 24, "SSA form with a \u03c6-node", GREY, 16, 700)]
    b.append(box(190, 50, 180, 56, ["BB1", "y\u2081 = x + 1 ; br y\u2081>0"],
                 GREY, size=12, lh=15))
    b.append(box(60, 165, 170, 50, ["BB2", "y\u2082 = y\u2081 * 2"], PURPLE,
                 size=12, lh=15))
    b.append(box(330, 165, 170, 50, ["BB3", "y\u2083 = \u2212y\u2081"], PURPLE,
                 size=12, lh=15))
    b.append(box(140, 290, 280, 72,
                 ["BB4", "y\u2084 = \u03c6( y\u2082 from BB2,",
                  "         y\u2083 from BB3 )", "return y\u2084"],
                 GREY_D, size=12, lh=15))
    b.append(arrow(245, 106, 150, 165, GREY))
    b.append(arrow(315, 106, 410, 165, GREY))
    b.append(arrow(150, 215, 230, 290, GREY))
    b.append(arrow(410, 215, 330, 290, GREY))
    b.append(text(W / 2, 384, "each name is assigned exactly once", LIGHT, 11,
                  500, italic=True))
    write("00_fundamentals/figures/ssa.svg", svg(W, H, "".join(b), "SSA"))


def fig_analyses():
    W, H = 820, 260
    b = [text(W / 2, 24, "Analyses feed transforms (a fixed-point loop)",
              GREY, 15, 700)]
    y = 56
    xs = [40, 250, 460]
    for i, x in enumerate(xs):
        b.append(box(x, y, 170, 56, ["analysis", "(pure)"], GREY, size=12,
                     lh=15))
        if i < 2:
            b.append(arrow(x + 170, y + 28, xs[i + 1], y + 28, GREY))
    b.append(arrow(xs[2] + 170, y + 28, 700, y + 28, GREY))
    b.append(box(700, y, 90, 56, ["cached", "results"], LIGHT, tcol=GREY_D,
                 size=11, lh=14))
    ty = 150
    b.append(box(160, ty, 480, 56,
                 ["transform pass  \u2014  mutates the IR using the results"],
                 PURPLE, size=13))
    for x in xs:
        b.append(arrow(x + 85, y + 56, x + 85, ty, GREY, RULE, dash="4 4"))
    b.append(path(f"M640 {ty+28} C740 {ty+28} 760 90 760 {y+56}", GREY, RULE,
                  arrow_end=True))
    b.append(text(760, 120, "invalidate", GREY, 10, 600))
    b.append(path(f"M160 {ty+28} C60 {ty+28} 40 120 40 {y+56}", PURPLE, RULE,
                  arrow_end=True, dash="5 4"))
    b.append(text(52, 128, "re-run", PURPLE, 10, 600, anchor="start"))
    write("00_fundamentals/figures/analyses.svg",
          svg(W, H, "".join(b), "Analyses and transforms"))


def fig_opt_levels():
    W, H = 1020, 320
    b = [text(W / 2, 26, "Optimization levels: debuggability \u2194 speed",
              GREY, 16, 700)]
    rows = [
        ("-O0", "identity translate; vars kept in memory", 0.05),
        ("-Og", "cheap, non-destructive passes; best to debug", 0.18),
        ("-O1", "local clean-ups: CSE, jump-thread, inline", 0.34),
        ("-O2", "loops, vectorize, IPO \u2014 most safe opts", 0.60),
        ("-O3", "aggressive inline + relaxed vectorizer", 0.78),
        ("-Os / -Oz", "size-first cost model (Oz = clang)", 0.5),
        ("-Ofast", "-O3 + -ffast-math (breaks IEEE!)", 0.92),
    ]
    x0, y0, rowh, barmax = 40, 56, 34, 340
    bx = 150
    for i, (flag, desc, frac) in enumerate(rows):
        y = y0 + i * rowh
        col = RED if flag == "-Ofast" else (
            AMBER if flag.startswith("-Os") else PURPLE)
        b.append(text(x0, y + 12, flag, GREY, 13, 700, anchor="start",
                      mono=True))
        b.append(rrect(bx, y, barmax, 20, "#E8E8E8", rx=10))
        b.append(rrect(bx, y, max(24, barmax * frac), 20, col, rx=10))
        b.append(text(bx + barmax + 12, y + 12, desc, GREY, 11, 500,
                      anchor="start"))
    b.append(text(bx, y0 + len(rows) * rowh + 10, "less optimization", LIGHT,
                  10, 600, anchor="start"))
    b.append(text(bx + barmax, y0 + len(rows) * rowh + 10, "more optimization",
                  LIGHT, 10, 600, anchor="end"))
    write("00_fundamentals/figures/opt-levels.svg",
          svg(W, H, "".join(b), "Optimization levels"))


# ── 01 local optimizations ──────────────────────────────────────────────────
def fig_cse():
    W, H = 760, 320
    b = [text(W / 2, 24, "Common-subexpression elimination (value DAG)",
              GREY, 15, 700)]
    # before: two trees computing (b*c)
    b.append(text(190, 58, "before", GREY, 12, 700))
    b.append(box(60, 80, 120, 40, "x = a + b*c", GREY, size=12))
    b.append(box(230, 80, 120, 40, "y = d + b*c", GREY, size=12))
    for x in (120, 290):
        b.append(box(x - 45, 160, 90, 36, "t = b*c", PURPLE, size=12))
        b.append(arrow(x, 120, x, 160, GREY))
    b.append(text(205, 232, "b*c computed twice", RED, 12, 600))
    b.append(arrow(380, 150, 470, 150, GREY, 2))
    # after: shared
    b.append(text(620, 58, "after", GREY, 12, 700))
    b.append(box(560, 80, 120, 40, "x = a + t", GREY, size=12))
    b.append(box(560, 140, 120, 40, "y = d + t", GREY, size=12))
    b.append(box(560, 210, 120, 40, "t = b*c", PURPLE, size=12))
    b.append(arrow(590, 210, 590, 120, GREY))
    b.append(arrow(650, 210, 650, 180, GREY))
    b.append(text(620, 274, "computed once, reused", TEAL, 12, 600))
    write("01_local_optimizations/figures/cse.svg",
          svg(W, H, "".join(b), "CSE"))


# ── 02 loop optimizations ───────────────────────────────────────────────────
def fig_loop_anatomy():
    W, H = 640, 440
    b = [text(W / 2, 24, "Anatomy of a natural loop", GREY, 16, 700)]
    b.append(box(220, 50, 200, 46, ["preheader", "runs once before loop"],
                 GREY_D, size=11, lh=14))
    b.append(box(230, 130, 180, 46, ["header", "loop guard / condition"],
                 PURPLE, size=11, lh=14))
    b.append(box(230, 220, 180, 46, ["body", "the loop's work"], GREY,
                 size=11, lh=14))
    b.append(box(230, 310, 180, 44, ["latch", "i++ ; back-edge"], GREY,
                 size=11, lh=14))
    b.append(box(470, 130, 140, 46, ["exit", "after the loop"], GREY_D,
                 size=11, lh=14))
    b.append(arrow(320, 96, 320, 130, GREY))
    b.append(arrow(320, 176, 320, 220, GREY))
    b.append(arrow(320, 266, 320, 310, GREY))
    b.append(arrow(410, 153, 470, 153, GREY))
    b.append(text(440, 140, "false", GREY, 10, 600))
    b.append(text(300, 200, "true", GREY, 10, 600, anchor="end"))
    # back-edge
    b.append(path("M230 332 C120 332 120 153 230 153", PURPLE, 2,
                  arrow_end=True))
    b.append(text(120, 245, "back-edge", PURPLE, 11, 700))
    b.append(text(W / 2, 410, "LICM hoists invariants into the preheader; "
                  "the latch owns the induction variable",
                  LIGHT, 11, 500, italic=True))
    write("02_loop_optimizations/figures/loop-anatomy.svg",
          svg(W, H, "".join(b), "Loop anatomy"))


# ── 03 interprocedural ──────────────────────────────────────────────────────
def fig_inlining():
    W, H = 760, 300
    b = [text(W / 2, 24, "Inlining removes the call boundary", GREY, 16, 700)]
    b.append(text(170, 58, "before", GREY, 12, 700))
    b.append(box(60, 78, 220, 60, ["caller", "\u2026 t = add(x, y) ; \u2026"],
                 GREY, size=12, lh=15))
    b.append(box(90, 180, 160, 56, ["callee add()", "return a + b"], PURPLE,
                 size=12, lh=15))
    b.append(arrow(170, 138, 170, 180, GREY))
    b.append(text(258, 160, "call", GREY, 10, 600, anchor="start"))
    b.append(path("M250 208 C300 208 300 108 280 108", GREY, RULE,
                  arrow_end=True))
    b.append(text(300, 165, "return", GREY, 10, 600, anchor="start"))
    b.append(arrow(360, 150, 450, 150, GREY, 2))
    b.append(text(610, 58, "after", GREY, 12, 700))
    b.append(box(490, 100, 250, 90,
                 ["caller (add inlined)", "\u2026 t = x + y ; \u2026",
                  "no call \u00b7 no frame \u00b7 arg copies gone"],
                 PURPLE, size=12, lh=16))
    b.append(text(615, 224, "unlocks const-prop across the old boundary",
                  TEAL, 11, 600))
    write("03_interprocedural/figures/inlining.svg",
          svg(W, H, "".join(b), "Inlining"))


# ── 04 dataflow analysis ────────────────────────────────────────────────────
def fig_dataflow():
    W, H = 780, 340
    b = [text(W / 2, 24, "Data-flow analysis: transfer + meet", GREY, 15, 700)]
    # block with IN/OUT
    bx, by, bw, bh = 300, 120, 200, 90
    b.append(box(bx, by, bw, bh, ["basic block B", "OUT = gen \u222a (IN \u2212 kill)"],
                 GREY, size=12, lh=18))
    b.append(box(bx + 30, by - 70, bw - 60, 40, "IN[B]", PURPLE, size=13))
    b.append(arrow(bx + bw / 2, by - 30, bx + bw / 2, by, GREY))
    b.append(box(bx + 30, by + bh + 30, bw - 60, 40, "OUT[B]", PURPLE,
                 size=13))
    b.append(arrow(bx + bw / 2, by + bh, bx + bw / 2, by + bh + 30, GREY))
    # predecessors meeting into IN
    b.append(box(120, by - 70, 120, 40, "OUT[P1]", GREY_D, size=12))
    b.append(box(120, by + 10, 120, 40, "OUT[P2]", GREY_D, size=12))
    b.append(path(f"M240 {by-50} C280 {by-50} 280 {by-55} {bx+30} {by-52}",
                  GREY, RULE, arrow_end=True))
    b.append(path(f"M240 {by+30} C280 {by+30} 285 {by-40} {bx+30} {by-45}",
                  GREY, RULE, arrow_end=True))
    b.append(text(270, by - 12, "meet (\u222a or \u2229)", TEAL, 11, 700))
    # direction note
    b.append(box(560, by - 70, 190, 40, "forward: IN \u2192 OUT", GREY, size=11))
    b.append(box(560, by + 10, 190, 40, "backward: OUT \u2192 IN", GREY,
                 size=11))
    b.append(text(W / 2, 300, "iterate to a fixed point over the CFG",
                  LIGHT, 11, 500, italic=True))
    write("04_data_flow_analysis/figures/dataflow.svg",
          svg(W, H, "".join(b), "Data-flow"))


# ── 05 control flow ─────────────────────────────────────────────────────────
def fig_jump_threading():
    W, H = 780, 340
    b = [text(W / 2, 24, "Jump threading skips a redundant test", GREY, 15,
              700)]

    def mini(ox, label, threaded):
        b.append(text(ox + 110, 56, label, GREY, 12, 700))
        b.append(box(ox + 60, 74, 100, 40, "if c", PURPLE, size=12))
        b.append(box(ox, 150, 100, 40, "A (c true)", GREY, size=11))
        b.append(box(ox + 160, 150, 100, 40, "B", GREY, size=11))
        b.append(box(ox + 60, 226, 100, 40, "if c", PURPLE if not threaded
                     else LIGHT, tcol=WHITE if not threaded else GREY_D,
                     size=12))
        b.append(box(ox + 30, 292, 160, 34, "merge", GREY_D, size=11))
        b.append(arrow(ox + 90, 114, ox + 50, 150, GREY))
        b.append(arrow(ox + 130, 114, ox + 210, 150, GREY))
        b.append(arrow(ox + 60, 170, ox + 100, 226, GREY))
        b.append(arrow(ox + 210, 170, ox + 150, 226, GREY))
        if not threaded:
            b.append(arrow(ox + 90, 266, ox + 90, 292, GREY))
            b.append(text(ox + 200, 246, "re-tests c!", RED, 10, 700,
                          anchor="start"))
        else:
            b.append(path(f"M{ox+50} 170 C{ox-10} 210 {ox-10} 292 {ox+30} 310",
                          TEAL, 2, arrow_end=True))
            b.append(text(ox - 6, 250, "threaded", TEAL, 10, 700,
                          anchor="start"))

    mini(40, "before", False)
    b.append(arrow(380, 190, 430, 190, GREY, 2))
    mini(470, "after", True)
    write("05_control_flow/figures/jump-threading.svg",
          svg(W, H, "".join(b), "Jump threading"))


# ── 06 memory optimizations ─────────────────────────────────────────────────
def fig_mem2reg():
    W, H = 760, 300
    b = [text(W / 2, 24, "mem2reg: promote stack slots to SSA values",
              GREY, 15, 700)]
    b.append(text(180, 58, "before (memory)", GREY, 12, 700))
    b.append(cylinder(80, 90, 200, 120, GREY,
                      lines=["alloca x", "store / load", "store / load"],
                      size=12))
    b.append(text(180, 232, "every use hits memory", RED, 11, 600))
    b.append(arrow(310, 150, 410, 150, PURPLE, 2))
    b.append(text(360, 132, "mem2reg", PURPLE, 11, 700))
    b.append(text(600, 58, "after (registers)", GREY, 12, 700))
    b.append(box(470, 90, 120, 36, "x\u2081 = \u2026", PURPLE, size=12))
    b.append(box(470, 140, 120, 36, "x\u2082 = \u2026", PURPLE, size=12))
    b.append(box(610, 115, 120, 36, "x\u2083 = \u03c6(\u2026)", GREY_D,
                 size=12))
    b.append(arrow(590, 108, 610, 128, GREY))
    b.append(arrow(590, 158, 610, 140, GREY))
    b.append(text(600, 232, "values live in SSA registers", TEAL, 11, 600))
    write("06_memory_optimizations/figures/mem2reg.svg",
          svg(W, H, "".join(b), "mem2reg"))


# ── 07 ssa form ─────────────────────────────────────────────────────────────
def fig_dom_frontier():
    W, H = 620, 400
    b = [text(W / 2, 24, "Dominance frontier \u2192 where \u03c6 goes",
              GREY, 15, 700)]
    nodes = {
        "A": (280, 60), "B": (150, 150), "C": (410, 150),
        "D": (280, 250), "E": (280, 340),
    }
    r = 26
    edges = [("A", "B"), ("A", "C"), ("B", "D"), ("C", "D"), ("D", "E")]
    for a, c in edges:
        (x1, y1), (x2, y2) = nodes[a], nodes[c]
        import math
        dx, dy = x2 - x1, y2 - y1
        d = math.hypot(dx, dy)
        b.append(arrow(x1 + dx / d * r, y1 + dy / d * r,
                       x2 - dx / d * r, y2 - dy / d * r, GREY))
    for n, (x, y) in nodes.items():
        col = PURPLE if n == "D" else GREY
        b.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')
        b.append(text(x, y, n, WHITE, 14, 700))
    b.append(box(360, 250, 200, 44,
                 ["D = DF(B) = DF(C)", "\u2192 insert \u03c6 here"],
                 PURPLE_D, size=11, lh=14))
    b.append(text(W / 2, 384,
                  "a def in B or C forces a \u03c6 at their join, D",
                  LIGHT, 11, 500, italic=True))
    write("07_ssa_form/figures/dominance-frontier.svg",
          svg(W, H, "".join(b), "Dominance frontier"))


# ── 08 vectorization ────────────────────────────────────────────────────────
def fig_vectorization():
    W, H = 780, 340
    b = [text(W / 2, 24, "Vectorization: 4 scalar iters \u2192 1 SIMD op",
              GREY, 15, 700)]
    b.append(text(150, 58, "scalar", GREY, 12, 700))
    for i in range(4):
        y = 80 + i * 46
        b.append(box(60, y, 190, 36, f"c[{i}] = a[{i}] + b[{i}]", GREY,
                     size=11))
    b.append(text(150, 288, "4 iterations, 4 adds", RED, 11, 600))
    b.append(arrow(280, 180, 380, 180, PURPLE, 2))
    b.append(text(330, 162, "SIMD", PURPLE, 11, 700))
    b.append(text(610, 58, "vectorized (width 4)", GREY, 12, 700))

    def lanes(x, y, label, col):
        b.append(text(x - 14, y + 18, label, GREY, 11, 700, anchor="end"))
        for i in range(4):
            b.append(box(x + i * 52, y, 48, 36, str(i), col, size=12))
    lanes(470, 90, "a", GREY)
    b.append(text(680, 145, "+", PURPLE, 20, 800))
    lanes(470, 155, "b", GREY)
    lanes(470, 225, "c", PURPLE)
    b.append(text(600, 288, "1 packed add (paddd/vaddps)", TEAL, 11, 600))
    write("08_vectorization/figures/vectorization.svg",
          svg(W, H, "".join(b), "Vectorization"))


# ── 09 register allocation ──────────────────────────────────────────────────
def fig_regalloc():
    W, H = 720, 360
    b = [text(W / 2, 24, "Register allocation = graph colouring", GREY, 15,
              700)]
    import math
    nodes = {"a": (170, 110), "b": (330, 90), "c": (300, 240),
             "d": (140, 250), "e": (450, 170)}
    colmap = {"a": PURPLE, "b": TEAL, "c": PURPLE, "d": TEAL, "e": AMBER}
    edges = [("a", "b"), ("a", "d"), ("b", "c"), ("b", "e"), ("c", "d"),
             ("c", "e"), ("d", "a")]
    for u, v in edges:
        (x1, y1), (x2, y2) = nodes[u], nodes[v]
        b.append(line(x1, y1, x2, y2, GREY, RULE))
    r = 24
    for n, (x, y) in nodes.items():
        tc = INK_DARK if colmap[n] == AMBER else WHITE
        b.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{colmap[n]}"/>')
        b.append(text(x, y, n, tc, 14, 700))
    b.append(text(310, 320, "adjacent live ranges get different registers",
                  LIGHT, 11, 500, italic=True))
    # legend
    lx = 560
    for i, (col, lab) in enumerate([(PURPLE, "r8"), (TEAL, "r9"),
                                    (AMBER, "spill")]):
        y = 90 + i * 40
        b.append(f'<circle cx="{lx}" cy="{y}" r="12" fill="{col}"/>')
        b.append(text(lx + 24, y, lab, GREY, 12, 600, anchor="start"))
    b.append(text(lx + 6, 60, "registers", GREY, 12, 700, anchor="middle"))
    write("09_register_allocation/figures/reg-alloc.svg",
          svg(W, H, "".join(b), "Register allocation"))


# ── 10 advanced ─────────────────────────────────────────────────────────────
def fig_pgo():
    W, H = 760, 300
    b = [text(W / 2, 24, "Profile-guided optimization feedback loop",
              GREY, 15, 700)]
    steps = [
        ("1. instrument", "clang -fprofile-generate", GREY, 60, 70),
        ("2. run workload", "collect .profraw counts", PURPLE, 300, 70),
        ("3. merge", "llvm-profdata \u2192 .profdata", GREY, 540, 70),
        ("4. re-optimize", "clang -fprofile-use", PURPLE, 300, 190),
    ]
    bw, bh = 170, 66
    pos = {}
    for name, sub, col, x, y in steps:
        pos[name] = (x, y)
        b.append(box(x, y, bw, bh, [name, sub], col, size=11, lh=15))
    b.append(arrow(60 + bw, 70 + bh / 2, 300, 70 + bh / 2, GREY))
    b.append(arrow(300 + bw, 70 + bh / 2, 540, 70 + bh / 2, GREY))
    b.append(path(f"M{540+bw/2} {70+bh} C{540+bw/2} 150 {300+bw+20} 150 "
                  f"{300+bw} {190+bh/2}", PURPLE, 2, arrow_end=True))
    b.append(path(f"M300 {190+bh/2} C160 {190+bh/2} 145 150 145 {70+bh}",
                  TEAL, 2, arrow_end=True))
    b.append(text(150, 165, "hot/cold layout,", TEAL, 10, 600))
    b.append(text(150, 180, "inline & branch hints", TEAL, 10, 600))
    write("10_advanced/figures/pgo.svg", svg(W, H, "".join(b), "PGO"))


# ── root: learning roadmap ──────────────────────────────────────────────────
def fig_roadmap():
    W, H = 900, 620
    b = [text(W / 2, 26, "How to read this guide", GREY, 18, 700)]
    bw, bh = 200, 52
    cols = [90, 350, 610]
    mid = 350

    def node(x, y, num, title, sub, col=GREY, w=bw):
        b.append(box(x, y, w, bh, [f"{num}  {title}", sub], col, size=12,
                     lh=15))

    node(mid, 56, "00", "Fundamentals", "pipeline \u00b7 IR \u00b7 SSA \u00b7 CFG",
         PURPLE)
    b.append(text(mid + bw + 14, 82, "start here", PURPLE, 12, 700,
                  anchor="start"))
    r1y = 150
    node(cols[0], r1y, "01", "Local", "peephole \u00b7 CSE")
    node(cols[1], r1y, "04", "Data-flow", "analyses")
    node(cols[2], r1y, "07", "SSA form", "phi \u00b7 dom-frontier")
    r2y = 240
    node(cols[0], r2y, "02", "Loops", "LICM \u00b7 unroll")
    node(cols[1], r2y, "05", "Control flow", "jump-thread")
    node(cols[2], r2y, "06", "Memory", "AA \u00b7 mem2reg")
    r3y = 330
    node(cols[0], r3y, "03", "Inter-proc", "inline \u00b7 LTO")
    node(cols[2], r3y, "08", "Vectorize", "loop \u00b7 SLP")
    r4y = 420
    node(mid, r4y, "09", "Register alloc", "coloring \u00b7 spill")
    r5y = 490
    node(mid, r5y, "10", "Advanced", "PGO \u00b7 BOLT")
    r6y = 560
    node(cols[0] + 60, r6y, "11", "GCC", "flags \u00b7 passes", GREY_D, w=170)
    node(cols[2] - 60, r6y, "12", "LLVM", "opt \u00b7 pass mgr", GREY_D, w=170)
    # 00 -> row1
    for c in cols:
        b.append(arrow(mid + bw / 2, 56 + bh, c + bw / 2, r1y, GREY))
    # row1 -> row2 -> row3 (vertical, cols 0 and 2; col1 stops at row2)
    for c in (cols[0], cols[1], cols[2]):
        b.append(arrow(c + bw / 2, r1y + bh, c + bw / 2, r2y, GREY))
    b.append(arrow(cols[0] + bw / 2, r2y + bh, cols[0] + bw / 2, r3y, GREY))
    b.append(arrow(cols[2] + bw / 2, r2y + bh, cols[2] + bw / 2, r3y, GREY))
    # row3 -> 09
    b.append(arrow(cols[0] + bw / 2, r3y + bh, mid + bw / 2 - 20, r4y, GREY))
    b.append(arrow(cols[2] + bw / 2, r3y + bh, mid + bw / 2 + 20, r4y, GREY))
    b.append(arrow(cols[1] + bw / 2, r2y + bh, mid + bw / 2, r4y, GREY,
                   dash="5 4"))
    # 09 -> 10 -> {11,12}
    b.append(arrow(mid + bw / 2, r4y + bh, mid + bw / 2, r5y, PURPLE, 2))
    b.append(arrow(mid + bw / 2, r5y + bh, cols[0] + 60 + 85, r6y, GREY))
    b.append(arrow(mid + bw / 2, r5y + bh, cols[2] - 60 + 85, r6y, GREY))
    write("figures/roadmap.svg", svg(W, H, "".join(b), "Guide roadmap"))


# ── Before/after "code card" primitives ─────────────────────────────────────
MONO = ("'SFMono-Regular',ui-monospace,'JetBrains Mono',Menlo,"
        "Consolas,monospace")
CARD_BG = "#232A35"          # self-contained dark code card (theme-independent)
CODE_FG = "#D7DCE6"
CODE_DIM = "#8892A5"
CODE_HI = "#7FC4FF"          # changed / highlighted line
CODE_GOOD = "#83CEA3"        # added
CODE_BAD = "#E98A90"         # removed
LBL_BEFORE = "#9AA0B4"
LBL_AFTER = "#7FC4FF"
PAD = 14
LH = 19
CSIZE = 12.5
CHARW = 7.55
LABEL_AREA = 28
BOTTOM = 12
_STYLE_COL = {"n": CODE_FG, "hi": CODE_HI, "dim": CODE_DIM,
              "good": CODE_GOOD, "bad": CODE_BAD}


def _txt(ln):
    return ln[0] if isinstance(ln, tuple) else ln


def card_size(lines, label, minw=0):
    maxlen = max([len(_txt(l)) for l in lines] + [len(label) + 2])
    w = max(minw, PAD * 2 + int(round(maxlen * CHARW)))
    h = LABEL_AREA + len(lines) * LH + BOTTOM
    return w, h


def code_card(x, y, lines, label, border, labelcol, minw=0):
    w, h = card_size(lines, label, minw)
    out = [rrect(x, y, w, h, CARD_BG, rx=11, stroke=border, sw=1.75)]
    out.append(f'<text x="{x+PAD}" y="{y+15}" fill="{labelcol}" '
               f'font-family="{FONT}" font-size="10.5" font-weight="700" '
               f'letter-spacing="1.2" text-anchor="start" '
               f'dominant-baseline="central">{esc(label)}</text>')
    cy = y + LABEL_AREA + LH / 2
    for ln in lines:
        txt, style = (ln if isinstance(ln, tuple) else (ln, "n"))
        out.append(
            f'<text x="{x+PAD}" y="{cy}" fill="{_STYLE_COL[style]}" '
            f'font-family="{MONO}" font-size="{CSIZE}" text-anchor="start" '
            f'dominant-baseline="central" '
            f'xml:space="preserve">{esc(txt)}</text>')
        cy += LH
    return "".join(out), w, h


def before_after(fname, title, before, after, op="", note_b="", note_a="",
                 blabel="BEFORE", alabel="AFTER", title2="", gap=104):
    wl, hl = card_size(before, blabel)
    wr, hr = card_size(after, alabel)
    top = 46 if not title2 else 62
    y0 = top
    maxh = max(hl, hr)
    xl = 24
    xr = xl + wl + gap
    W = xr + wr + 24
    note_h = 26 if (note_b or note_a) else 0
    H = top + maxh + note_h + 18
    b = [text(W / 2, 24, title, GREY, 15.5, 700)]
    if title2:
        b.append(text(W / 2, 44, title2, LIGHT, 11.5, 500, italic=True))
    cl, _, _ = code_card(xl, y0, before, blabel, GREY_D, LBL_BEFORE)
    cr, _, _ = code_card(xr, y0, after, alabel, PURPLE, LBL_AFTER)
    b.append(cl)
    b.append(cr)
    ay = y0 + maxh / 2
    b.append(arrow(xl + wl + 16, ay, xr - 12, ay, PURPLE, 2.0))
    if op:
        b.append(text((xl + wl + xr) / 2, ay - 13, op, PURPLE, 11, 700))
    if note_b:
        b.append(text(xl + wl / 2, y0 + maxh + 15, note_b, RED, 11, 600))
    if note_a:
        b.append(text(xr + wr / 2, y0 + maxh + 15, note_a, TEAL, 11, 600))
    write(fname, svg(W, H, "".join(b), title))


def rules_fig(fname, title, pairs, note="", lhs_hdr="", rhs_hdr=""):
    """A card of  lhs  →  rhs  rewrite rules (monospace)."""
    lw = max(len(l) for l, _ in pairs)
    rw = max(len(r) for _, r in pairs)
    x0, y0 = 24, 46
    lx = x0 + PAD
    arrow_x1 = lx + int(lw * CHARW) + 12
    arrow_x2 = arrow_x1 + 30
    rx = arrow_x2 + 12
    cardw = (rx + int(rw * CHARW) + PAD) - x0
    rows = len(pairs)
    hdr_h = 20 if (lhs_hdr or rhs_hdr) else 0
    cardh = LABEL_AREA + hdr_h + rows * LH + BOTTOM
    W = x0 + cardw + 24
    H = y0 + cardh + (24 if note else 12)
    b = [text(W / 2, 24, title, GREY, 15.5, 700)]
    b.append(rrect(x0, y0, cardw, cardh, CARD_BG, rx=11, stroke=GREY_D,
                   sw=1.75))
    cy = y0 + LABEL_AREA + hdr_h + LH / 2
    if hdr_h:
        b.append(text(lx, y0 + 16, lhs_hdr, LBL_BEFORE, 10.5, 700,
                      anchor="start"))
        b.append(text(rx, y0 + 16, rhs_hdr, LBL_AFTER, 10.5, 700,
                      anchor="start"))
    for l, r in pairs:
        b.append(f'<text x="{lx}" y="{cy}" fill="{CODE_FG}" '
                 f'font-family="{MONO}" font-size="{CSIZE}" text-anchor="start"'
                 f' dominant-baseline="central" '
                 f'xml:space="preserve">{esc(l)}</text>')
        b.append(arrow(arrow_x1, cy, arrow_x2, cy, PURPLE, 1.8))
        b.append(f'<text x="{rx}" y="{cy}" fill="{CODE_GOOD}" '
                 f'font-family="{MONO}" font-size="{CSIZE}" text-anchor="start"'
                 f' dominant-baseline="central" '
                 f'xml:space="preserve">{esc(r)}</text>')
        cy += LH
    if note:
        b.append(text(W / 2, y0 + cardh + 13, note, LIGHT, 11, 500,
                      italic=True))
    write(fname, svg(W, H, "".join(b), title))


# ── 01 local: before/after per optimization ─────────────────────────────────
def figs_local():
    before_after(
        "01_local_optimizations/figures/01_const_fold.svg",
        "Constant folding", 
        [("%t = mul i32 3, 4", "dim"), ("%y = add i32 %t, 1", "dim")],
        [("%y = i32 13", "hi")], op="fold",
        note_a="evaluated at compile time")
    before_after(
        "01_local_optimizations/figures/02_const_propagation.svg",
        "Constant & copy propagation",
        ["a = 5", ("b = a + 2", "n"), ("c = b * 3", "n"), ("d = c", "n")],
        ["a = 5", ("b = 7", "hi"), ("c = 21", "hi"), ("d = 21", "hi")],
        op="SCCP", note_a="each use folds to a literal")
    before_after(
        "01_local_optimizations/figures/04_dead_code.svg",
        "Dead-code elimination",
        [("a = expensive();", "bad"), "b = compute();", "return b;"],
        ["b = compute();", "return b;"], op="DCE",
        note_b="a is never used", note_a="side-effect-free \u2192 removed")
    rules_fig(
        "01_local_optimizations/figures/05_algebraic_simpl.svg",
        "Algebraic simplification",
        [("x + 0", "x"), ("x * 1", "x"), ("x * 0", "0"), ("x - x", "0"),
         ("x & 0", "0"), ("x | 0", "x"), ("x ^ x", "0"),
         ("(x<<a)<<b", "x << (a+b)"), ("!!x", "x != 0")],
        note="integers only \u2014 IEEE-754 float needs -ffast-math")
    rules_fig(
        "01_local_optimizations/figures/06_strength_reduction.svg",
        "Strength reduction",
        [("x * 2", "x << 1"), ("x * 8", "x << 3"),
         ("x / 2  (u)", "x >> 1"), ("x % 8  (u)", "x & 7"),
         ("x * 9", "(x<<3) + x"), ("x * 10", "(x<<3)+(x<<1)"),
         ("x * 7", "(x<<3) - x")],
        note="division by constant \u2192 multiply-by-magic + shift")
    rules_fig(
        "01_local_optimizations/figures/07_peephole.svg",
        "Peephole / instruction combining",
        [("lea rax,[rdi+0]", "mov rax, rdi"),
         ("cmp eax, 0", "test eax, eax"),
         ("mov eax,0", "xor eax, eax"),
         ("mov rcx,rax;shr 32", "mov ecx, eax")],
        note="a small (2-4 instruction) sliding window", lhs_hdr="naive",
        rhs_hdr="combined")
    before_after(
        "01_local_optimizations/figures/08_branch_simpl.svg",
        "Branch simplification",
        ["if (p)", "    return 1;", "return 0;"],
        [("return !!p;", "hi")], op="SimplifyCFG",
        note_a="branch becomes a compare")
    before_after(
        "01_local_optimizations/figures/10_load_combine.svg",
        "Load / store combining",
        [("v = a[0] | a[1]<<8", "dim"),
         ("  | a[2]<<16 | a[3]<<24;", "dim")],
        [("mov eax, [rdi]", "hi"), ("; one 32-bit load", "dim")],
        op="combine", note_a="4 byte loads \u2192 1 word load")


# ── 02 loops ─────────────────────────────────────────────────────────────────
def figs_loops():
    before_after(
        "02_loop_optimizations/figures/01_licm.svg",
        "Loop-invariant code motion (LICM)",
        ["for (i=0;i<n;i++) {",
         ("  a[i]=(x*y+k)*a[i];", "bad"), "}"],
        [("t = x*y + k;", "hi"), "for (i=0;i<n;i++) {",
         ("  a[i]=t*a[i];", "good"), "}"], op="hoist",
        note_b="recomputed every iter", note_a="computed once")
    before_after(
        "02_loop_optimizations/figures/02_unroll.svg",
        "Loop unrolling (by 4)",
        ["for (i=0;i<n;i++)", "  a[i]=b[i]+c[i];"],
        ["for (;i+3<n;i+=4){", "  a[i  ]=b[i  ]+c[i  ];",
         "  a[i+1]=b[i+1]+c[i+1];", "  a[i+2]=b[i+2]+c[i+2];",
         "  a[i+3]=b[i+3]+c[i+3];", "}", ("// scalar epilogue", "dim")],
        op="unroll", note_a="fewer branches, more ILP")
    before_after(
        "02_loop_optimizations/figures/04_unswitch.svg",
        "Loop unswitching",
        ["for (i=0;i<n;i++){", ("  if (cond)", "bad"), "    a[i]=f(b[i]);",
         "  else", "    a[i]=g(b[i]);", "}"],
        [("if (cond) {", "hi"), "  for(..) a[i]=f(b[i]);", "} else {",
         "  for(..) a[i]=g(b[i]);", "}"], op="unswitch",
        note_b="branch per iteration", note_a="branch hoisted out")
    before_after(
        "02_loop_optimizations/figures/05_fusion.svg",
        "Loop fusion (jamming)",
        ["for(i..) a[i]=b[i]+1;", "for(i..) c[i]=a[i]*2;"],
        ["for (i=0;i<n;i++){", ("  a[i]=b[i]+1;", "good"),
         ("  c[i]=a[i]*2;", "good"), "}"], op="fuse",
        note_a="one pass, better locality")
    before_after(
        "02_loop_optimizations/figures/06_fission.svg",
        "Loop fission (distribution)",
        ["for (i=0;i<n;i++){", "  a[i]=b[i]+1;", "  hash(&h,a[i]);", "}"],
        ["for(i..) a[i]=b[i]+1;", "for(i..) hash(&h,a[i]);"], op="split",
        note_a="vectorizable half isolated")
    before_after(
        "02_loop_optimizations/figures/07_interchange.svg",
        "Loop interchange",
        ["for (i..N)", "  for (j..N)", ("    A[j][i]=..", "bad")],
        ["for (j..N)", "  for (i..N)", ("    A[j][i]=..", "good")],
        op="swap", note_b="column stride (cache miss)",
        note_a="unit stride (cache hit)")
    before_after(
        "02_loop_optimizations/figures/09_iv_simplification.svg",
        "Induction-variable simplification",
        ["for (i=0;i<n;i++)", ("  sum += a[i*8];", "bad")],
        ["p = a;", "for (i=0;i<n;i++){", ("  sum += *p;", "good"),
         "  p += 8;", "}"], op="IV-simpl",
        note_b="multiply + index each iter", note_a="pointer bump")
    before_after(
        "02_loop_optimizations/figures/10_rerolling.svg",
        "Loop rerolling",
        [("a[i  ]=b[i  ]+1;", "dim"), ("a[i+1]=b[i+1]+1;", "dim"),
         ("a[i+2]=b[i+2]+1;", "dim"), ("a[i+3]=b[i+3]+1;", "dim")],
        ["for (k=0;k<4;k++)", ("  a[i+k]=b[i+k]+1;", "hi")], op="reroll",
        note_a="clean loop to vectorize")
    before_after(
        "02_loop_optimizations/figures/11_idiom_recognition.svg",
        "Loop idiom recognition",
        [("for(i..) buf[i]=0;", "dim"), ("while(*s++) ;", "dim"),
         ("for(i..)c+=(x>>i)&1;", "dim")],
        [("memset(buf,0,n);", "good"), ("rawmemchr(s,0);", "good"),
         ("__popcount(x);", "good")], op="recognize",
        note_a="loop \u2192 one call/intrinsic")
    before_after(
        "02_loop_optimizations/figures/12_versioning.svg",
        "Loop versioning (runtime memcheck)",
        ["for (i=0;i<n;i++)", "  a[i]=b[i]+c[i];",
         ("// a,b,c may alias?", "dim")],
        [("if (no_overlap) {", "hi"), "  /* vectorized */",
         "} else {", "  /* scalar */", "}"], op="guard",
        note_a="fast path picked at runtime")


# ── 03 interprocedural ──────────────────────────────────────────────────────
def figs_ipo():
    before_after(
        "03_interprocedural/figures/02_ipsccp.svg",
        "Interprocedural SCCP",
        ["callA: f(0);", "callB: f(0);", ("int f(int x){", "n"),
         ("  if (x) hot();", "bad"), "  else cold();", "}"],
        ["int f() {", ("  cold();", "hi"), "}", ("// x proven 0", "dim")],
        op="specialize", note_a="dead branch removed")
    before_after(
        "03_interprocedural/figures/03_arg_promotion.svg",
        "Argument promotion",
        ["int hot(const int *p){", ("  return *p + 1;", "bad"), "}",
         "int r = hot(&x);"],
        ["int hot(int v){", ("  return v + 1;", "good"), "}",
         "int r = hot(x);"], op="by-value",
        note_b="load through pointer", note_a="value in a register")
    before_after(
        "03_interprocedural/figures/04_devirtualization.svg",
        "Devirtualization",
        ["B *p = new D();", ("p->foo();", "bad"),
         ("// indirect call", "dim")],
        [("D::foo(p);", "hi"), ("// then inline", "dim")], op="resolve",
        note_b="vtable load + indirect", note_a="direct \u2192 inlinable")
    before_after(
        "03_interprocedural/figures/05_tail_call.svg",
        "Tail-call elimination",
        ["fact(n, acc){", "  if(!n) return acc;",
         ("  return fact(n-1,", "bad"), "              acc*n);", "}"],
        ["fact:", "  test n,n; jz done", "  mul acc,n; dec n",
         ("  jmp fact  ; no call", "hi"), "done: mov ret,acc"], op="TCE",
        note_b="stack grows per call", note_a="reuses the frame (a loop)")
    before_after(
        "03_interprocedural/figures/07_lto.svg",
        "Link-time optimization",
        ["// a.o: int add(a,b)", "// b.o: add(1,2)",
         ("call add", "bad"), "// TU wall between them"],
        [("mov eax, 3", "hi"), "ret", ("// inlined + folded", "dim")],
        op="LTO", note_b="opaque cross-TU call", note_a="whole-program view")


# ── 05 control flow ─────────────────────────────────────────────────────────
def figs_control():
    before_after(
        "05_control_flow/figures/02_cfg_simplification.svg",
        "SimplifyCFG \u2192 select",
        ["br cond, B2, B3", "B2: x = 1; br B4", "B3: x = 2; br B4",
         "B4: use x"],
        [("x = select(cond,1,2);", "hi"), "use x"], op="fold",
        note_a="branch \u2192 branchless select")
    before_after(
        "05_control_flow/figures/03_if_conversion.svg",
        "If-conversion (cmov)",
        ["if (a > b)", "  r = x;", "else", "  r = y;"],
        ["cmp a, b", "mov r, y", ("cmovg r, x", "hi")], op="predicate",
        note_a="no branch to mispredict")
    before_after(
        "05_control_flow/figures/07_loop_rotation.svg",
        "Loop rotation (while \u2192 do-while)",
        ["header:", "  if !cond goto exit", "  body", "  goto header",
         "exit:"],
        [("if (!cond) goto exit;", "hi"), "loop:", "  body",
         "  if cond goto loop", "exit:"], op="rotate",
        note_a="one branch/iter, vectorizable")
    before_after(
        "05_control_flow/figures/08_branch_folding.svg",
        "Branch folding / cross-jumping",
        ["B1: .. ; jmp epi1", "B2: .. ; jmp epi2",
         ("epi1: pop rbp; ret", "bad"), ("epi2: pop rbp; ret", "bad")],
        ["B1: .. ; jmp shared", "B2: .. ; jmp shared",
         ("shared: pop rbp; ret", "hi")], op="merge",
        note_a="identical tails shared")


# ── 06 memory ────────────────────────────────────────────────────────────────
def figs_memory():
    before_after(
        "06_memory_optimizations/figures/02_sroa.svg",
        "Scalar replacement of aggregates",
        ["%p = alloca Pair", "store x, %p.a", "store x+1, %p.b",
         "%a = load %p.a", "%b = load %p.b", "ret %a + %b"],
        [("%a = x", "good"), ("%b = x + 1", "good"),
         ("ret 2*x + 1", "hi"), ("// no alloca", "dim")], op="SROA+mem2reg",
        note_a="struct fields become SSA")
    before_after(
        "06_memory_optimizations/figures/04_store_to_load.svg",
        "Store-to-load forwarding",
        ["*p = x;", ("y = *p;", "bad")],
        ["*p = x;", ("y = x;", "hi")], op="forward",
        note_b="reload from memory", note_a="reuse the stored value")
    before_after(
        "06_memory_optimizations/figures/05_gvn.svg",
        "Global value numbering (loads)",
        ["v1 = *p;", "/* no store to p */", ("v2 = *p;", "bad")],
        ["v1 = *p;", ("v2 = v1;", "hi")], op="GVN",
        note_a="second load eliminated")
    before_after(
        "06_memory_optimizations/figures/06_dead_store_elim.svg",
        "Dead-store elimination",
        [("*p = 1;", "bad"), "*p = 2;"],
        ["*p = 2;", ("// first store dead", "dim")], op="DSE",
        note_b="overwritten unread", note_a="only live store kept")
    before_after(
        "06_memory_optimizations/figures/07_memcpy_opt.svg",
        "MemCpyOpt",
        ["memcpy(tmp,src,64);", ("memcpy(dst,tmp,64);", "bad")],
        [("memcpy(dst,src,64);", "hi"), ("// tmp is dead", "dim")],
        op="combine", note_a="copy chain collapsed")
    before_after(
        "06_memory_optimizations/figures/08_escape_analysis.svg",
        "Escape analysis",
        [("p = malloc(2*4);", "bad"), "p[0]=a; p[1]=b;",
         "r = p[0]+p[1];", "free(p);"],
        [("int a_=a, b_=b;", "good"), ("r = a_ + b_;", "hi"),
         ("// no heap", "dim")], op="stackify",
        note_b="heap alloc never escapes", note_a="scalarized away")


# ── 07 ssa ───────────────────────────────────────────────────────────────────
def figs_ssa():
    before_after(
        "07_ssa_form/figures/01_ssa_intro.svg",
        "Into SSA form",
        ["x = 1", "if cond:", "    x = 2", "print(x)"],
        ["x1 = 1", "if cond:", "    x2 = 2",
         ("x3 = \u03c6(x1, x2)", "hi"), "print(x3)"], op="rename",
        note_a="one definition per name")
    before_after(
        "07_ssa_form/figures/05_out_of_ssa.svg",
        "Out of SSA: the swap problem",
        [("x = \u03c6(y, ..)", "n"), ("y = \u03c6(x, ..)", "n"),
         ("// parallel copies", "dim")],
        [("t = y", "good"), "x = y", ("y = t", "good"),
         ("// temp breaks cycle", "dim")], op="sequentialize",
        note_b="naive x\u2190y; y\u2190x corrupts", note_a="Sreedhar: add a temp")


# ── 08 vectorization ─────────────────────────────────────────────────────────
def figs_vec():
    before_after(
        "08_vectorization/figures/02_reduction.svg",
        "Reduction (sum)",
        ["s = 0;", "for (i=0;i<n;i++)", ("  s += a[i];", "bad")],
        ["v = {0,0,0,0,..};", "for (;i+7<n;i+=8)", ("  v += a[i:i+8];", "hi"),
         ("s = hadd(v);", "good"), "for (;i<n;i++) s+=a[i];"], op="vectorize",
        note_b="serial accumulate", note_a="8 lanes + horizontal add")
    before_after(
        "08_vectorization/figures/04_masked.svg",
        "Masked vectorization",
        ["for (i=0;i<n;i++)", ("  if (a[i]>0)", "bad"),
         "    b[i]=a[i]*2;"],
        ["va = a[i:i+VF];", ("m = va > 0;", "hi"), "r = va * 2;",
         ("mstore b[i:], r, m", "good")], op="mask",
        note_a="per-lane predicate, no branch")


# ── 11 gcc: IR pipeline ──────────────────────────────────────────────────────
def fig_gcc_pipeline():
    W, H = 940, 250
    b = [text(W / 2, 26, "GCC: two IRs, four stages", GREY, 16, 700)]
    y, bh = 60, 120
    bw = 176
    xs = [24, 254, 484, 714]
    stages = [
        ("GENERIC", ["language-", "independent trees"], GREY_D),
        ("GIMPLE", ["three-address SSA", "(all mid-end here)"], PURPLE),
        ("RTL", ["register transfer", "language (\u2248 asm)"], GREY),
        ("asm", ["target", "assembly"], GREY_D),
    ]
    cy = y + bh / 2
    for x, (ttl, rows, col) in zip(xs, stages):
        b.append(rrect(x, y, bw, bh, col, rx=12))
        b.append(text(x + bw / 2, y + 26, ttl, WHITE, 14, 700))
        b.append(line(x + 18, y + 44, x + bw - 18, y + 44, WHITE, 1))
        for i, r in enumerate(rows):
            b.append(text(x + bw / 2, y + 70 + i * 20, r, WHITE, 11, 500))
    labels = ["front-end", "SSA + opt", "expand"]
    for i in range(3):
        x1, x2 = xs[i] + bw, xs[i + 1]
        b.append(arrow(x1, cy, x2, cy, GREY, 2))
        b.append(text((x1 + x2) / 2, cy - 12, labels[i], GREY, 10, 600))
    b.append(text(W / 2, y + bh + 36, "mid-end passes run on GIMPLE; "
                  "register allocation & scheduling on RTL",
                  LIGHT, 11, 500, italic=True))
    write("11_gcc_specific/figures/pipeline.svg",
          svg(W, H, "".join(b), "GCC pipeline"))


# ── 12 llvm: pipeline ────────────────────────────────────────────────────────
def fig_llvm_pipeline():
    W, H = 660, 540
    cx, bw = 235, 250
    b = [text(W / 2, 26, "LLVM / Clang pipeline", GREY, 16, 700)]
    steps = [
        (56, 46, ["source.{c,cpp}"], GREY_D, 13),
        (150, 52, ["LLVM IR", "text .ll / bitcode .bc"], PURPLE, 12),
        (250, 46, ["LLVM IR (optimized)"], PURPLE, 13),
        (344, 70, ["llc backend", "ISel \u00b7 MIR \u00b7 RegAlloc",
                   "scheduler \u00b7 asm printer"], GREY, 12),
        (464, 46, ["object file"], GREY_D, 13),
    ]
    for y, h, lines, col, sz in steps:
        b.append(box(cx - bw / 2, y, bw, h, lines, col, size=sz, lh=17))
    arr = [(102, 150, "Clang front-end"),
           (202, 250, "opt \u2014 mid-end passes"),
           (296, 344, "instruction selection"),
           (414, 464, "")]
    for y1, y2, lab in arr:
        b.append(arrow(cx, y1, cx, y2, GREY, 2))
        if lab:
            b.append(text(cx + bw / 2 + 14, (y1 + y2) / 2, lab, GREY, 11,
                          600, anchor="start"))
    write("12_llvm_specific/figures/pipeline.svg",
          svg(W, H, "".join(b), "LLVM pipeline"))


# ── 13 practical: optimization loop ──────────────────────────────────────────
def fig_recipe():
    W, H = 1020, 250
    b = [text(W / 2, 26, "The optimization loop \u2014 never guess, measure",
              GREY, 16, 700)]
    bw, bh, y = 172, 66, 78
    step = bw + 27
    steps = [
        ("1 MEASURE", "profile first", PURPLE),
        ("2 ATTRIBUTE", "find the hot spot", GREY),
        ("3 INSPECT", "read asm + IR", PURPLE),
        ("4 CHANGE", "source / flags / algo", GREY),
        ("5 RE-MEASURE", "confirm, watch regress", PURPLE),
    ]
    xs = [24 + i * step for i in range(5)]
    for x, (ttl, sub, col) in zip(xs, steps):
        b.append(box(x, y, bw, bh, [ttl, sub], col, size=12, lh=17))
    for i in range(4):
        b.append(arrow(xs[i] + bw, y + bh / 2, xs[i + 1], y + bh / 2,
                       GREY, 2))
    # feedback arc from step 5 back to step 1
    x5 = xs[4] + bw / 2
    x1 = xs[0] + bw / 2
    yb = y + bh
    b.append(path(f"M{x5} {yb} C{x5} {yb+70} {x1} {yb+70} {x1} {yb}",
                  TEAL, 2, arrow_end=True))
    b.append(text((x1 + x5) / 2, yb + 60, "iterate until it stops helping",
                  TEAL, 11, 600))
    write("13_practical/figures/optimization-loop.svg",
          svg(W, H, "".join(b), "Optimization loop"))


# ── root: learning roadmap ──────────────────────────────────────────────────
ALL_BA = [figs_local, figs_loops, figs_ipo, figs_control, figs_memory,
          figs_ssa, figs_vec,
          fig_gcc_pipeline, fig_llvm_pipeline, fig_recipe]

ALL = [
    fig_roadmap,
    fig_pipeline, fig_cfg, fig_ssa, fig_analyses, fig_opt_levels,
    fig_cse, fig_loop_anatomy, fig_inlining, fig_dataflow,
    fig_jump_threading, fig_mem2reg, fig_dom_frontier, fig_vectorization,
    fig_regalloc, fig_pgo,
]

if __name__ == "__main__":
    for fn in ALL:
        fn()
    for fn in ALL_BA:
        fn()
    print("\nDone: hero + before/after figures generated.")
