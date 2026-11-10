"""
The floating Pixel Shark panel (bottom-right).

Flow when a question is asked:
    1. the mascot starts bobbing and the shark swims across while a
       blinking cursor shows it is working,
    2. the answer is looked up in the results the app already computed,
    3. the answer is typed out word by word (the mascot bobs, then a heart pops up) or the mascot
       shakes (error), then it settles back to the idle face.
"""
import time

import streamlit as st

from .assistant import SUGGESTIONS, answer, greeting, reveal_seconds, screen_html
from .pixel_cat import cat_svg


def _ask(question):
    st.session_state.cat_pending = question


def _ask_from_form():
    st.session_state.cat_pending = st.session_state.get("cat_q", "").strip() or " "


def _is_phone():
    """True for phone browsers, so the panel starts minimised and does not cover the page."""
    try:
        ua = st.context.headers.get("User-Agent", "")
    except Exception:          # older Streamlit versions have no st.context
        return False
    return any(w in ua for w in ("iPhone", "Android", "Mobile"))


def _toggle():
    st.session_state.cat_open = not st.session_state.get("cat_open", True)


def render_panel(facts, signature):
    """facts: dict of computed results (or None before there is anything to analyse).
    signature: changes whenever the documents / options change, which clears old answers."""
    ss = st.session_state
    ss.setdefault("cat_open", not _is_phone())
    ss.setdefault("cat_msgs", [])
    ss.setdefault("cat_pending", None)
    if ss.get("cat_sig") != signature:       # new input -> old answers no longer apply
        ss.cat_sig = signature
        ss.cat_msgs = []
        ss.cat_pending = None
    pending, ss.cat_pending = ss.cat_pending, None
    rest = "error" if facts is None else "idle"
    intro = greeting(facts)

    # ---------------- minimised: just the cat and one button ----------------
    if not ss.cat_open:
        with st.container(key="cat_panel_min"):
            st.markdown(f'<div class="cat-avatar" style="width:fit-content;margin:0 auto">'
                        f'{cat_svg(rest, size=92)}</div>', unsafe_allow_html=True)
            st.button("Ask Sharky", key="cat_toggle_min", on_click=_toggle)
        return

    # ---------------- open panel ----------------
    with st.container(key="cat_panel"):
        st.button("Minimise", key="cat_toggle", on_click=_toggle)
        screen = st.empty()
        left, right = st.columns(2)
        for i, (label, question) in enumerate(SUGGESTIONS.items()):
            with (left if i % 2 == 0 else right):
                st.button(label, key=f"cat_quick_{label}", on_click=_ask, args=(question,))
        with st.form("cat_form", clear_on_submit=True):
            c1, c2 = st.columns([5, 2])
            with c1:
                st.text_input("Ask Sharky", key="cat_q", label_visibility="collapsed",
                              placeholder="Ask about rank, cosine, eigenvalues...")
            with c2:
                st.form_submit_button("Ask", on_click=_ask_from_form)

        if pending is None:                   # resting view (also used for plain reruns)
            screen.markdown(screen_html(cat_svg(rest), rest, ss.cat_msgs, intro), unsafe_allow_html=True)
            return

        # 1) thinking: paws tap, cursor blinks
        question = pending.strip()
        ss.cat_msgs.append({"role": "you", "text": question or "(empty question)"})
        screen.markdown(screen_html(cat_svg("thinking", typing=True), "thinking", ss.cat_msgs, intro,
                                    thinking=True), unsafe_allow_html=True)
        time.sleep(0.8)
        # 2) look the answer up in the existing results
        state, text = answer(question, facts)
        ss.cat_msgs.append({"role": "cat", "text": text, "error": state == "error", "fresh": True})
        # 3) type it out; the cat taps for as long as the reveal lasts
        svg = cat_svg(state, typing_for=None if state == "error" else reveal_seconds(text))
        screen.markdown(screen_html(svg, state, ss.cat_msgs, intro), unsafe_allow_html=True)
        for msg in ss.cat_msgs:               # later reruns show it without replaying the typing
            msg.pop("fresh", None)