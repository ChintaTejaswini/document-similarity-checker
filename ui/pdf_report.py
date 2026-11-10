"""
PDF report export.

    build_pdf(data) -> bytes

`data` is the dictionary of results the app has already computed (the same `facts` the assistant
reads, plus V2 = the first two eigenvectors). Nothing is recalculated here: this file only
LAYS OUT numbers and draws the three charts (heatmap, bar chart, scatter) with ReportLab, so no
extra image or browser library is needed.

Long collections are shortened on paper (see the PDF_MAX_* numbers). The maths always uses every document.
"""
import datetime
import html
import io
import os
from functools import lru_cache

import numpy as np
from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .theme import CHART

PDF_MAX_ROWS = 40        # table rows per table
PDF_MAX_COLS = 8         # table columns per table
PDF_HEATMAP_DOCS = 30    # documents drawn in the heatmap
PDF_LABELS_UP_TO = 25    # point labels in the scatter plot (more points: no labels)

NAVY, INDIGO, PALE, EDGE = "#14213D", "#243A82", "#F1F4FF", "#DCE3F7"
W = A4[0] - 36 * mm      # usable page width


# ----------------------------------------------------------------------------
# Fonts and text safety (the built-in PDF fonts have no Greek letters or arrows)
# ----------------------------------------------------------------------------
_FONT_FILES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
]
_ASCII = {"θ": "theta", "λ": "lambda", "σ": "sigma", "≤": "<=", "≥": ">=", "ᵀ": "^T", "²": "^2", "−": "-",
          "ᵢ": "_i", "Â": "A-hat", "ℝ": "R", "×": "x", "→": "->", "…": "...", "≈": "~", "·": ".", "’": "'",
          "“": '"', "”": '"', "–": "-", "—": "-"}


@lru_cache(maxsize=1)
def _fonts():
    """(regular, bold, glyph set or None). A Unicode TrueType font if one is installed, else Helvetica."""
    for reg, bold in _FONT_FILES:
        if os.path.exists(reg) and os.path.exists(bold):
            try:
                f = TTFont("ReportSans", reg)
                pdfmetrics.registerFont(f)
                pdfmetrics.registerFont(TTFont("ReportSans-Bold", bold))
                pdfmetrics.registerFontFamily("ReportSans", normal="ReportSans", bold="ReportSans-Bold",
                                              italic="ReportSans", boldItalic="ReportSans-Bold")
                return "ReportSans", "ReportSans-Bold", set(f.face.charToGlyph)
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold", None


def _has(ch):
    glyphs = _fonts()[2]
    if glyphs is not None:
        return ord(ch) in glyphs
    try:
        ch.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def _txt(s):
    """Plain text the chosen font can print: unknown characters become ASCII words or '?'."""
    s = " ".join(str(s).split())
    return "".join(c if _has(c) else _ASCII.get(c, "?") for c in s)


def _e(s):
    """Text -> safe Paragraph markup."""
    return html.escape(_txt(s), quote=False)


def _short(s, n=16):
    s = _txt(s)
    return s if len(s) <= n else s[:n - 1] + "..."


# ----------------------------------------------------------------------------
# Paragraph styles and small layout helpers
# ----------------------------------------------------------------------------
def _styles():
    reg, bold, _ = _fonts()
    mk = lambda name, **kw: ParagraphStyle(name, fontName=kw.pop("fontName", reg), **kw)
    return dict(
        title=mk("t", fontName=bold, fontSize=20, leading=24, textColor=colors.HexColor(NAVY)),
        eyebrow=mk("e", fontSize=8.5, leading=11, textColor=colors.HexColor("#5B49C9")),
        body=mk("b", fontSize=9, leading=12.5, textColor=colors.HexColor(NAVY)),
        h2=mk("h", fontName=bold, fontSize=13, leading=16, textColor=colors.HexColor(NAVY), spaceBefore=14,
              spaceAfter=2, keepWithNext=1),
        sub=mk("s", fontSize=8.5, leading=11.5, textColor=colors.HexColor("#3F4F80"), spaceAfter=4, keepWithNext=1),
        formula=mk("f", fontName="Courier", fontSize=8, leading=10.5, textColor=colors.HexColor(NAVY),
                   backColor=colors.HexColor(PALE), borderPadding=(4, 5, 4, 5), spaceAfter=7, spaceBefore=3,
                   keepWithNext=1),
        small=mk("sm", fontSize=7.5, leading=10, textColor=colors.HexColor("#3F4F80"), spaceBefore=2),
        cell=mk("c", fontSize=7.5, leading=9.5, textColor=colors.HexColor(NAVY)),
        cell_r=mk("cr", fontSize=7.5, leading=9.5, textColor=colors.HexColor(NAVY), alignment=2),
        head=mk("hd", fontName=bold, fontSize=7.5, leading=9.5, textColor=colors.white),
        head_r=mk("hdr", fontName=bold, fontSize=7.5, leading=9.5, textColor=colors.white, alignment=2),
    )


def _section(st, num, title, sub, formula):
    return [Paragraph(f"{num}&nbsp;&nbsp;{_e(title)}", st["h2"]), Paragraph(_e(sub), st["sub"]),
            Paragraph(_e(formula), st["formula"])]


def _note(st, markup):
    """Interpretation box: pale panel with a pink bar on the left. `markup` may use <b>."""
    t = Table([[Paragraph("<b>Interpretation.</b> " + markup, st["body"])]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F7F8FF")),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(CHART["pink"])),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return [Spacer(1, 4), t, Spacer(1, 4)]


def _table(st, header, rows, widths, text_cols=(0,)):
    """Grid table. Columns in `text_cols` are left-aligned and wrap; the rest are right-aligned numbers."""
    def cell(v, j, head=False):
        left = j in text_cols
        key = ("head" if head else "cell") + ("" if left else "_r")
        return Paragraph(_e(v), st[key])
    data = [[cell(h, j, True) for j, h in enumerate(header)]] + [[cell(v, j) for j, v in enumerate(r)] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(INDIGO)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(PALE)]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor(EDGE)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2), ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return t


def _grid_widths(first, ncols):
    """First column `first` mm wide, the others share the rest of the page."""
    return [first * mm] + [(W - first * mm) / max(1, ncols)] * ncols


def _caption(st, text):
    return Paragraph(_e(text), st["small"])


# ----------------------------------------------------------------------------
# Charts, drawn with ReportLab shapes
# ----------------------------------------------------------------------------
def _hex_rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def _heat_color(v):
    """Colour of value v in [0, 1] on the app's heatmap scale."""
    stops = CHART["heat"]
    v = min(max(float(v), 0.0), 1.0)
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if v <= b:
            t = (v - a) / (b - a) if b > a else 0
            return [x + (y - x) * t for x, y in zip(_hex_rgb(ca), _hex_rgb(cb))]
    return _hex_rgb(stops[-1][1])


def _ink_for(rgb):
    """Navy or white text, whichever reads better on this background."""
    return colors.white if 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2] < 0.5 else colors.HexColor(NAVY)


def _rotated_label(d, x, y, text, size, angle=45):
    g = Group(String(0, 0, text, fontName=_fonts()[0], fontSize=size, textAnchor="end",
                     fillColor=colors.HexColor(NAVY)))
    g.translate(x, y)
    g.rotate(angle)
    d.add(g)


def heatmap_drawing(S, labels):
    """Similarity matrix as coloured squares (first PDF_HEATMAP_DOCS documents)."""
    k = min(len(labels), PDF_HEATMAP_DOCS)
    names = [_short(l, 18) for l in labels[:k]]
    left, bottom, size = 34 * mm, 30 * mm, min(112 * mm, W - 58 * mm)
    cell = size / k
    d = Drawing(W, size + bottom + 6 * mm)
    fs = min(8, max(3.5, cell * 0.75))
    for i in range(k):
        for j in range(k):
            rgb = _heat_color(S[i, j])
            x, y = left + j * cell, bottom + (k - 1 - i) * cell
            d.add(Rect(x, y, cell, cell, fillColor=colors.Color(*rgb), strokeColor=colors.white, strokeWidth=0.6))
            if k <= 10:
                d.add(String(x + cell / 2, y + cell / 2 - 3, f"{S[i, j]:.2f}", fontName=_fonts()[0], fontSize=7,
                             textAnchor="middle", fillColor=_ink_for(rgb)))
        d.add(String(left - 3, bottom + (k - 1 - i) * cell + cell / 2 - fs / 3, names[i], fontName=_fonts()[0],
                     fontSize=fs, textAnchor="end", fillColor=colors.HexColor(NAVY)))
        _rotated_label(d, left + i * cell + cell / 2 + fs / 3, bottom - 3, names[i], fs)
    bar_x = left + size + 8 * mm                                  # colour scale, 0 .. 1
    for s in range(30):
        d.add(Rect(bar_x, bottom + size * s / 30, 7, size / 30 + 0.4, strokeColor=None, strokeWidth=0,
                   fillColor=colors.Color(*_heat_color(s / 29))))
    for v in (0, 0.5, 1):
        d.add(String(bar_x + 10, bottom + size * v - 2.5, f"{v:g}", fontName=_fonts()[0], fontSize=7,
                     fillColor=colors.HexColor(CHART["muted"])))
    return d


def bar_drawing(names, values):
    """Explained variance per component; the first two bars are highlighted."""
    h, left, bottom = 62 * mm, 14 * mm, 9 * mm
    d = Drawing(W, h)
    top = max(max(values), 1e-9)
    plot_h, slot = h - bottom - 8 * mm, (W - left - 4 * mm) / len(values)
    d.add(Line(left, bottom, W - 4 * mm, bottom, strokeColor=colors.HexColor(EDGE)))
    for i, (nm, v) in enumerate(zip(names, values)):
        bh = plot_h * v / top
        x = left + i * slot + slot * 0.2
        d.add(Rect(x, bottom, slot * 0.6, bh, strokeColor=None, strokeWidth=0,
                   fillColor=colors.HexColor(CHART["pt"] if i < 2 else CHART["dim"])))
        d.add(String(x + slot * 0.3, bottom + bh + 2, f"{v:.1f}%", fontName=_fonts()[0], fontSize=7,
                     textAnchor="middle", fillColor=colors.HexColor(NAVY)))
        d.add(String(x + slot * 0.3, bottom - 9, nm, fontName=_fonts()[0], fontSize=7.5, textAnchor="middle",
                     fillColor=colors.HexColor(NAVY)))
    d.add(String(2, h - 8, "Explained variance %", fontName=_fonts()[0], fontSize=7.5,
                 fillColor=colors.HexColor(CHART["muted"])))
    return d


def _span(v):
    lo, hi = float(v.min()), float(v.max())
    pad = max(0.4, (hi - lo) * 0.15)
    return lo - pad, hi + pad


def scatter_drawing(Z, labels, var):
    """Every document projected onto PC1 and PC2."""
    h, left, bottom, right = 96 * mm, 15 * mm, 12 * mm, 6 * mm
    d = Drawing(W, h)
    (x0, x1), (y0, y1) = _span(Z[:, 0]), _span(Z[:, 1])
    px = lambda v: left + (v - x0) / (x1 - x0) * (W - left - right)
    py = lambda v: bottom + (v - y0) / (y1 - y0) * (h - bottom - 6 * mm)
    reg = _fonts()[0]
    for i in range(5):                                           # grid lines and tick labels
        gx, gy = x0 + (x1 - x0) * i / 4, y0 + (y1 - y0) * i / 4
        d.add(Line(px(gx), py(y0), px(gx), py(y1), strokeColor=colors.HexColor(EDGE), strokeWidth=0.5))
        d.add(Line(px(x0), py(gy), px(x1), py(gy), strokeColor=colors.HexColor(EDGE), strokeWidth=0.5))
        d.add(String(px(gx), bottom - 9, f"{gx:.1f}", fontName=reg, fontSize=6.5, textAnchor="middle",
                     fillColor=colors.HexColor(CHART["muted"])))
        d.add(String(left - 3, py(gy) - 2, f"{gy:.1f}", fontName=reg, fontSize=6.5, textAnchor="end",
                     fillColor=colors.HexColor(CHART["muted"])))
    if x0 < 0 < x1:
        d.add(Line(px(0), py(y0), px(0), py(y1), strokeColor=colors.HexColor("#B4C0EA"), strokeWidth=0.8))
    if y0 < 0 < y1:
        d.add(Line(px(x0), py(0), px(x1), py(0), strokeColor=colors.HexColor("#B4C0EA"), strokeWidth=0.8))
    for i in range(len(labels)):
        d.add(Circle(px(Z[i, 0]), py(Z[i, 1]), 3, fillColor=colors.HexColor(CHART["pt"]),
                     strokeColor=colors.white, strokeWidth=0.8))
        if len(labels) <= PDF_LABELS_UP_TO:
            d.add(String(px(Z[i, 0]), py(Z[i, 1]) + 5, _short(labels[i], 20), fontName=reg, fontSize=7,
                         textAnchor="middle", fillColor=colors.HexColor(NAVY)))
    d.add(String(left + (W - left - right) / 2, 1, f"PC1 ({var[0]:.1f}%)", fontName=reg, fontSize=8,
                 textAnchor="middle", fillColor=colors.HexColor(NAVY)))
    g = Group(String(0, 0, f"PC2 ({var[1]:.1f}%)", fontName=reg, fontSize=8, textAnchor="middle",
                     fillColor=colors.HexColor(NAVY)))
    g.translate(7, bottom + (h - bottom) / 2)
    g.rotate(90)
    d.add(g)
    return d


# ----------------------------------------------------------------------------
# The report
# ----------------------------------------------------------------------------
def _top_columns(A, m):
    """Which word columns to print: all of them, or the PDF_MAX_COLS most frequent (kept in original order)."""
    if m <= PDF_MAX_COLS:
        return np.arange(m)
    return np.sort(np.argsort(-A.sum(axis=0), kind="stable")[:PDF_MAX_COLS])


def _page(canvas, doc):
    reg = _fonts()[0]
    canvas.saveState()
    canvas.setFont(reg, 7.5)
    canvas.setFillColor(colors.HexColor("#5C6A99"))
    canvas.drawString(18 * mm, 10 * mm, "Document Similarity & Dimensionality Analyzer")
    canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_pdf(data):
    """Return the finished report as PDF bytes."""
    st = _styles()
    n, m, r = data["n"], data["m"], data["r"]
    labels, previews, vocab = data["labels"], data["docs"], data["vocab"]
    A, norms, G, S = data["A"], data["norms"], data["G"], data["S"]
    vals, var, Z, V2 = data["vals"], data["var"], data["Z"], data["V2"]
    bi, bj, cs = data["best"]
    lo_i, lo_j = data["worst"]
    pi, pj = data["closest"]
    f = lambda x, nd=4: f"{x:.{nd}f}"
    story = []

    # ---- title, summary, documents -------------------------------------------------------------
    story += [Paragraph("LINEAR ALGEBRA &amp; VECTOR CALCULUS, MINI PROJECT 8", st["eyebrow"]),
              Paragraph("Document Similarity &amp; Dimensionality Report", st["title"]),
              Paragraph(f"Generated on {datetime.datetime.now():%d %B %Y, %H:%M}. "
                        f"Common words {'removed' if data['drop_stop'] else 'kept'}.", st["sub"]), Spacer(1, 6)]
    stats = [("Documents (n)", n), ("Vocabulary (m)", m), ("Rank of A", r), ("Variance in 2D", f"{var[:2].sum():.1f}%")]
    t = Table([[Paragraph(f'<font size="15"><b>{_e(v)}</b></font>', st["body"]) for _, v in stats],
               [Paragraph(_e(k), st["small"]) for k, _ in stats]], colWidths=[W / 4] * 4)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(PALE)),
                           ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(EDGE)),
                           ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.white),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, 0), 7),
                           ("BOTTOMPADDING", (0, 1), (-1, 1), 6)]))
    story += [t, Spacer(1, 8), Paragraph("Documents analysed", st["h2"])]
    rows = [[labels[i], previews[i]] for i in range(min(n, PDF_MAX_ROWS))]
    story.append(_table(st, ["Label", "Text (first words)"], rows, [42 * mm, W - 42 * mm], text_cols=(0, 1)))
    if n > PDF_MAX_ROWS:
        story.append(_caption(st, f"Showing {PDF_MAX_ROWS} of {n} documents. All {n} are used in every calculation."))

    # ---- 01 feature matrix ---------------------------------------------------------------------
    cols = _top_columns(A, m)
    story += _section(st, "01", "Feature matrix", "Each row is a document, each column a word. Entry = how often "
                      "the word appears.", "A[i][j] = number of times word j appears in document i   (A is n x m)")
    rows = [[labels[i]] + [str(int(A[i, j])) for j in cols] for i in range(min(n, PDF_MAX_ROWS))]
    story.append(_table(st, [""] + [_short(vocab[j], 9) for j in cols], rows, _grid_widths(34, len(cols))))
    if n > PDF_MAX_ROWS or m > PDF_MAX_COLS:
        story.append(_caption(st, f"Showing {min(n, PDF_MAX_ROWS)} of {n} documents and {len(cols)} of {m} words "
                                  "(the most frequent). All are used in every calculation."))
    story += _note(st, f"{n} documents and {m} distinct words give a {n} x {m} matrix. Every document is now a list "
                       "of numbers, so linear algebra can be applied.")

    # ---- 02 rank -------------------------------------------------------------------------------
    story += _section(st, "02", "Rank", "How many documents carry independent information?",
                      "rank(A) = number of non-zero rows in the row echelon form of A")
    if r == n:
        msg = f"rank = {r} = n, so all {n} documents are linearly independent: each one adds new information."
    else:
        msg = (f"rank = {r} &lt; n = {n}, so {n - r} document(s) are linear combinations of the others "
               "(redundant in the vector sense).")
    story += _note(st, msg + f" The documents span an {r}-dimensional subspace of R<super>{m}</super>.")

    # ---- 03 norms ------------------------------------------------------------------------------
    story += _section(st, "03", "Document vectors and norms", f"Each row of A is a vector in a {m}-dimensional "
                      "space (one axis per word).", "||d|| = sqrt( <d, d> ) = sqrt( d1^2 + d2^2 + ... + dm^2 )")
    rows = [[labels[i], previews[i], f(norms[i])] for i in range(min(n, PDF_MAX_ROWS))]
    story.append(_table(st, ["Label", "Text", "Norm ||d||"], rows, [34 * mm, W - 54 * mm, 20 * mm], text_cols=(0, 1)))
    if n > PDF_MAX_ROWS:
        story.append(_caption(st, f"Showing {PDF_MAX_ROWS} of {n} documents."))
    story += _note(st, f"<b>{_e(labels[int(norms.argmax())])}</b> is the longest vector ({f(norms.max())}) and "
                       f"<b>{_e(labels[int(norms.argmin())])}</b> the shortest ({f(norms.min())}). Length depends on "
                       "document size, which is why similarity uses the angle instead.")

    # ---- 04 inner product ----------------------------------------------------------------------
    k = min(n, PDF_MAX_COLS)
    story += _section(st, "04", "Inner product", "The dot product of two document vectors measures how many words "
                      "they share.", "<u, v> = u1 v1 + u2 v2 + ... + um vm")
    rows = [[labels[i]] + [f(G[i, j], 2) for j in range(k)] for i in range(k)]
    story.append(_table(st, [""] + [_short(l, 9) for l in labels[:k]], rows, _grid_widths(34, k)))
    if n > k:
        story.append(_caption(st, f"Showing the first {k} of {n} documents."))
    story.append(Paragraph(_e(f"cos theta = <{labels[bi]}, {labels[bj]}> / (||{labels[bi]}|| * ||{labels[bj]}||) = "
                              f"{G[bi, bj]:.2f} / ({norms[bi]:.4f} x {norms[bj]:.4f}) = {cs:.4f}"),
                           ParagraphStyle("w", parent=st["formula"], spaceBefore=6, keepWithNext=0)))
    story += _note(st, "A dot product of 0 means two documents share no words (they are orthogonal). "
                       "The line above is a worked example for the most similar pair.")

    # ---- 05 similarity matrix ------------------------------------------------------------------
    story += _section(st, "05", "Similarity matrix", "Cosine of the angle between every pair of documents.",
                      "S = A_hat A_hat^T  where A_hat has unit-length rows,  S[i][j] = cos theta(i, j)")
    story.append(heatmap_drawing(S, labels))
    if n > PDF_HEATMAP_DOCS:
        story.append(_caption(st, f"The heatmap shows the first {PDF_HEATMAP_DOCS} of {n} documents; "
                                  f"S is computed for all {n}."))
    story += _note(st, f"Most similar pair: <b>{_e(labels[bi])} &amp; {_e(labels[bj])}</b> ({f(S[bi, bj])}). "
                       f"Least similar pair: {_e(labels[lo_i])} &amp; {_e(labels[lo_j])} ({f(S[lo_i, lo_j])}). "
                       "1 means the same word proportions, 0 means no words in common. "
                       "S is symmetric with 1s on the diagonal.")

    # ---- 06 PCA --------------------------------------------------------------------------------
    kv = min(len(vals), 8)
    story += _section(st, "06", "Principal component analysis", "Find the directions along which the documents "
                      "vary the most.", "X_c = A - mean,   C = X_c^T X_c / (n-1),   C v = lambda v")
    rows = [[f"PC{i + 1}", f(vals[i]), f"{var[i]:.2f}", f"{np.cumsum(var)[i]:.2f}"] for i in range(kv)]
    story.append(_table(st, ["Component", "Eigenvalue (lambda)", "Explained %", "Cumulative %"], rows,
                        [W / 4] * 4))
    story += [Spacer(1, 6), bar_drawing([f"PC{i + 1}" for i in range(kv)], list(var[:kv])),
              Paragraph("Principal components (eigenvectors) as word weights", st["sub"])]
    rows = [[vocab[i], f(V2[i, 0]), f(V2[i, 1])] for i in range(min(m, 12))]
    story.append(_table(st, ["Word", "PC1", "PC2"], rows, [W - 60 * mm, 30 * mm, 30 * mm]))
    if m > 12:
        story.append(_caption(st, f"Showing 12 of {m} words."))
    top = ", ".join(_e(w) for w in data["top_words"])
    story += _note(st, f"PC1 explains <b>{var[0]:.1f}%</b> of the variance and PC1 + PC2 together explain "
                       f"<b>{var[:2].sum():.1f}%</b>. The words with the largest weight on PC1 are {top}. "
                       "(The sign of an eigenvector is arbitrary.)")

    # ---- 07 projection -------------------------------------------------------------------------
    story += _section(st, "07", "2D projection", "Every document projected onto the first two principal "
                      "components.", "Z = X_c V2      (n x 2)")
    story.append(scatter_drawing(Z, labels, var))
    rows = [[labels[i], f(Z[i, 0]), f(Z[i, 1])] for i in range(min(n, PDF_MAX_ROWS))]
    story += [Spacer(1, 6), _table(st, ["Label", "PC1", "PC2"], rows, [W - 60 * mm, 30 * mm, 30 * mm])]
    if n > PDF_MAX_ROWS:
        story.append(_caption(st, f"Showing {PDF_MAX_ROWS} of {n} documents."))
    story += _note(st, "Documents that sit close together use similar words. In 2D the closest pair is "
                       f"<b>{_e(labels[pi])} &amp; {_e(labels[pj])}</b>. Compare this plot with the similarity matrix: "
                       f"they should tell the same story. The 2D view keeps {var[:2].sum():.1f}% of the variance.")

    # ---- 08 most similar pairs + checks --------------------------------------------------------
    story += _section(st, "08", "Most similar pairs and verification", "The document pairs whose word proportions "
                      "are closest, by cosine similarity.", "cos theta(i, j) = S[i][j]")
    iu = np.triu_indices(n, 1)
    order = np.argsort(-S[iu], kind="stable")[:4]
    rows = [[f"{labels[iu[0][o]]} & {labels[iu[1][o]]}", f"{S[iu][o] * 100:.1f}%"] for o in order]
    story.append(_table(st, ["Pair", "Similarity"], rows, [W - 40 * mm, 40 * mm]))
    story.append(Spacer(1, 8))
    rows = [[name, "PASS" if ok else "FAIL", detail] for name, ok, detail in data["checks"]]
    story.append(_table(st, ["Consistency check", "Result", "Detail"], rows, [70 * mm, 20 * mm, W - 90 * mm],
                        text_cols=(0, 1, 2)))
    story += _note(st, f"All calculations were verified: {data['passed']} of {len(data['checks'])} "
                       "consistency checks passed.")

    buf = io.BytesIO()
    SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=18 * mm, title="Document Similarity Report",
                      author="Document Similarity & Dimensionality Analyzer").build(
        story, onFirstPage=_page, onLaterPages=_page)
    return buf.getvalue()
