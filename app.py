"""
Document Similarity and Dimensionality Analyzer  (Streamlit UI)

This file only DISPLAYS things. All the maths lives in the results/ package:
    text_processor -> rank -> similarity -> pca
Each stage below takes the output of the previous one (the sequential process
required by the assignment).

The look (dreamy blue pixel-art workspace) lives in ui/:
    ui/theme.py       colours, background, glass panels, cards, buttons
    ui/pixel_cat.py   the pixel-art cat mascot
    ui/assistant.py   Pixel Cat's answers (built only from the results below)
    ui/pdf_report.py  the "Export report as PDF" feature at the bottom of the page
    ui/panel.py       the floating assistant panel

Run:  streamlit run app.py
"""
import html

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from results.text_processor import clean_text, tokenize, build_vocab, build_feature_matrix
from results.rank import matrix_rank
from results.similarity import (
    get_document_vectors, vector_norm, inner_product,
    cos_similarity, build_similarity_matrix,
)
from results.pca import (
    center_matrix, compute_covariance, compute_eigen, compute_eigen_dual,
    explained_variance, project_data,
)
from results.documents import collect_documents

from ui.theme import build_css, CHART as CH
from ui.panel import render_panel
from ui.pdf_report import build_pdf

st.set_page_config(page_title="Document Similarity Analyzer", layout="wide")

# ----------------------------------------------------------------------------
# Sample inputs and a small stop-word list (optional preprocessing)
# ----------------------------------------------------------------------------
SAMPLES = {
    "Sample: animals & cars (4 docs)": "cat dog pet\ndog pet pet\ncar engine\ncar car engine",
    "Sample: three topics (9 docs)": "\n".join([
        "the team won the football match with a late goal",
        "players train hard before the big tournament final",
        "the coach praised the team after the match",
        "fresh pasta with tomato sauce and basil",
        "the chef baked bread and cooked pasta for dinner",
        "spicy soup with fresh basil and garlic",
        "the new laptop has a fast processor and memory",
        "software update improves processor speed and battery",
        "developers write software code for the laptop",
    ]),
}
OWN, UPLOAD = "Write my own", "Upload .txt files"

# Responsible handling of big collections. None of these limit HOW MANY documents you can add;
# they only keep the browser and the server from running out of memory or time.
TABLE_MAX_ROWS = 200       # table rows drawn on screen (the maths always uses every document)
TABLE_MAX_COLS = 40        # table columns drawn on screen
HEATMAP_MAX_DOCS = 300     # documents drawn in the similarity heatmap
LABEL_TEXT_MAX_DOCS = 40   # point labels in the PCA plot (more points -> labels on hover only)
DUAL_PCA_ABOVE = 1200      # vocabularies larger than this use the n x n route to the same eigenpairs
MAX_CELLS = 25_000_000     # n*m (and n*n) matrix cells that can be analysed safely

STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with", "is",
    "are", "was", "were", "has", "have", "had", "it", "its", "this", "that",
    "at", "by", "as", "be", "from", "after", "before",
}

# ----------------------------------------------------------------------------
# Sidebar: input options (unchanged)
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Settings")
    dark = st.toggle("Dark mode", value=False)
    source = st.radio("Documents", [*SAMPLES, OWN, UPLOAD])
    raw, uploads = "", []
    if source in SAMPLES:
        raw = SAMPLES[source]
    else:
        if source == UPLOAD:
            files = st.file_uploader("Select one or more .txt files", type=["txt"],
                                     accept_multiple_files=True, key="doc_files")
            uploads = [(f.name, f.getvalue()) for f in files or []]
            st.caption("Each file is one document, labelled with its filename. "
                       "Type extra documents below to combine them with the files.")
        raw = st.text_area("Your own documents (one per line)", height=180, key="manual_docs",
                           placeholder="cat dog pet\ndog pet pet\ncar engine")
    drop_stop = st.checkbox("Remove common words (the, and, of ...)", value=True)

# Theme: background photo, frosted glass, light cards (see ui/theme.py)
st.markdown(build_css(dark), unsafe_allow_html=True)


# ----------------------------------------------------------------------------
# Small display helpers (no maths in here)
# ----------------------------------------------------------------------------
def section(num, title, sub):
    st.markdown(f'<div class="sec" id="sec-{num}"><div class="num">{num}</div><div>'
                f'<div class="sec-title">{title}</div><div class="sec-sub">{sub}</div></div></div>',
                unsafe_allow_html=True)


def formula(text):
    st.markdown(f'<div class="formula">{html.escape(text)}</div>', unsafe_allow_html=True)


def note(text):
    st.markdown(f'<div class="note"><b>Interpretation.</b> {text}</div>', unsafe_allow_html=True)


def table(df, nd=4, left=False, index=True):
    body = df.to_html(border=0, classes="tbl", index=index, escape=True,
                      float_format=lambda x: f"{x:.{nd}f}").replace("\n", "").replace("$", "&#36;")
    st.markdown(f'<div class="tbl-wrap{" left" if left else ""}">{body}</div>', unsafe_allow_html=True)


def show(fig):
    cfg = {"displayModeBar": False}
    try:
        st.plotly_chart(fig, width="stretch", theme=None, config=cfg)
    except TypeError:  # older Streamlit versions
        st.plotly_chart(fig, use_container_width=True, theme=None, config=cfg)


def style(fig, height):
    fig.update_layout(
        height=height, margin=dict(l=16, r=16, t=16, b=16),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Nunito, system-ui, sans-serif", color=CH["text"], size=13),
        showlegend=False)
    fig.update_xaxes(gridcolor=CH["grid"], zerolinecolor=CH["grid"], linecolor=CH["grid"], automargin=True)
    fig.update_yaxes(gridcolor=CH["grid"], zerolinecolor=CH["grid"], linecolor=CH["grid"], automargin=True)
    return fig


def heat_ink(v):
    """Navy or white text for a heatmap cell, whichever contrasts more with the cell colour."""
    stops = CH["heat"]
    hex_rgb = lambda h: [int(h[i:i + 2], 16) for i in (1, 3, 5)]
    rgb = hex_rgb(stops[-1][1])
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if v <= b:
            t = (v - a) / (b - a)
            rgb = [x + (y - x) * t for x, y in zip(hex_rgb(ca), hex_rgb(cb))]
            break
    lin = [(c / 255) / 12.92 if c / 255 <= 0.03928 else ((c / 255 + 0.055) / 1.055) ** 2.4 for c in rgb]
    lum = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    navy_lum = 0.0157                                   # luminance of #14213D
    white_contrast = 1.05 / (lum + 0.05)
    navy_contrast = (lum + 0.05) / (navy_lum + 0.05)
    return "#FFFFFF" if white_contrast > navy_contrast else CH["text"]


# ----------------------------------------------------------------------------
# Header (a frosted panel; the summary cards are added to it once results exist)
# ----------------------------------------------------------------------------
steps = ["Documents", "Feature matrix", "Rank", "Document vectors",
         "Norm / inner product", "Similarity matrix", "PCA", "Projection"]
targets = ["top", "sec-01", "sec-02", "sec-03", "sec-04", "sec-05", "sec-06", "sec-07"]
header = st.container(key="glass_header")
with header:
    st.markdown(
        '<div id="top"></div>'
        '<div class="eyebrow">Linear Algebra &amp; Vector Calculus</div>'
        '<div class="h1">Document Similarity &amp; Dimensionality Analyzer</div>'
        '<div class="lead">Represent documents numerically, compare their similarities, '
        'and reduce them to a 2D picture.</div>',
        unsafe_allow_html=True)
    st.markdown('<div class="flow">' + '<span class="arrow">&rarr;</span>'.join(
        f'<a class="chip" href="#{t}" target="_self">{s}</a>' for s, t in zip(steps, targets)) + '</div>',
        unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# Input handling
# ----------------------------------------------------------------------------
def words_of(text):
    tk = tokenize(clean_text(text))
    return [w for w in tk if w not in STOP_WORDS] if drop_stop else tk


# uploaded files (one document each) + manual lines; empty / unreadable ones are skipped with a note
labels, docs, notes = collect_documents(uploads, raw, usable=lambda t: bool(words_of(t)))
tokens = [words_of(d) for d in docs]
hl = [html.escape(l).replace("$", "&#36;") for l in labels]        # safe to place inside HTML
previews = [" ".join(d.split()) for d in docs]
previews = [p if len(p) <= 200 else p[:197].rstrip() + "…" for p in previews]   # long files: first words only

for level, msg in notes:
    (st.warning if level == "warning" else st.info)(msg)

signature = hash((tuple(labels), tuple(docs), drop_stop))   # lets the cat forget answers about older input

if len(docs) < 2:
    st.info("Add at least two documents in the sidebar to begin (upload .txt files, type one per line, or both).")
    render_panel(None, signature)
    st.stop()

# ============================================================================
# STAGE 1  Documents -> Feature matrix
# ============================================================================
vocab = build_vocab(tokens)
if len(vocab) < 2:
    st.warning("The documents need at least two different words in total.")
    render_panel(None, signature)
    st.stop()

n, m = len(docs), len(vocab)
if max(n * m, n * n) > MAX_CELLS:
    st.error(f"This collection is too large to analyse in the browser: {n:,} documents x {m:,} distinct words "
             f"= {n * m:,} matrix cells (the safe limit is {MAX_CELLS:,}). Tick \"Remove common words\", "
             "or analyse fewer or shorter documents.")
    render_panel(None, signature)
    st.stop()

A = np.array(build_feature_matrix(tokens, vocab), dtype=float)

# ============================================================================
# STAGE 2  Rank
# ============================================================================
r = int(matrix_rank(A))

# ============================================================================
# STAGE 3-4  Document vectors -> norm / inner product
# ============================================================================
V = get_document_vectors(A)
norms = np.array([vector_norm(v) for v in V])
if n <= 200:
    G = np.array([[inner_product(a, b) for b in V] for a in V])
else:                                    # identical numbers, without n*n Python calls
    G = V @ V.T

# ============================================================================
# STAGE 5  Similarity matrix
# ============================================================================
S = np.array(build_similarity_matrix(V))

# ============================================================================
# STAGE 6-7  PCA -> projection
# ============================================================================
X = center_matrix(A)
if m > DUAL_PCA_ABOVE:
    # large vocabulary: same eigenvalues/eigenvectors via the small n x n matrix (no m x m matrix needed)
    vals, vecs = compute_eigen_dual(X)
    trace_C = float(np.sum(X * X) / (n - 1))
else:
    C = compute_covariance(X)
    vals, vecs = compute_eigen(C)
    trace_C = float(np.trace(C))
vals = np.where(np.abs(vals) < 1e-10, 0.0, vals)
var = explained_variance(vals)
Z = project_data(X, vecs)
V2 = np.zeros((m, 2))                    # first two eigenvectors (zero-padded if fewer exist)
V2[:, :min(2, vecs.shape[1])] = vecs[:, :2]
if Z.shape[1] < 2:
    Z = np.hstack([Z, np.zeros((n, 2 - Z.shape[1]))])

if n < 3:
    st.warning("With only 2 documents PCA has a single meaningful direction. Use 3 or more for a useful 2D plot.")

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------
with header:
    st.markdown('<div class="stats">' + "".join(
        f'<div class="stat"><div class="stat-v">{v}</div><div class="stat-k">{k}</div></div>'
        for k, v in [("Documents (n)", n), ("Vocabulary (m)", m), ("Rank of A", r),
                     ("Variance in 2D", f"{var[:2].sum():.1f}%")]) + "</div>", unsafe_allow_html=True)

# ----------------------------------------------------------------------------
# 01 Feature matrix
# ----------------------------------------------------------------------------
with st.container(key="glass_feature"):
    section("01", "Feature matrix", "Each row is a document, each column a word. Entry = how often the word appears.")
    formula("A[i][j] = number of times word j appears in document i      (A is n x m)")
    cols = np.arange(m) if m <= TABLE_MAX_COLS else np.sort(np.argsort(-A.sum(axis=0), kind="stable")[:TABLE_MAX_COLS])
    table(pd.DataFrame(A[:TABLE_MAX_ROWS][:, cols].astype(int), index=labels[:TABLE_MAX_ROWS],
                       columns=[vocab[j] for j in cols]))
    if n > TABLE_MAX_ROWS or m > TABLE_MAX_COLS:
        st.caption(f"Display only: showing {min(n, TABLE_MAX_ROWS)} of {n} documents and the "
                   f"{len(cols)} most frequent of {m} words. All {n} documents and {m} words are used in every calculation.")
    note(f"{n} documents and {m} distinct words give a {n} &times; {m} matrix. "
         "Every document is now a list of numbers, so linear algebra can be applied.")

# ----------------------------------------------------------------------------
# 02 Rank
# ----------------------------------------------------------------------------
with st.container(key="glass_rank"):
    section("02", "Rank", "How many documents carry independent information?")
    formula("rank(A) = number of non-zero rows in the row echelon form of A")
    if r == n:
        msg = f"rank = {r} = n, so all {n} documents are linearly independent: each one adds new information."
    else:
        msg = (f"rank = {r} &lt; n = {n}, so {n - r} document(s) are linear combinations of the others "
               "(redundant in the vector sense).")
    note(msg + f" The documents span an {r}-dimensional subspace of &#8477;<sup>{m}</sup>.")

# ----------------------------------------------------------------------------
# 03 Document vectors and norms
# ----------------------------------------------------------------------------
with st.container(key="glass_norms"):
    section("03", "Document vectors and norms",
            f"Each row of A is a vector in a {m}-dimensional space (one axis per word).")
    formula("||d|| = sqrt( <d, d> ) = sqrt( d1^2 + d2^2 + ... + dm^2 )")
    table(pd.DataFrame({"Text": previews, "Norm ||d||": norms}, index=labels).head(TABLE_MAX_ROWS), left=True)
    if n > TABLE_MAX_ROWS:
        st.caption(f"Display only: showing {TABLE_MAX_ROWS} of {n} documents.")
    note(f"{hl[int(norms.argmax())]} is the longest vector ({norms.max():.4f}) and "
         f"{hl[int(norms.argmin())]} the shortest ({norms.min():.4f}). "
         "Length depends on document size, which is why similarity uses the angle instead.")

# ----------------------------------------------------------------------------
# 04 Inner product
# ----------------------------------------------------------------------------
with st.container(key="glass_inner"):
    section("04", "Inner product", "The dot product of two document vectors measures how many words they share.")
    formula("<u, v> = u1 v1 + u2 v2 + ... + um vm")
    gk = min(n, TABLE_MAX_ROWS)
    table(pd.DataFrame(G[:gk, :gk], index=labels[:gk], columns=labels[:gk]), nd=2)
    if n > gk:
        st.caption(f"Display only: showing the first {gk} of {n} documents.")
    off = S.copy()
    np.fill_diagonal(off, -np.inf)
    bi, bj = np.unravel_index(np.argmax(off), off.shape)
    cs = cos_similarity(V[bi], V[bj])
    st.markdown(
        f'<div class="formula" style="margin-top:.9rem">cos &theta; = &lt;{hl[bi]}, {hl[bj]}&gt; / '
        f'(||{hl[bi]}|| &middot; ||{hl[bj]}||) = {G[bi, bj]:.2f} / '
        f'({norms[bi]:.4f} &times; {norms[bj]:.4f}) = {cs:.4f}</div>', unsafe_allow_html=True)
    note("A dot product of 0 means two documents share no words (they are orthogonal). "
         "The line above is a worked example for the most similar pair.")

# ----------------------------------------------------------------------------
# 05 Similarity matrix
# ----------------------------------------------------------------------------
with st.container(key="glass_similarity"):
    section("05", "Similarity matrix", "Cosine of the angle between every pair of documents.")
    formula("S = Â Âᵀ   where Â has unit-length rows,   S[i][j] = cos θ(i, j)")
    hk = min(n, HEATMAP_MAX_DOCS)
    hlab = [html.escape(l) for l in labels[:hk]]          # plotly reads a little HTML, so escape filenames
    hm = go.Figure(go.Heatmap(z=S[:hk, :hk], x=hlab, y=hlab, zmin=0, zmax=1, colorscale=CH["heat"],
                              xgap=3 if hk <= 40 else 0, ygap=3 if hk <= 40 else 0, showscale=True,
                              colorbar=dict(thickness=10, len=0.9, outlinewidth=0, tickfont=dict(color=CH["muted"]))))
    if n <= 15:
        for i in range(n):
            for j in range(n):
                hm.add_annotation(x=hlab[j], y=hlab[i], text=f"{S[i, j]:.2f}", showarrow=False,
                                  font=dict(size=12, color=heat_ink(S[i, j])))
    style(hm, max(300, min(46 * hk + 60, 760)))
    hm.update_yaxes(autorange="reversed", showgrid=False)
    hm.update_xaxes(showgrid=False)
    if hk > 6 or max(len(l) for l in labels[:hk]) > 6:       # filenames are longer than D1, D2 ...
        hm.update_xaxes(tickangle=-45)
    show(hm)
    if n > hk:
        st.caption(f"Display only: the heatmap shows the first {hk} of {n} documents; S is computed for all {n}.")
    lo_i, lo_j = np.unravel_index(np.argmin(np.where(np.isinf(off), np.inf, off)), off.shape)
    note(f"Most similar pair: <b>{hl[bi]} &amp; {hl[bj]}</b> ({S[bi, bj]:.4f}). "
         f"Least similar pair: {hl[lo_i]} &amp; {hl[lo_j]} ({S[lo_i, lo_j]:.4f}). "
         "1 means the same word proportions, 0 means no words in common. S is symmetric with 1s on the diagonal.")

# ----------------------------------------------------------------------------
# 06 PCA
# ----------------------------------------------------------------------------
with st.container(key="glass_pca"):
    section("06", "Principal component analysis", "Find the directions along which the documents vary the most.")
    formula("X_c = A - mean,   C = X_cᵀ X_c / (n-1),   C v = λ v")
    k = min(len(vals), 8)
    ev = pd.DataFrame({"Eigenvalue λ": vals[:k], "Explained %": var[:k], "Cumulative %": np.cumsum(var)[:k]},
                      index=[f"PC{i + 1}" for i in range(k)])
    c1, c2 = st.columns(2, gap="large")
    with c1:
        table(ev, nd=4)
    with c2:
        bar = go.Figure(go.Bar(x=ev.index, y=ev["Explained %"],
                               marker_color=[CH["pt"] if i < 2 else CH["dim"] for i in range(k)],
                               text=[f"{v:.1f}%" for v in ev["Explained %"]], textposition="outside",
                               cliponaxis=False))
        style(bar, 260)
        bar.update_yaxes(title_text="Explained variance %", range=[0, max(110, var[0] + 15)], showgrid=False)
        bar.update_xaxes(showgrid=False)
        show(bar)

    st.markdown('<div class="sub-label">Principal components (eigenvectors) as word weights</div>',
                unsafe_allow_html=True)
    pcs = pd.DataFrame(V2, index=vocab, columns=["PC1", "PC2"])
    table(pcs.head(12), nd=4)
    if m > 12:
        st.caption(f"Showing 12 of {m} words.")
    top = [html.escape(vocab[i]) for i in np.argsort(-np.abs(V2[:, 0]))[:3]]
    note(f"PC1 explains <b>{var[0]:.1f}%</b> of the variance and PC1 + PC2 together explain "
         f"<b>{var[:2].sum():.1f}%</b>. The words with the largest weight on PC1 are "
         f"{', '.join(top)}. (The sign of an eigenvector is arbitrary.)")

# ----------------------------------------------------------------------------
# 07 Projection
# ----------------------------------------------------------------------------
with st.container(key="glass_projection"):
    section("07", "2D projection", "Every document projected onto the first two principal components.")
    formula("Z = X_c V₂      (n x 2)")
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        slab = [html.escape(l) for l in labels]
        sc = go.Figure(go.Scatter(
            x=Z[:, 0], y=Z[:, 1], mode="markers+text" if n <= LABEL_TEXT_MAX_DOCS else "markers",
            text=slab, textposition="top center",
            textfont=dict(size=12, color=CH["text"]),
            marker=dict(size=13, color=CH["pt"], line=dict(width=2, color=CH["card"])),
            hovertext=[f"<b>{sl}</b><br>{html.escape(p)}" for sl, p in zip(slab, previews)], hoverinfo="text"))
        style(sc, 400)
        sc.update_xaxes(title_text=f"PC1 ({var[0]:.1f}%)", zeroline=True)
        sc.update_yaxes(title_text=f"PC2 ({var[1]:.1f}%)", zeroline=True)
        pad_x = max(0.4, np.ptp(Z[:, 0]) * 0.15)
        pad_y = max(0.4, np.ptp(Z[:, 1]) * 0.2)
        sc.update_xaxes(range=[Z[:, 0].min() - pad_x, Z[:, 0].max() + pad_x])
        sc.update_yaxes(range=[Z[:, 1].min() - pad_y, Z[:, 1].max() + pad_y])
        show(sc)
    with c2:
        table(pd.DataFrame(Z, index=labels, columns=["PC1", "PC2"]).head(TABLE_MAX_ROWS), nd=4)
        if n > TABLE_MAX_ROWS:
            st.caption(f"Display only: showing {TABLE_MAX_ROWS} of {n} documents.")
    d2 = np.linalg.norm(Z[:, None, :] - Z[None, :, :], axis=2)
    np.fill_diagonal(d2, np.inf)
    pi, pj = np.unravel_index(np.argmin(d2), d2.shape)
    note(f"Documents that sit close together use similar words. In 2D the closest pair is "
         f"<b>{hl[pi]} &amp; {hl[pj]}</b>. Compare this plot with the similarity matrix: they should tell the same story. "
         f"The 2D view keeps {var[:2].sum():.1f}% of the variance.")

# ----------------------------------------------------------------------------
# 08 Verification
# ----------------------------------------------------------------------------
with st.container(key="glass_verify"):
    section("08", "Most similar pairs", "The document pairs whose word proportions are closest, by cosine similarity.")
    kk = min(n, m)
    sv = np.linalg.svd(X, compute_uv=False)
    nonzero = A.any(axis=1)
    checks = [
        ("Rank is at most min(n, m)", r <= kk, f"{r} ≤ {kk}"),
        ("S is symmetric", np.allclose(S, S.T), "S = Sᵀ"),
        ("Diagonal of S is 1", np.allclose(np.diag(S)[nonzero], 1), "cos θ(d, d) = 1"),
        ("Values of S lie in [0, 1]", S.min() >= -1e-9 and S.max() <= 1 + 1e-9,
         f"min {S.min():.3f}, max {S.max():.3f}"),
        ("Eigenvectors are orthonormal", np.allclose(vecs.T @ vecs, np.eye(vecs.shape[1]), atol=1e-8), "VᵀV = I"),
        ("Sum of eigenvalues = trace(C)", np.isclose(vals.sum(), trace_C),
         f"{vals.sum():.4f} vs {trace_C:.4f}"),
        ("Eigenvalues match SVD", np.allclose(vals[:kk], sv[:kk] ** 2 / (n - 1), atol=1e-8), "λ = σ² / (n−1)"),
        ("Scores have zero mean", np.allclose(Z.mean(axis=0), 0, atol=1e-8), "mean(Z) = 0"),
        ("Score variance = eigenvalue", np.allclose(Z.var(axis=0, ddof=1), vals[:2], atol=1e-8), "var(PCᵢ) = λᵢ"),
    ]
    passed = sum(bool(ok) for _, ok, _ in checks)
    # top pairs, read straight from the similarity matrix S computed above
    iu = np.triu_indices(n, 1)
    order = np.argsort(-S[iu], kind="stable")[:4]
    st.markdown('<div class="stats">' + "".join(
        f'<div class="stat"><div class="stat-v">{S[iu][o] * 100:.1f}%</div>'
        f'<div class="stat-k">{hl[iu[0][o]]} &amp; {hl[iu[1][o]]}</div></div>'
        for o in order) + "</div>", unsafe_allow_html=True)
    note(f"Higher percentages mean the two documents use words in more similar proportions. "
         f"All calculations were verified: {passed} of {len(checks)} consistency checks passed.")

# ----------------------------------------------------------------------------
# Pixel Cat assistant: answers only from the results calculated above
# ----------------------------------------------------------------------------
facts = dict(
    n=n, m=m, r=r, labels=labels, docs=previews, vocab=vocab, A=A, norms=norms, G=G, S=S,
    vals=vals, var=var, Z=Z, trace=trace_C,
    best=(bi, bj, cs), worst=(lo_i, lo_j), closest=(pi, pj),
    top_words=[vocab[i] for i in np.argsort(-np.abs(V2[:, 0]))[:3]],
    checks=checks, passed=passed, drop_stop=drop_stop,
)
# ----------------------------------------------------------------------------
# 09 Export: the whole report as a PDF (built from the results above, nothing is recalculated)
# ----------------------------------------------------------------------------
with st.container(key="glass_export"):
    section("09", "Export report", "Save everything above (tables, charts, interpretations and checks) as a PDF.")
    if st.button("Generate PDF report", key="make_pdf"):
        with st.spinner("Building the PDF..."):
            try:
                st.session_state.pdf_report = (signature, build_pdf({**facts, "V2": V2}))
            except Exception as err:                       # never break the analysis because of the export
                st.session_state.pdf_report = None
                st.error(f"Sorry, the PDF could not be created ({type(err).__name__}: {err}).")
    ready = st.session_state.get("pdf_report")
    if ready and ready[0] == signature:                    # only offer a report that matches the current documents
        st.download_button("Download PDF report", data=ready[1], file_name="document_similarity_report.pdf",
                           mime="application/pdf", key="download_pdf")
        st.caption(f"Report ready ({len(ready[1]) / 1024:.0f} KB). Long collections are shortened on paper; "
                   "the calculations always use every document.")

render_panel(facts, signature)