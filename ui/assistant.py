"""
Pixel Shark's brain.

The shark does NOT call any AI service and does NOT calculate anything new.
Every answer is assembled from numbers the app has already computed
(rank, norms, inner products, similarity matrix, eigenvalues, explained variance,
projection and the verification checks), which arrive in the `facts` dict.

    answer(question, facts) -> ("success" | "error", text)
"""
import html
import re

import numpy as np

from .pixel_cat import bubble_html, sprite

SUGGESTIONS = {
    "Rank": "What is the rank of A?",
    "Cosine": "Which documents are the most similar by cosine similarity?",
    "Eigenvalues": "Explain the eigenvalues.",
    "PCA": "Explain the PCA result.",
}

_ORDINALS = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}
_DOC = r"(?:documents?|docs?|d)"
_JOIN = r"(?:,|and|&|vs\.?|versus|with|to|-|/)"
_DOC_REFS = re.compile(
    rf"\b{_DOC}\s*#?\s*(\d+(?:\s*{_JOIN}\s*(?:{_DOC}\s*)?#?\s*\d+|\s+{_DOC}\s*#?\s*\d+)*)")


def _has(q, *words):
    return any(w in q for w in words)


def _doc_numbers(q):
    m = _DOC_REFS.search(q)
    return [int(x) for x in re.findall(r"\d+", m.group(1))] if m else []


def _label_refs(q, labels):
    """Documents whose filename appears in the question (in order of appearance).
    Plain labels such as D1 are left to the number matcher above."""
    found = []
    for i, lab in enumerate(labels):
        if re.fullmatch(r"d\d+", lab.lower()):
            continue
        m = re.search(r"(?<![\w.])" + re.escape(lab.lower()) + r"(?!\w)", q)
        if m:
            found.append((m.start(), i))
    return [i for _, i in sorted(found)]


def _eig_index(q):
    m = (re.search(r"(?:eigenvalues?|lambda|λ|\bpc|components?)\s*#?\s*(\d+)", q)
         or re.search(r"\b(first|second|third|fourth|fifth)\s+(?:eigenvalue|principal|component|pc)", q))
    if not m:
        return None
    g = m.group(1)
    return _ORDINALS.get(g, None) if not g.isdigit() else int(g)


# ----------------------------------------------------------------------------
# Individual answers (each only reads values that are already computed)
# ----------------------------------------------------------------------------
def _rank(f):
    n, m, r = f["n"], f["m"], f["r"]
    out = [f"rank(A) = {r}.",
           f"A has {n} documents (rows) and {m} words (columns), so the rank can be at most min(n, m) = {min(n, m)}."]
    if r == n:
        out.append(f"The rank equals n, so all {n} documents are linearly independent: each one adds new information.")
    else:
        out.append(f"The rank is smaller than n = {n}, so {n - r} document(s) are linear combinations of the others "
                   "(redundant in the vector sense).")
    out.append(f"The documents span an {r}-dimensional subspace of ℝ^{m}.")
    return "\n".join(out)


def _pair(f, i, j):
    L, S, G, N = f["labels"], f["S"], f["G"], f["norms"]
    if i == j:
        return (f"{L[i]} compared with itself gives cos θ = {S[i, j]:.4f}: "
                "every document points in exactly the same direction as itself.")
    out = [f"The cosine similarity of {L[i]} and {L[j]} is {S[i, j]:.4f}.",
           f"From the tables: <{L[i]}, {L[j]}> = {G[i, j]:.2f}, ||{L[i]}|| = {N[i]:.4f}, ||{L[j]}|| = {N[j]:.4f}."]
    if G[i, j] == 0:
        out.append("The inner product is 0, so these two documents share no words (their vectors are orthogonal).")
    else:
        out.append("1 would mean identical word proportions and 0 no shared words.")
    return "\n".join(out)


def _neighbours(f, k):
    L, S = f["labels"], f["S"]
    order = [j for j in np.argsort(-S[k]) if j != k][:3]
    parts = ", ".join(f"{L[j]} ({S[k, j]:.4f})" for j in order)
    return (f"Documents most similar to {L[k]}, by cosine similarity: {parts}.\n"
            f"Your text for {L[k]}: \"{f['docs'][k]}\"")


def _similarity(f):
    L, S, G, N = f["labels"], f["S"], f["G"], f["norms"]
    bi, bj, cs = f["best"]
    wi, wj = f["worst"]
    return "\n".join([
        "Cosine similarity compares the angle between two document vectors, so document length does not matter.",
        f"Most similar pair: {L[bi]} and {L[bj]}, cos θ = {S[bi, bj]:.4f}.",
        f"Least similar pair: {L[wi]} and {L[wj]}, cos θ = {S[wi, wj]:.4f}.",
        f"Worked example: <{L[bi]}, {L[bj]}> = {G[bi, bj]:.2f}, ||{L[bi]}|| = {N[bi]:.4f}, "
        f"||{L[bj]}|| = {N[bj]:.4f}, so cos θ = {cs:.4f}.",
        "S is symmetric with 1s on the diagonal. Ask me about any pair, for example \"similarity of doc 1 and doc 2\" or use two filenames."])


def _eigen(f, idx=None):
    vals, var, m = f["vals"], f["var"], f["m"]
    if idx is not None:
        if not 1 <= idx <= m:
            return None
        k = idx - 1
        return (f"λ{idx} = {vals[k]:.4f}. It explains {var[k]:.2f}% of the variance "
                f"(cumulative {var[:idx].sum():.2f}%).\n"
                f"An eigenvalue is the variance of the documents along its principal component, "
                f"so PC{idx} carries {var[k]:.2f}% of the total.")
    show = min(5, len(vals))
    lam = ", ".join(f"λ{i + 1} = {vals[i]:.4f}" for i in range(show))
    nz = int(np.count_nonzero(vals))
    more = f" (first {show} of {len(vals)})" if len(vals) > show else ""
    return "\n".join([
        f"The covariance matrix C = X_cᵀ X_c / (n−1) has {m} eigenvalues, largest first{more}:",
        lam + ".",
        f"They add up to trace(C) = {f['trace']:.4f}. Only {nz} of them are non-zero, "
        f"so your documents really vary in {nz} direction(s).",
        f"Each eigenvalue is the variance along its principal component: PC1 explains {f['var'][0]:.2f}%."])


def _pca(f):
    var, L = f["var"], f["labels"]
    pi, pj = f["closest"]
    out = ["PCA centres A (X_c = A − mean), builds C = X_cᵀ X_c / (n−1) and finds its eigenvectors.",
           f"PC1 explains {var[0]:.1f}% of the variance and PC1 + PC2 together explain {var[:2].sum():.1f}%.",
           "Words with the largest weight on PC1: " + ", ".join(f["top_words"]) + ".",
           f"In the 2D projection the closest pair is {L[pi]} and {L[pj]}.",
           "The sign of an eigenvector is arbitrary, so a plot may appear mirrored."]
    if f["n"] < 3:
        out.append("With only 2 documents PCA has a single meaningful direction.")
    return "\n".join(out)


def _norms(f, k=None):
    L, N = f["labels"], f["norms"]
    if k is not None:
        return (f"||{L[k]}|| = {N[k]:.4f}. This is sqrt(<d, d>), the length of the document vector.\n"
                f"Your text for {L[k]}: \"{f['docs'][k]}\"")
    out = [f"The norm ||d|| = sqrt(<d, d>) is the length of a document vector.",
           f"{L[int(N.argmax())]} is the longest ({N.max():.4f}) and {L[int(N.argmin())]} the shortest ({N.min():.4f})."]
    if len(N) <= 8:
        out.append(", ".join(f"||{L[i]}|| = {N[i]:.4f}" for i in range(len(N))) + ".")
    out.append("Length depends on document size, which is why similarity uses the angle instead.")
    return "\n".join(out)


def _inner(f):
    L, G, n = f["labels"], f["G"], f["n"]
    bi, bj, _ = f["best"]
    iu = np.triu_indices(n, 1)
    zero, pairs = int(np.sum(G[iu] == 0)), len(iu[0])
    return "\n".join([
        "The inner product <u, v> = u1 v1 + u2 v2 + ... + um vm measures how many words two documents share.",
        f"{zero} of the {pairs} document pairs have inner product 0, meaning they share no words.",
        f"The most similar pair, {L[bi]} and {L[bj]}, has <{L[bi]}, {L[bj]}> = {G[bi, bj]:.2f}."])


def _features(f):
    A, vocab = f["A"], f["vocab"]
    counts = A.sum(axis=0)
    top = int(np.argmax(counts))
    out = [f"A is a {f['n']} × {f['m']} feature matrix: each row is a document, each column a word, "
           "and each entry counts how often the word appears.",
           f"There are {int(A.sum())} word occurrences in total. The most frequent word is "
           f"\"{vocab[top]}\" ({int(counts[top])} times)."]
    if f["drop_stop"]:
        out.append("Common words (the, and, of ...) were removed before counting.")
    return "\n".join(out)


def _verification(f):
    failed = [name for name, ok, _ in f["checks"] if not ok]
    out = [f"{f['passed']} of {len(f['checks'])} verification checks passed."]
    if failed:
        out.append("These checks failed: " + "; ".join(failed) + ".")
    else:
        out.append("They confirm, for example, that S is symmetric with 1s on the diagonal, the eigenvectors are "
                   "orthonormal and the eigenvalues match the SVD.")
    return "\n".join(out)


def _summary(f):
    L, S = f["labels"], f["S"]
    bi, bj, _ = f["best"]
    return "\n".join([
        f"{f['n']} documents and {f['m']} words give a {f['n']} × {f['m']} matrix A with rank {f['r']}.",
        f"Most similar pair: {L[bi]} and {L[bj]} (cos θ = {S[bi, bj]:.4f}).",
        f"PC1 + PC2 keep {f['var'][:2].sum():.1f}% of the variance.",
        f"{f['passed']} of {len(f['checks'])} verification checks passed."])


def greeting(f):
    if f is None:
        return ("Add at least two documents in the sidebar and I will start reading them. "
                "Once the analysis runs, ask me about rank, cosine similarity, eigenvalues or PCA.")
    return (f"Hi! I have read your {f['n']} documents ({f['m']} words). "
            "Ask me about rank, cosine similarity, eigenvalues or PCA, or tap a button below.")


# ----------------------------------------------------------------------------
# Question routing
# ----------------------------------------------------------------------------
def answer(question, f):
    """Return (state, text). state is 'success' or 'error' (drives the cat's face)."""
    q = " ".join(question.lower().split())
    if f is None:
        return "error", "I need at least two documents with results before I can answer. Add them in the sidebar."
    if not q:
        return "error", "Type a question first, or tap one of the buttons."

    n = f["n"]
    ks = _label_refs(q, f["labels"])          # "report.txt vs notes.txt"
    nums = [] if ks else _doc_numbers(q)      # "doc 2 and doc 5", "D3"
    if nums:
        bad = [x for x in nums if not 1 <= x <= n]
        if bad:
            return "error", f"I can only see documents 1 to {n} in this analysis, so document {bad[0]} does not exist."
        ks = [x - 1 for x in nums]
    if ks:
        if len(ks) >= 2:
            return "success", _pair(f, ks[0], ks[1])
        if _has(q, "norm", "length", "long"):
            return "success", _norms(f, ks[0])
        return "success", _neighbours(f, ks[0])

    if _has(q, "verif", "check", "pass", "fail", "valid", "correct", "trust", "consistent"):
        return "success", _verification(f)
    if _has(q, "rank", "independent", "redundan", "span", "linearly"):
        return "success", _rank(f)
    if _has(q, "eigen", "lambda", "λ") or re.search(r"\bpc\s*\d", q):
        text = _eigen(f, _eig_index(q))
        if text is None:
            return "error", f"There are only {f['m']} eigenvalues in this analysis."
        return "success", text
    if _has(q, "cosine", "similar", "angle", "similarity") or re.search(r"\bcos\b", q):
        return "success", _similarity(f)
    if _has(q, "pca", "principal", "component", "variance", "project", "2d", "dimension", "reduc"):
        return "success", _pca(f)
    if _has(q, "norm", "length", "magnitude"):
        return "success", _norms(f)
    if _has(q, "inner", "dot"):
        return "success", _inner(f)
    if _has(q, "vocab", "feature", "matrix", "word", "term", "count"):
        return "success", _features(f)
    if _has(q, "summar", "overview", "everything", "result"):
        return "success", _summary(f)
    if re.search(r"\b(hi|hello|hey)\b", q) or _has(q, "help", "what can you", "who are you"):
        return "success", greeting(f)
    return "error", ("I can only answer from the results on this page, and I did not recognise that question. "
                     "Try: rank, cosine similarity (for example \"similarity of doc 1 and doc 2\"), eigenvalues, PCA, "
                     "norms, inner products or the verification checks.")


# ----------------------------------------------------------------------------
# HTML for the panel (single-line strings so Markdown never treats them as code)
# ----------------------------------------------------------------------------
STATUS = {"idle": "Ready to help", "thinking": "Reading your results", "success": "Answer ready",
          "error": "Couldn't answer that"}


def _plain(text):
    return "<br>".join(html.escape(line) for line in text.split("\n"))


def _words(text):
    return [w for w in text.replace("\n", " \n ").split(" ") if w != ""]


def _step_ms(words):
    return max(12, min(32, int(2800 / max(1, len(words)))))


def reveal_seconds(text):
    """How long the typewriter reveal of `text` takes (the cat types for this long)."""
    words = _words(text)
    return len(words) * _step_ms(words) / 1000


def _typewriter(text):
    words = _words(text)
    step = _step_ms(words)
    parts = []
    for i, w in enumerate(words):
        last = " last" if i == len(words) - 1 else ""
        if w == "\n":
            parts.append("<br>")
        else:
            parts.append(f'<span class="w{last}" style="--i:{i}">{html.escape(w)}</span>')
    return f'<span class="tw" style="--step:{step}ms">{" ".join(parts)}</span>'


def message_html(msg):
    if msg["role"] == "you":
        return f'<div class="msg you">{html.escape(msg["text"])}</div>'
    cls = "msg cat err" if msg.get("error") else "msg cat"
    body = _typewriter(msg["text"]) if msg.get("fresh") else _plain(msg["text"])
    return f'<div class="{cls}">{body}</div>'


def thinking_html():
    # the shark swims across while the results are being read
    return ('<div class="msg cat"><span class="dots">Reading your results</span><span class="cursor"></span>'
            f'<div class="swim">{sprite("shark", 2)}</div></div>')


def screen_html(svg, state, messages, intro, thinking=False):
    """Mascot avatar + status + chat log for the floating panel."""
    log = "".join(message_html(m) for m in messages)
    if not messages:
        log = f'<div class="msg cat">{_plain(intro)}</div>'
    if thinking:
        log += thinking_html()
    bubble = bubble_html() if state == "idle" else ""      # typed lines only while resting
    return (f'<div class="cat-head"><div class="cat-avatar">{svg}</div>'
            f'<div class="cat-title"><b>Pixel Shark</b>'
            f'<span class="cat-status s-{state}">{STATUS[state]}</span>{bubble}</div></div>'
            f'<div class="cat-log"><div>{log}</div></div>')