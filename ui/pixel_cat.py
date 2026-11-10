"""
Pixel Shark - the mascot, shown as three pixel-art PNGs (assets/mascot.png, shark.png, heart.png).

The file and function names (cat_svg) are kept so panel.py and assistant.py keep working.

    mascot  the shark-hoodie character (always visible)
    shark   swims behind the mascot when idle, and across the "Reading your results" bubble
    heart   pops up when an answer has finished typing

States passed to cat_svg():
    idle      mascot breathes, shark swims behind it
    thinking  mascot bobs 2px up and down
    success   mascot bobs while the answer is typed, then stops and a heart fades in and out
    error     mascot shakes side to side twice

All animation is CSS (ui/theme.py). The typing speech bubble is built by bubble_html() + bubble_css().
"""
import base64
import html
import math
from functools import lru_cache
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"
NATIVE = {"mascot": (37, 52), "shark": (31, 19), "heart": (14, 12)}     # size in art pixels

# ---- speech bubble: edit these (keep each line under ~16 characters so it fits) ----
BUBBLE_LINES = ["Hi, I'm Shark!", "Ask about rank", "Try cosine!", "PCA = 2D map"]
TYPE_MS = 60        # milliseconds per typed character
ERASE_MS = 30       # milliseconds per deleted character
PAUSE_S = 1.5       # how long a finished line stays on screen


@lru_cache(maxsize=None)
def _uri(name):
    """A PNG from assets/ as a data URI (read once, then cached)."""
    try:
        return "data:image/png;base64," + base64.b64encode((ASSETS / f"{name}.png").read_bytes()).decode("ascii")
    except OSError:
        return ""


def sprite(name, scale=2, cls=""):
    """One sprite as an <img>, scaled by a whole number so the pixels stay sharp."""
    w, h = NATIVE[name]
    return f'<img class="px {cls}" src="{_uri(name)}" width="{w * scale}" height="{h * scale}" alt="">'


def cat_svg(state="idle", typing=False, size=108, label=None, typing_for=None):
    """Return the mascot as an HTML string (same signature as the old cat drawing).

    typing_for  seconds the mascot bobs for; afterwards the bobbing stops and the heart appears
    size        about how wide to draw it; it is rounded to a whole-number scale (108 -> 2x)
    """
    if state not in ("idle", "thinking", "success", "error"):
        state = "idle"
    scale = max(1, size // 40)
    style = ""
    if typing_for:
        typing = True
        style = f' style="--bob:{max(1, math.ceil(typing_for / 0.5))};--done:{typing_for:.2f}s"'
    classes = f"pcat s-{state}" + (" typing" if typing else "")
    shark = sprite("shark", scale, "pc-shark") if state == "idle" else ""
    heart = sprite("heart", scale, "pc-heart") if state == "success" else ""
    aria = label or "Pixel Shark mascot"
    return (f'<div class="{classes}"{style} role="img" aria-label="{aria}">'
            f'{shark}<div class="pc-body">{sprite("mascot", scale)}</div>{heart}</div>')


# ----------------------------------------------------------------------------
# Typing speech bubble
# ----------------------------------------------------------------------------
def _timeline():
    """For each line: (start, typed, held, end, characters) in seconds; plus the whole loop length."""
    t, rows = 0.0, []
    for text in BUBBLE_LINES:
        n = len(text)
        typed = t + n * TYPE_MS / 1000
        held = typed + PAUSE_S
        end = held + n * ERASE_MS / 1000
        rows.append((t, typed, held, end, n))
        t = end + 0.2
    return rows, t


def bubble_css():
    """Keyframes for the bubble. Each line grows from 0 to n characters (steps(n) = one character
    per step), waits, then shrinks back. Only one line is wider than 0 at any moment."""
    rows, total = _timeline()
    pct = lambda s: f"{s / total * 100:.3f}%"
    css = []
    for k, (start, typed, held, end, n) in enumerate(rows, 1):
        w = f"{n}ch"
        typing_in = f"width:0;animation-timing-function:steps({n},end)"
        first = f"0%{{{typing_in}}}" if start == 0 else f"0%{{width:0}}{pct(start)}{{{typing_in}}}"
        css.append(f"@keyframes tl{k}{{{first}{pct(typed)}{{width:{w};animation-timing-function:linear}}"
                   f"{pct(held)}{{width:{w};animation-timing-function:steps({n},end)}}"
                   f"{pct(end)}{{width:0}}100%{{width:0}}}}")
        css.append(f".bubble .ln:nth-child({k}){{animation:tl{k} {total:.2f}s linear infinite;}}")
    # the heart fades in and out each time a line has finished typing
    stops = "".join(f"{pct(typed)}{{opacity:0}}{pct(typed + .25)}{{opacity:1}}"
                    f"{pct(typed + 1.1)}{{opacity:1}}{pct(typed + 1.4)}{{opacity:0}}"
                    for _, typed, _, _, _ in rows)
    css.append(f"@keyframes tlh{{0%{{opacity:0}}{stops}100%{{opacity:0}}}}")
    css.append(f".bubble .px{{animation:tlh {total:.2f}s linear infinite;}}")
    return "\n".join(css)


def bubble_html():
    """The speech bubble: lines typed one character at a time, a blinking block cursor, a heart."""
    lines = "".join(f'<span class="ln">{html.escape(t)}</span>' for t in BUBBLE_LINES)
    return f'<div class="bubble"><span class="tl">{lines}</span>{sprite("heart", 1)}</div>'