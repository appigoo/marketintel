# utils/css.py — Global CSS injection for MarketIntel

import streamlit as st

def inject_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Bebas+Neue&family=Noto+Sans+TC:wght@400;500;700;900&display=swap');

/* ── ROOT VARS ── */
:root {
  --bg:#07080a; --ink:#0e1015; --card:#12151b; --line:#1c2030;
  --muted:#2e3650; --dim:#4a5270; --body:#8892aa;
  --bright:#d4daf0; --white:#eef2ff;
  --bull:#00e676; --bull-dim:#00e67614;
  --bear:#ff3d57; --bear-dim:#ff3d5714;
  --warn:#ffab00; --warn-dim:#ffab0014;
  --ice:#00b8ff;  --ice-dim:#00b8ff14;
  --lav:#b388ff;  --lav-dim:#b388ff14;
  --fd:'Bebas Neue',sans-serif;
  --fb:'Noto Sans TC',sans-serif;
  --fm:'DM Mono',monospace;
}

/* ── GLOBAL RESET ── */
html, body, [class*="css"] {
  background-color: var(--bg) !important;
  color: var(--body) !important;
  font-family: var(--fb) !important;
}

/* ── HIDE STREAMLIT CHROME ── */
#MainMenu, footer, header { visibility: hidden !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }
section[data-testid="stSidebar"] { display: none !important; }
.stDeployButton { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--muted); border-radius: 2px; }

/* ── TOP BAR ── */
.mi-topbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px; height: 50px;
  background: var(--ink); border-bottom: 1px solid var(--line);
  position: sticky; top: 0; z-index: 200;
}
.mi-brand { font-family: var(--fd); font-size: 20px; letter-spacing: .08em; color: var(--white); }
.mi-brand span { color: var(--ice); }
.mi-topbar-right { display: flex; align-items: center; gap: 14px; font-family: var(--fm); font-size: 10px; }
.mi-live { display: flex; align-items: center; gap: 5px; color: var(--bull); }
.mi-pdot { width: 6px; height: 6px; border-radius: 50%; background: var(--bull);
  animation: pa 1.4s ease-in-out infinite; display: inline-block; }
@keyframes pa { 0%,100%{opacity:1} 50%{opacity:.2} }
.mi-clock { color: var(--ice); font-family: var(--fm); }
.mi-src { padding: 2px 7px; border-radius: 20px; font-size: 9px; letter-spacing: .08em;
  border: 1px solid var(--bull); color: var(--bull); margin-right: 2px; }

/* ── HERO VERDICT ── */
.mi-hero {
  padding: 22px 28px 18px; border-bottom: 1px solid var(--line);
  background: linear-gradient(135deg, #0e101508 0%, var(--bg) 60%);
  position: relative; overflow: hidden;
}
.mi-hero::before {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(ellipse 45% 90% at 5% 50%, #b388ff06 0%, transparent 70%);
  pointer-events: none;
}
.mi-eyebrow {
  font-family: var(--fm); font-size: 9px; letter-spacing: .2em;
  color: var(--lav); margin-bottom: 8px; text-transform: uppercase;
  display: flex; align-items: center; gap: 8px;
}
.mi-eyebrow::after { content:''; flex:1; height:1px; background:var(--line); }
.mi-headline {
  font-family: var(--fd); font-size: 38px; letter-spacing: .04em;
  color: var(--white); line-height: 1.1; margin-bottom: 10px;
}
.mi-sub { font-size: 13px; color: var(--body); line-height: 1.65; margin-bottom: 16px; }
.mi-sub strong { color: var(--bright); }

/* ── SIGNAL PILLS ── */
.mi-sigs { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 4px; }
.mi-sig {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 13px; border-radius: 5px; border: 1px solid;
  font-family: var(--fm); font-size: 10px; font-weight: 500;
}
.sg-bull { color:var(--bull); border-color:var(--bull); background:var(--bull-dim); }
.sg-bear { color:var(--bear); border-color:var(--bear); background:var(--bear-dim); }
.sg-warn { color:var(--warn); border-color:var(--warn); background:var(--warn-dim); }
.sg-ice  { color:var(--ice);  border-color:var(--ice);  background:var(--ice-dim);  }
.sg-lav  { color:var(--lav);  border-color:var(--lav);  background:var(--lav-dim);  }

/* ── SCORECARD ROW ── */
.mi-cards { display: grid; grid-template-columns: repeat(4, 1fr); border-bottom: 1px solid var(--line); }
.mi-card {
  padding: 16px 18px; border-right: 1px solid var(--line);
  position: relative; transition: background .2s; cursor: default;
}
.mi-card:last-child { border-right: none; }
.mi-card:hover { background: var(--card); }
.mi-card::before { content:''; position:absolute; top:0; left:0; right:0; height:2px; }
.mi-card-kw { font-family:var(--fm); font-size:9px; letter-spacing:.1em; color:var(--dim); margin-bottom:5px; }
.mi-card-vd { font-family:var(--fd); font-size:18px; letter-spacing:.05em; line-height:1; margin-bottom:3px; }
.vd-bull{color:var(--bull)} .vd-warn{color:var(--warn)} .vd-bear{color:var(--bear)} .vd-neut{color:var(--dim)}
.mi-card-rsn { font-size:10px; color:var(--body); line-height:1.4; margin-bottom:8px; }
.mi-stat-row { display:flex; gap:10px; margin-top:4px; }
.mi-stat { font-family:var(--fm); font-size:9px; }
.mi-sv { color:var(--bright); } .mi-sl { color:var(--dim); }

/* ── SECTION HEADER ── */
.mi-sec-hdr {
  display: flex; align-items: center; justify-content: space-between;
  padding: 11px 22px; border-bottom: 1px solid var(--line);
  background: var(--ink);
}
.mi-sec-title { font-family:var(--fm); font-size:9px; letter-spacing:.18em; color:var(--dim); text-transform:uppercase; }
.mi-sec-note { font-size:11px; color:var(--body); }

/* ── AI VERDICT PANEL ── */
.mi-ai-panel {
  padding: 18px 20px; border-bottom: 1px solid var(--line);
  background: linear-gradient(180deg, #b388ff06 0%, transparent 50%);
}
.mi-ai-eye { font-family:var(--fm); font-size:8px; letter-spacing:.18em; color:var(--lav); margin-bottom:10px; }
.mi-score-row { display:flex; align-items:baseline; gap:8px; margin-bottom:8px; }
.mi-score-num { font-family:var(--fd); font-size:60px; line-height:1; }
.mi-score-label strong { display:block; font-family:var(--fd); font-size:18px; letter-spacing:.05em; color:var(--bright); }
.mi-score-label { font-size:11px; color:var(--body); }
.mi-ai-sum { font-size:11px; color:var(--body); line-height:1.65; margin-bottom:12px; }
.mi-ai-sum strong { color:var(--bright); }
.mi-action {
  display:flex; align-items:flex-start; gap:8px; padding:7px 10px;
  border-radius:4px; border:1px solid var(--line); background:var(--card);
  font-size:10px; line-height:1.4; margin-bottom:5px;
}
.mi-action-icon { font-size:12px; flex-shrink:0; margin-top:1px; }
.mi-action-txt { color:var(--body); }
.mi-action-txt strong { color:var(--bright); }

/* ── ALERT ITEMS ── */
.mi-alert {
  display:flex; align-items:flex-start; gap:8px;
  padding:8px 10px; border-radius:4px; border:1px solid; border-left-width:3px;
  font-size:10px; line-height:1.4; margin-bottom:5px;
}
.al-cr{border-color:var(--bear);background:var(--bear-dim)}
.al-wn{border-color:var(--warn);background:var(--warn-dim)}
.al-in{border-color:var(--ice);background:var(--ice-dim)}
.mi-alert-h{color:var(--bright);font-weight:700;margin-bottom:2px}
.mi-alert-d{color:var(--body)}
.mi-alert-t{font-family:var(--fm);font-size:8px;color:var(--dim);flex-shrink:0;align-self:center}

/* ── COMMUNITY ITEMS ── */
.mi-ci {
  display:flex; align-items:center; gap:8px;
  padding:8px 10px; border-radius:4px; background:var(--card);
  border:1px solid var(--line); margin-bottom:5px;
  transition:border-color .15s;
}
.mi-ci:hover{border-color:var(--muted)}
.mi-ci-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.mi-ci-name{font-size:11px;color:var(--bright);font-weight:700}
.mi-ci-tags{font-size:9px;color:var(--dim);margin-top:1px}
.mi-ci-count{font-family:var(--fm);font-size:10px;color:var(--body)}
.mi-ci-delta{font-family:var(--fm);font-size:8px}

/* ── FLOW ITEMS ── */
.mi-flow {
  display:flex; align-items:center; gap:7px; margin-bottom:6px;
}
.mi-flow-from{font-family:var(--fm);font-size:9px;padding:3px 8px;border-radius:3px;border:1px solid;width:65px;text-align:center;flex-shrink:0}
.mi-flow-arr{color:var(--muted);font-size:11px}
.mi-flow-to{font-family:var(--fm);font-size:9px;padding:3px 8px;border-radius:3px;border:1px solid;flex:1;text-align:center}
.mi-flow-str{font-family:var(--fm);font-size:8px;width:28px;text-align:right;flex-shrink:0}

/* ── CORR CARDS ── */
.mi-corr-card {
  background:var(--card); border:1px solid var(--line); border-radius:5px;
  padding:10px 12px; margin-bottom:6px;
}
.mi-corr-pair{font-family:var(--fm);font-size:10px;font-weight:500;color:var(--bright)}
.mi-corr-r{font-family:var(--fd);font-size:18px;line-height:1}
.mi-corr-bar-bg{height:5px;background:var(--line);border-radius:2px;overflow:hidden;margin:5px 0}
.mi-corr-bar{height:100%;border-radius:2px}
.mi-corr-desc{font-size:10px;color:var(--body);line-height:1.4}
.mi-corr-lag{font-family:var(--fm);font-size:9px;margin-top:3px}

/* ── HIST INSIGHT ── */
.mi-hist-insight {
  background:var(--card); border:1px solid var(--line); border-radius:5px;
  padding:12px; margin-bottom:8px;
}
.mi-hi-title{font-family:var(--fm);font-size:8px;letter-spacing:.15em;color:var(--ice);margin-bottom:6px}
.mi-hi-txt{font-size:11px;color:var(--body);line-height:1.6}
.mi-hi-txt strong{color:var(--bright)}
.mi-stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-top:8px}
.mi-stat-box{text-align:center;background:var(--ink);border-radius:4px;padding:6px 4px}
.mi-stat-big{font-family:var(--fd);font-size:18px;line-height:1;margin-bottom:2px}
.mi-stat-lbl{font-family:var(--fm);font-size:8px;color:var(--dim)}

/* ── TABLES ── */
.mi-table{width:100%;border-collapse:collapse;font-family:var(--fm);font-size:10px}
.mi-table th{text-align:left;padding:6px 10px;font-size:8px;letter-spacing:.12em;color:var(--dim);border-bottom:1px solid var(--line)}
.mi-table td{padding:7px 10px;border-bottom:1px solid var(--line)}
.mi-table tr:last-child td{border-bottom:none}
.mi-table tr:hover td{background:var(--card)}

/* ── LAG BADGE ── */
.lag-lead{padding:2px 7px;border-radius:3px;font-size:8px;border:1px solid;color:var(--bull);border-color:var(--bull);background:var(--bull-dim)}
.lag-sync{padding:2px 7px;border-radius:3px;font-size:8px;border:1px solid;color:var(--ice);border-color:var(--ice);background:var(--ice-dim)}
.lag-weak{padding:2px 7px;border-radius:3px;font-size:8px;border:1px solid;color:var(--warn);border-color:var(--warn);background:var(--warn-dim)}

/* ── INPUT ELEMENTS OVERRIDE ── */
div[data-testid="stTextInput"] input {
  background: var(--card) !important; color: var(--bright) !important;
  border: 1px solid var(--line) !important; border-radius: 4px !important;
  font-family: var(--fm) !important; font-size: 12px !important;
}
div[data-testid="stTextInput"] input:focus { border-color: var(--ice) !important; }
div[data-testid="stSelectbox"] select,
div[data-testid="stMultiSelect"] {
  background: var(--card) !important; color: var(--bright) !important;
  border: 1px solid var(--line) !important;
}
.stButton > button {
  background: transparent !important; color: var(--ice) !important;
  border: 1px solid var(--ice) !important; border-radius: 4px !important;
  font-family: var(--fm) !important; font-size: 11px !important;
  letter-spacing: .12em !important; transition: all .2s !important;
}
.stButton > button:hover {
  background: var(--ice-dim) !important;
  box-shadow: 0 0 16px #00b8ff22 !important;
}
div[data-testid="stTabs"] button {
  font-family: var(--fm) !important; font-size: 10px !important;
  letter-spacing: .12em !important; color: var(--dim) !important;
  background: transparent !important; border: none !important;
  border-bottom: 2px solid transparent !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--ice) !important;
  border-bottom-color: var(--ice) !important;
}
div[data-testid="stTabs"] { border-bottom: 1px solid var(--line) !important; }
[data-testid="stMetric"] { background: var(--card); border:1px solid var(--line); border-radius:5px; padding:10px 12px; }
[data-testid="stMetricLabel"] { color: var(--dim) !important; font-family: var(--fm) !important; font-size: 9px !important; }
[data-testid="stMetricValue"] { color: var(--bright) !important; font-family: var(--fd) !important; }
[data-testid="stMetricDelta"] { font-family: var(--fm) !important; font-size: 10px !important; }

/* spinner */
.stSpinner { color: var(--ice) !important; }
div[data-testid="stSpinner"] p { color: var(--ice) !important; font-family: var(--fm) !important; font-size: 11px !important; }
</style>
""", unsafe_allow_html=True)


def topbar_html(time_str: str = "") -> str:
    return f"""
<div class="mi-topbar">
  <div class="mi-brand">MARKET<span>INTEL</span></div>
  <div class="mi-topbar-right">
    <span class="mi-src">G.TRENDS</span>
    <span class="mi-src">STOCKTWITS</span>
    <span class="mi-src">REDDIT</span>
    <span class="mi-src">YFINANCE</span>
    <div class="mi-live"><div class="mi-pdot"></div>LIVE</div>
    <div class="mi-clock">{time_str} HKT</div>
  </div>
</div>"""


def hero_html(headline: str, sub: str, signals: list[dict]) -> str:
    sigs_html = "".join(
        f'<span class="mi-sig {s["cls"]}">{s["icon"]} {s["text"]}</span>'
        for s in signals
    )
    return f"""
<div class="mi-hero">
  <div class="mi-eyebrow">AI 綜合結論 · 即時分析</div>
  <div class="mi-headline">{headline}</div>
  <div class="mi-sub">{sub}</div>
  <div class="mi-sigs">{sigs_html}</div>
</div>"""


def scorecard_row_html(cards: list[dict]) -> str:
    """cards: [{kw, verdict, verdict_cls, reason, stats:[{val,lbl}], color}]"""
    items = []
    for c in cards:
        stats_html = "".join(
            f'<div class="mi-stat"><div class="mi-sv" style="color:{s["color"]}">{s["val"]}</div><div class="mi-sl">{s["lbl"]}</div></div>'
            for s in c.get("stats", [])
        )
        items.append(f"""
<div class="mi-card" style="border-top: 2px solid {c['color']};">
  <div class="mi-card-kw">{c['kw']}</div>
  <div class="mi-card-vd {c['verdict_cls']}">{c['verdict']}</div>
  <div class="mi-card-rsn">{c['reason']}</div>
  <div class="mi-stat-row">{stats_html}</div>
</div>""")
    return f'<div class="mi-cards">{"".join(items)}</div>'


def alert_html(level: str, icon: str, headline: str, detail: str, time_str: str) -> str:
    cls = {"critical": "al-cr", "warning": "al-wn", "info": "al-in"}.get(level, "al-in")
    return f"""
<div class="mi-alert {cls}">
  <div style="font-size:12px;flex-shrink:0">{icon}</div>
  <div style="flex:1">
    <div class="mi-alert-h">{headline}</div>
    <div class="mi-alert-d">{detail}</div>
  </div>
  <div class="mi-alert-t">{time_str}</div>
</div>"""


def community_html(color: str, name: str, tags: str, count: str, delta: str, delta_color: str) -> str:
    return f"""
<div class="mi-ci">
  <div class="mi-ci-dot" style="background:{color}"></div>
  <div style="flex:1">
    <div class="mi-ci-name">{name}</div>
    <div class="mi-ci-tags">{tags}</div>
  </div>
  <div style="text-align:right">
    <div class="mi-ci-count">{count}</div>
    <div class="mi-ci-delta" style="color:{delta_color}">{delta}</div>
  </div>
</div>"""


def corr_card_html(pair: str, pair_color: str, r_val: float, bar_color: str,
                   desc: str, lag_text: str, lag_color: str) -> str:
    bar_pct = int(abs(r_val) * 100)
    return f"""
<div class="mi-corr-card">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px">
    <div class="mi-corr-pair" style="color:{pair_color}">{pair}</div>
    <div class="mi-corr-r" style="color:{bar_color}">{r_val:.2f}</div>
  </div>
  <div class="mi-corr-bar-bg"><div class="mi-corr-bar" style="width:{bar_pct}%;background:{bar_color}"></div></div>
  <div class="mi-corr-desc">{desc}</div>
  <div class="mi-corr-lag" style="color:{lag_color}">{lag_text}</div>
</div>"""
