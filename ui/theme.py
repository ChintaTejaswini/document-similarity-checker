"""
Visual theme for the Streamlit app: dreamy blue pixel-art workspace.

Palette
    baby blue  #BFE0FF   page glow, chips
    navy       #14213D   text on light surfaces, buttons
    lavender   #BBA8F5   badges, table headers, user chat bubbles
    white      #FFFFFF   glass panels, cards
    soft pink  #FFAFCB   cursor, focus ring, note accents

Rules the CSS follows
    * Sections sit on translucent frosted-glass panels.
    * Tables, matrices, charts, formulas and notes sit on SOLID light cards,
      so numbers never depend on what is behind them.
    * "Dark mode" only deepens the background overlay and the glass panels;
      cards stay light so every table and chart keeps the same strong contrast.
    * Fonts are applied to text elements only (never to `*`), so Streamlit's
      icon font keeps working and icon names are never shown as text.
"""
import base64
from functools import lru_cache
from pathlib import Path
from string import Template

from .pixel_cat import bubble_css

ASSET_BG = Path(__file__).resolve().parent.parent / "assets" / "background.jpg"

# Colours used inside Plotly charts. Charts always live on a solid light card.
CHART = dict(
    card="#FBFCFF", text="#14213D", muted="#3F4F80", grid="#DCE3F7",
    heat=[[0, "#F5F2FF"], [0.55, "#A8BDF0"], [1, "#1B2B5B"]],
    pt="#4B5FD1", dim="#C9D2F2", pink="#F28DB2",
)

DAY = dict(
    ink="#14213D", ink2="#33437A",
    glass="rgba(255,255,255,.74)", glass_edge="rgba(255,255,255,.85)",
    side="rgba(255,255,255,.82)",
    shadow="0 14px 40px rgba(20,33,61,.20)",
    overlay="linear-gradient(180deg, rgba(160,200,255,.30) 0%, rgba(60,90,180,.40) 55%, rgba(30,48,120,.55) 100%)",
    btn="#243A82", btn_ink="#FFFFFF", btn_hover="#5B49C9",
)
NIGHT = dict(
    ink="#EEF3FF", ink2="#C9D4F6",
    glass="rgba(14,23,58,.68)", glass_edge="rgba(190,205,255,.26)",
    side="rgba(11,18,46,.86)",
    shadow="0 14px 40px rgba(2,6,24,.50)",
    overlay="linear-gradient(180deg, rgba(14,26,78,.48) 0%, rgba(9,16,52,.64) 60%, rgba(6,11,38,.78) 100%)",
    btn="#C9BAF7", btn_ink="#14213D", btn_hover="#FFC2D9",
)


@lru_cache(maxsize=1)
def background_uri():
    """The cat-by-the-window picture as a data URI (read once, then cached)."""
    try:
        data = base64.b64encode(ASSET_BG.read_bytes()).decode("ascii")
        return f"data:image/jpeg;base64,{data}"
    except OSError:
        return ""          # missing file -> plain blue fallback colour is used


_CSS = Template(r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&family=Pixelify+Sans:wght@500;600;700&family=VT323&family=JetBrains+Mono:wght@400;500&display=swap');

:root{
  --ink:${ink}; --ink2:${ink2}; --glass:${glass}; --edge:${glass_edge}; --side:${side};
  --shadow:${shadow}; --btn:${btn}; --btn-ink:${btn_ink}; --btn-hover:${btn_hover};
  --card:#FBFCFF; --card-ink:#14213D; --card-ink2:#3F4F80; --card-line:#D6DEF6; --card-head:#ECE8FB;
  --navy:#14213D; --sky:#BFE0FF; --lav:#BBA8F5; --lav-soft:#E4DCFB; --pink:#FFAFCB; --pink-deep:#F28DB2;
  --ok:#0F766E; --bad:#BE123C;
  --body:'Nunito',system-ui,-apple-system,'Segoe UI',sans-serif;
  --pixel:'Pixelify Sans','Nunito',system-ui,sans-serif;
  --mono:'JetBrains Mono',ui-monospace,Consolas,monospace;
}

/* ---------- page background: photo + soft blur + blue overlay ---------- */
.stApp{isolation:isolate;background:#2F4F94;color:var(--ink);font-family:var(--body);}
.stApp::before{content:"";position:fixed;inset:-28px;z-index:-2;
  background:url("${bg}") center/cover no-repeat #2F4F94;filter:blur(7px) saturate(1.05);}
.stApp::after{content:"";position:fixed;inset:0;z-index:-1;background:${overlay};pointer-events:none;}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stAppViewContainer"],[data-testid="stMain"]{background:transparent;}
.block-container{max-width:1080px;padding:2.2rem 1.4rem 9rem;}

/* ---------- text ---------- */
.stApp :where(p,li,label,button,input,textarea,td,th,small,a,h1,h2,h3,h4,h5){font-family:var(--body);}
.stApp p,.stApp li,.stApp label,.stApp h1,.stApp h2,.stApp h3,.stApp h4,
.stApp [data-testid="stWidgetLabel"] p{color:var(--ink);}
.stApp small,.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] p{color:var(--ink2);}
/* keep Streamlit's own icon font intact so icon names never appear as text */
.stApp [data-testid="stIconMaterial"],.stApp .material-symbols-rounded,.stApp .material-icons{
  font-family:'Material Symbols Rounded','Material Icons'!important;}
.stApp :focus-visible{outline:3px solid var(--pink);outline-offset:2px;border-radius:10px;}

/* ---------- frosted glass panels ---------- */
[class*="st-key-glass"]{background:var(--glass);border:1px solid var(--edge);border-radius:24px;
  padding:1.3rem 1.5rem 1.5rem;box-shadow:var(--shadow);
  -webkit-backdrop-filter:blur(16px) saturate(1.3);backdrop-filter:blur(16px) saturate(1.3);
  transition:box-shadow .25s ease, transform .25s ease;}
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
  [class*="st-key-glass"],[data-testid="stSidebar"]{background:rgba(236,243,255,.96);}
}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{background:var(--side);border-right:1px solid var(--edge);
  -webkit-backdrop-filter:blur(18px) saturate(1.3);backdrop-filter:blur(18px) saturate(1.3);}
[data-testid="stSidebar"] > div:first-child{background:transparent;}
[data-testid="stSidebar"] h3{font-family:var(--pixel);font-size:1.3rem;font-weight:600;color:var(--ink);}
[data-testid="stSidebar"] :where(p,label,span,li){color:var(--ink);}
.stApp textarea,.stApp input[type="text"],.stApp [data-baseweb="textarea"],.stApp [data-baseweb="base-input"]{
  background:var(--card)!important;color:var(--card-ink)!important;border-radius:12px;}
.stApp [data-baseweb="textarea"],.stApp [data-baseweb="base-input"]{border:1px solid var(--card-line)!important;}
.stApp textarea::placeholder,.stApp input::placeholder{color:#5D6C9C!important;opacity:1;}
[data-testid="stFileUploaderDropzone"]{background:var(--card);border:1.5px dashed #94A9E3;border-radius:14px;}
[data-testid="stFileUploaderDropzone"] :where(span,small,p,div){color:#2B3A68!important;}

/* ---------- buttons (one style everywhere) ---------- */
.stApp [data-testid^="stBaseButton"]{background:var(--btn);color:var(--btn-ink);border:0;border-radius:12px;
  font-weight:700;box-shadow:0 3px 0 rgba(20,33,61,.28);
  transition:background .2s ease, transform .15s ease, box-shadow .15s ease;}
.stApp [data-testid^="stBaseButton"] :where(p,span,div){color:inherit;font-weight:700;}
.stApp [data-testid^="stBaseButton"]:hover{background:var(--btn-hover);color:var(--btn-ink);transform:translateY(-1px);}
.stApp [data-testid^="stBaseButton"]:active{transform:translateY(1px);box-shadow:0 1px 0 rgba(20,33,61,.28);}
[data-testid="stSidebar"][aria-expanded] [data-testid^="stBaseButton"]{box-shadow:none;}

/* ---------- alerts (info / warning shown before results exist) ---------- */
[data-testid="stAlert"]{background:var(--card);border:1px solid var(--card-line);border-radius:16px;
  box-shadow:0 8px 24px rgba(20,33,61,.14);}
[data-testid="stAlert"] :where(p,span,div){color:var(--card-ink);}

/* ---------- header, pipeline navigation ---------- */
.stApp .eyebrow{font-size:.9rem;font-weight:700;color:var(--ink2);margin-bottom:.35rem;}
.stApp .h1{font-family:var(--pixel);font-size:clamp(1.6rem,3.4vw,2.3rem);font-weight:600;line-height:1.15;
  color:var(--ink);margin:0;}
.stApp .lead{color:var(--ink2);margin:.55rem 0 1.1rem;font-size:1.02rem;max-width:62ch;}
.stApp .flow{display:flex;flex-wrap:wrap;gap:.45rem;align-items:center;}
.stApp .chip{display:inline-block;font-size:.8rem;font-weight:700;padding:.32rem .75rem;border-radius:999px;
  background:#FBFCFF;color:var(--navy);border:1px solid var(--card-line);text-decoration:none;
  transition:background .2s ease,transform .15s ease,box-shadow .2s ease;box-shadow:0 2px 0 rgba(20,33,61,.12);}
.stApp a.chip:hover{background:var(--lav-soft);transform:translateY(-1px);color:var(--navy);}
.stApp .arrow{color:var(--ink2);font-size:.85rem;}

/* ---------- summary cards ---------- */
.stApp .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:.8rem;margin:1.1rem 0 .4rem;}
.stApp .stat{background:var(--card);border:1px solid var(--card-line);border-radius:16px;padding:.9rem 1rem;
  box-shadow:0 6px 18px rgba(20,33,61,.12);}
.stApp .stat-v{font-family:var(--pixel);font-size:1.75rem;font-weight:600;color:var(--card-ink);line-height:1.1;}
.stApp .stat-k{font-size:.82rem;font-weight:600;color:var(--card-ink2);margin-top:.25rem;}

/* ---------- section headings, formulas, notes ---------- */
.stApp .sec{display:flex;gap:.9rem;align-items:flex-start;margin:0 0 .8rem;scroll-margin-top:1.2rem;}
.stApp .num{font-family:var(--pixel);font-size:.95rem;font-weight:600;color:var(--navy);background:var(--lav);
  border-radius:10px;padding:.2rem .55rem;margin-top:.1rem;}
.stApp .sec-title{font-family:var(--pixel);font-size:1.4rem;font-weight:600;color:var(--ink);line-height:1.2;}
.stApp .sec-sub{font-size:.95rem;color:var(--ink2);margin-top:.2rem;}
.stApp .formula{font-family:var(--mono);font-size:.84rem;color:var(--card-ink);background:#EEEAFD;
  border:1px solid #D5CCF7;border-radius:12px;padding:.55rem .85rem;margin:.2rem 0 .85rem;display:inline-block;
  max-width:100%;overflow-x:auto;}
.stApp .note{background:var(--card);border:1px solid var(--card-line);border-left:5px solid var(--pink-deep);
  border-radius:14px;padding:.7rem 1rem;margin:.95rem 0 0;color:var(--card-ink);font-size:.95rem;line-height:1.6;}
.stApp .note b{color:#2B2F9E;font-weight:800;}
.stApp .sub-label{font-size:.95rem;font-weight:700;color:var(--ink2);margin:.9rem 0 .4rem;}

/* ---------- tables: solid light cards ---------- */
.stApp .tbl-wrap{overflow-x:auto;border:1px solid var(--card-line);border-radius:16px;background:var(--card);
  box-shadow:0 6px 18px rgba(20,33,61,.12);}
.stApp table.tbl{border-collapse:collapse;width:100%;font-size:.88rem;font-variant-numeric:tabular-nums;}
.stApp .tbl th{background:var(--card-head)!important;font-weight:800;color:var(--card-ink);text-align:right;
  padding:.6rem .85rem;border-bottom:1px solid var(--card-line);white-space:nowrap;}
.stApp .tbl td{padding:.5rem .85rem;text-align:right;border-bottom:1px solid #E6EBFA;color:var(--card-ink);}
.stApp .tbl tbody tr:nth-child(even) td,.stApp .tbl tbody tr:nth-child(even) th{background:#F3F6FF!important;}
.stApp .tbl tbody th{text-align:left;color:var(--card-ink);font-weight:800;background:transparent!important;}
.stApp .tbl-wrap.left th,.stApp .tbl-wrap.left td{text-align:left;}
.stApp .tbl tr:last-child td,.stApp .tbl tr:last-child th{border-bottom:none;}
.stApp .tbl td.ok{color:var(--ok);font-weight:800;}
.stApp .tbl td.bad{color:var(--bad);font-weight:800;}

/* ---------- charts: solid light cards ---------- */
[data-testid="stPlotlyChart"]{background:var(--card);border:1px solid var(--card-line);border-radius:16px;
  padding:0;overflow:hidden;box-shadow:0 6px 18px rgba(20,33,61,.12);}

/* ================= Pixel Cat assistant panel ================= */
[class*="st-key-cat_panel"]{position:fixed!important;right:18px;bottom:18px;z-index:99990;
  width:min(372px,calc(100vw - 24px));background:rgba(250,252,255,.88);border:1px solid rgba(255,255,255,.95);
  border-radius:26px;padding:14px 14px 12px;gap:.55rem!important;box-shadow:0 18px 50px rgba(12,22,70,.38);
  -webkit-backdrop-filter:blur(18px) saturate(1.25);backdrop-filter:blur(18px) saturate(1.25);
  color:var(--card-ink);}
.st-key-cat_panel_min{width:auto;max-width:calc(100vw - 24px);}
[class*="st-key-cat_panel"] [data-testid="stHorizontalBlock"]{flex-wrap:nowrap!important;gap:.45rem!important;}
[class*="st-key-cat_panel"] [data-testid="stColumn"]{min-width:0!important;width:auto!important;flex:1 1 0!important;}
[class*="st-key-cat_panel"] [data-testid="stVerticalBlock"]{gap:.4rem!important;}
[class*="st-key-cat_panel"] [data-testid="stHorizontalBlock"]{align-items:center;}
[class*="st-key-cat_panel"] [data-testid="stElementContainer"]:not([class*="st-key-cat_toggle"]){width:100%!important;}
[class*="st-key-cat_panel"] [data-testid="stButton"],[class*="st-key-cat_panel"] [data-testid="stFormSubmitButton"],
[class*="st-key-cat_panel"] [data-testid="stTextInput"]{width:100%!important;}
[class*="st-key-cat_panel"] [data-testid^="stBaseButton"]{min-height:2.4rem;padding:.2rem .6rem;font-size:.82rem;width:100%;}
[class*="st-key-cat_panel"] [data-testid="stForm"] [data-testid="stColumn"]:first-child{flex:5 1 0!important;}
[class*="st-key-cat_panel"] [data-testid="stForm"] [data-testid="stColumn"]:last-child{flex:2 1 0!important;}
[class*="st-key-cat_panel"] [data-testid="stForm"]{border:0;padding:0;background:transparent;}
[class*="st-key-cat_panel"] [data-testid="stTextInput"] input{font-size:.88rem;}
.st-key-cat_toggle{position:absolute;top:12px;right:12px;width:auto!important;z-index:2;}
.st-key-cat_toggle [data-testid^="stBaseButton"]{background:transparent;color:#2B3A68;border:1px solid #BFCBEE;
  box-shadow:none;min-height:1.7rem;padding:.1rem .6rem;font-size:.74rem;width:auto!important;}
.st-key-cat_toggle [data-testid^="stBaseButton"]:hover{background:var(--lav-soft);color:var(--navy);transform:none;}

.cat-head{display:flex;gap:.75rem;align-items:center;padding-right:5.2rem;}
.cat-avatar{flex:0 0 auto;background:linear-gradient(180deg,#DCEBFF,#EDE6FF);border-radius:18px;padding:6px 6px 2px;
  border:1px solid #D0DBF7;}
.cat-title b{font-family:var(--pixel);font-size:1.15rem;font-weight:600;color:var(--card-ink);display:block;}
.cat-status{display:inline-block;margin-top:.25rem;font-size:.74rem;font-weight:800;padding:.12rem .55rem;border-radius:999px;}
.cat-status.s-idle{background:#E4DCFB;color:#2B2468;}
.cat-status.s-thinking{background:#CFE5FF;color:#12315F;}
.cat-status.s-success{background:#D8F4E6;color:#0B4B33;}
.cat-status.s-error{background:#FFDCE8;color:#8A1236;}
.cat-log{display:flex;flex-direction:column-reverse;max-height:min(250px,32vh);overflow-y:auto;margin-top:.55rem;
  padding:.1rem .15rem .1rem 0;scrollbar-width:thin;}
.msg{max-width:94%;padding:.5rem .8rem;border-radius:16px;font-size:.88rem;line-height:1.5;margin:.22rem 0;
  overflow-wrap:anywhere;}
.msg.you{background:#DDD4FA;color:#14213D;margin-left:auto;border-bottom-right-radius:5px;font-weight:600;}
.msg.cat{background:#FFFFFF;color:#14213D;border:1px solid var(--card-line);border-bottom-left-radius:5px;}
.msg.cat.err{background:#FFF1F6;border-color:#FFB3CD;}
.cursor{display:inline-block;width:.5em;height:1.05em;margin-left:3px;vertical-align:-.18em;background:var(--pink-deep);
  animation:cur-blink 1s steps(1) infinite;}
.dots::after{content:"";animation:dots 1.2s steps(1) infinite;}
@keyframes cur-blink{0%,50%{opacity:1}50.01%,100%{opacity:0}}
@keyframes dots{0%{content:""}25%{content:"."}50%{content:".."}75%{content:"..."}}

/* typewriter reveal: words appear one after another, the cursor follows the newest word */
.tw .w{position:relative;display:inline-block;opacity:0;animation:tw-in 0s linear forwards;
  animation-delay:calc(var(--i) * var(--step));}
.tw .w::after{content:"";position:absolute;left:100%;top:.2em;width:.5em;height:1.05em;margin-left:2px;
  background:var(--pink-deep);opacity:0;animation:tw-cur var(--step) steps(1) 1;
  animation-delay:calc(var(--i) * var(--step));}
.tw .w.last::after{animation:cur-blink 1s steps(1) infinite;animation-delay:calc(var(--i) * var(--step));}
@keyframes tw-in{to{opacity:1}}
@keyframes tw-cur{0%,100%{opacity:1}}

/* ---------- mascot (pixel shark) ---------- */
.cat-avatar{position:relative;overflow:hidden;}
.pcat{position:relative;}
.pcat .px,.swim .px,.bubble .px{display:block;image-rendering:crisp-edges;image-rendering:pixelated;}
.pcat .pc-body{position:relative;z-index:1;animation:pc-breathe 3s steps(1) infinite;}
.pcat.typing .pc-body{animation:pc-bob .5s steps(1) var(--bob,infinite);}
.pcat.s-error .pc-body{animation:pc-shake .4s steps(1) 2;}
.pcat .pc-shark{position:absolute;left:0;bottom:0;z-index:0;animation:pc-swim 16s steps(76) infinite;}
.pcat .pc-heart{position:absolute;top:-6px;right:-2px;z-index:2;opacity:0;animation:pc-heart 1.8s var(--done,0s) 1 both;}
.swim{position:relative;height:38px;overflow:hidden;margin-top:.4rem;}
.swim .px{position:absolute;bottom:0;left:0;animation:pc-lane 5s steps(150) infinite;}
@keyframes pc-breathe{0%,50%{transform:translateY(0)}50.01%,100%{transform:translateY(-2px)}}
@keyframes pc-bob{0%{transform:translateY(0)}50%{transform:translateY(-2px)}}
@keyframes pc-shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-2px)}75%{transform:translateX(2px)}}
@keyframes pc-swim{from{transform:translateX(-64px)}to{transform:translateX(88px)}}
@keyframes pc-lane{from{left:-64px}to{left:100%}}
@keyframes pc-heart{0%{opacity:0;transform:translateY(4px)}20%,70%{opacity:1;transform:translateY(0)}100%{opacity:0;transform:translateY(-4px)}}

/* speech bubble: lines are typed one character at a time (keyframes are generated in pixel_cat.py) */
.bubble{position:relative;display:flex;align-items:center;gap:6px;width:fit-content;max-width:100%;margin:.5rem 0 0 8px;
  padding:.12rem .55rem;background:#fff;border:2px solid #2B3A68;border-radius:10px;box-shadow:0 3px 0 rgba(20,33,61,.22);
  font-family:'VT323',ui-monospace,monospace;font-size:1.2rem;line-height:1.25;color:var(--card-ink);}
.bubble::before{content:"";position:absolute;left:-7px;top:50%;width:8px;height:8px;background:#fff;
  border-left:2px solid #2B3A68;border-bottom:2px solid #2B3A68;transform:translateY(-50%) rotate(45deg);}
.bubble .tl{display:inline-flex;align-items:center;white-space:nowrap;}
.bubble .tl::after{content:"";width:.5em;height:.85em;margin-left:2px;background:var(--pink-deep);animation:cur-blink 1s steps(1) infinite;}
.bubble .ln{display:inline-block;overflow:hidden;white-space:nowrap;width:0;}
.bubble .px{flex:0 0 auto;opacity:0;}

/* ---------- responsive ---------- */
@media (max-width:900px){.block-container{padding:1.4rem 1rem 9rem;}}
@media (max-width:760px){
  .stApp .stats{grid-template-columns:repeat(2,1fr);}
  [class*="st-key-glass"]{padding:1rem 1rem 1.2rem;border-radius:20px;}
  [class*="st-key-cat_panel"]{right:10px;bottom:10px;border-radius:22px;}
  .cat-log{max-height:130px;}
}
@media (max-height:640px){.cat-log{max-height:104px;}}
@media (prefers-reduced-motion:reduce){
  .tw .w{opacity:1;animation:none;}
  .tw .w::after,.cursor,.dots::after{animation:none;opacity:0;}
  .pcat,.pcat *,.swim .px{animation:none!important;}
  .pcat .pc-shark{display:none;}
  .bubble .ln{animation:none!important;width:auto!important;}
  .bubble .ln:not(:first-child),.bubble .px{display:none;}
  .stApp [data-testid^="stBaseButton"],.stApp .chip{transition:none;}
}
</style>
""")


def build_css(dark=False):
    tokens = dict(NIGHT if dark else DAY)
    tokens["bg"] = background_uri()
    return _CSS.substitute(tokens).replace("</style>", bubble_css() + "\n</style>")