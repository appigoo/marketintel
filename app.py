# app.py — MarketSignal: Social Media Trading Signal System
# Real data: Stocktwits + Reddit + yFinance + Groq AI
from __future__ import annotations
import sys, os
_DIR = os.path.dirname(os.path.abspath(__file__))
if _DIR not in sys.path: sys.path.insert(0, _DIR)

import streamlit as st
st.set_page_config(
    page_title="MarketSignal — 社媒交易信號",
    page_icon="📡", layout="wide",
    initial_sidebar_state="collapsed",
)

from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from data.fetcher import (
    fetch_stocktwits_stream, fetch_stocktwits_history,
    fetch_reddit_posts, fetch_price_realtime,
    fetch_intraday, fetch_daily_history,
    fetch_trends_7d, build_hourly_sentiment, compute_sentiment_momentum,
)
from data.signals import (
    signal_sentiment_momentum, signal_volume_anomaly,
    signal_divergence, compute_backtest_winrate,
    compute_composite_signal,
    SIGNAL_BUY, SIGNAL_SELL, SIGNAL_HOLD, SIGNAL_WATCH,
)
from data.groq_ai import generate_signal_narrative
from components.charts import (
    chart_sentiment_timeseries, chart_price_sentiment_overlay,
    chart_volume_bars, chart_signal_gauge,
    chart_backtest_returns, chart_reddit_sentiment,
    chart_price_candle,
)

# ── CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@300;400;500&family=Bebas+Neue&family=Noto+Sans+TC:wght@400;500;700&display=swap');
:root{
  --bg:#07080a;--ink:#0e1015;--card:#12151b;--line:#1c2030;
  --dim:#4a5270;--body:#8892aa;--bright:#d4daf0;--white:#eef2ff;
  --bull:#00e676;--bear:#ff3d57;--warn:#ffab00;--ice:#00b8ff;--lav:#b388ff;
}
*,*::before,*::after{box-sizing:border-box}
html,body,[class*="css"]{background:var(--bg)!important;color:var(--body)!important;font-family:'Noto Sans TC',sans-serif!important}
#MainMenu,footer,header{visibility:hidden!important}
.block-container{padding:0!important;max-width:100%!important}
section[data-testid="stSidebar"]{display:none!important}
.stDeployButton{display:none!important}
div[data-testid="stToolbar"]{display:none!important}
::-webkit-scrollbar{width:3px;height:3px}
::-webkit-scrollbar-thumb{background:#2e3650;border-radius:2px}

/* TOPBAR */
.mi-topbar{display:flex;align-items:center;justify-content:space-between;
  padding:0 24px;height:48px;background:var(--ink);border-bottom:1px solid var(--line);
  position:sticky;top:0;z-index:200}
.mi-brand{font-family:'Bebas Neue',sans-serif;font-size:20px;letter-spacing:.08em;color:var(--white)}
.mi-brand span{color:var(--ice)}
.mi-tr{display:flex;align-items:center;gap:14px;font-family:'DM Mono',monospace;font-size:10px}
.mi-live{display:flex;align-items:center;gap:5px;color:var(--bull)}
.mi-dot{width:6px;height:6px;border-radius:50%;background:var(--bull);
  animation:pa 1.4s ease-in-out infinite}
@keyframes pa{0%,100%{opacity:1}50%{opacity:.2}}
.mi-clock{color:var(--ice);font-family:'DM Mono',monospace}
.mi-src{padding:2px 7px;border-radius:20px;font-size:9px;letter-spacing:.08em;
  border:1px solid var(--bull);color:var(--bull)}

/* SIGNAL HERO */
.sig-hero{padding:20px 24px 16px;border-bottom:1px solid var(--line);position:relative;overflow:hidden}
.sig-hero::before{content:'';position:absolute;inset:0;pointer-events:none;
  background:radial-gradient(ellipse 40% 100% at 2% 50%,var(--glow-color,#00e67608) 0%,transparent 70%)}
.sig-eye{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.2em;
  color:var(--lav);margin-bottom:6px;display:flex;align-items:center;gap:8px}
.sig-eye::after{content:'';flex:1;height:1px;background:var(--line)}
.sig-main{display:flex;align-items:flex-start;gap:24px;margin-bottom:14px;flex-wrap:wrap}
.sig-badge{font-family:'Bebas Neue',sans-serif;font-size:52px;line-height:1;letter-spacing:.06em;
  padding:8px 20px;border-radius:6px;border:2px solid;white-space:nowrap}
.sig-right{flex:1;min-width:240px}
.sig-ticker{font-family:'DM Mono',monospace;font-size:11px;color:var(--dim);margin-bottom:4px}
.sig-price{font-family:'Bebas Neue',sans-serif;font-size:32px;letter-spacing:.04em;color:var(--white);line-height:1}
.sig-chg{font-family:'DM Mono',monospace;font-size:13px;margin-left:8px}
.sig-one-liner{font-size:15px;color:var(--bright);font-weight:700;margin:8px 0 4px}
.sig-confidence{font-family:'DM Mono',monospace;font-size:10px;color:var(--dim);margin-bottom:8px}

/* PRICE TARGETS */
.sig-targets{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.sig-target{padding:6px 14px;border-radius:4px;font-family:'DM Mono',monospace;
  font-size:11px;border:1px solid;text-align:center}
.st-entry{color:var(--ice);border-color:var(--ice);background:rgba(0,184,255,.08)}
.st-stop{color:var(--bear);border-color:var(--bear);background:rgba(255,61,87,.08)}
.st-target{color:var(--bull);border-color:var(--bull);background:rgba(0,230,118,.08)}
.st-rr{color:var(--warn);border-color:var(--warn);background:rgba(255,171,0,.08)}

/* SUB SIGNALS */
.sub-sigs{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.sub-sig{display:flex;align-items:center;gap:6px;padding:5px 12px;border-radius:4px;
  font-family:'DM Mono',monospace;font-size:10px;border:1px solid}
.ss-buy{color:var(--bull);border-color:var(--bull);background:rgba(0,230,118,.08)}
.ss-sell{color:var(--bear);border-color:var(--bear);background:rgba(255,61,87,.08)}
.ss-watch{color:var(--warn);border-color:var(--warn);background:rgba(255,171,0,.08)}
.ss-hold{color:var(--dim);border-color:var(--dim);background:rgba(74,82,112,.08)}

/* CARDS */
.mi-card{background:var(--card);border:1px solid var(--line);border-radius:5px;
  padding:14px 16px;margin-bottom:8px}
.mi-card-title{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.15em;
  color:var(--dim);text-transform:uppercase;margin-bottom:8px}
.mi-card-val{font-family:'Bebas Neue',sans-serif;font-size:28px;line-height:1}
.mi-card-sub{font-size:11px;color:var(--body);margin-top:3px}

/* AI BLOCK */
.ai-block{background:var(--card);border:1px solid var(--line);border-radius:5px;
  padding:14px 16px;margin-bottom:8px;
  background:linear-gradient(135deg,rgba(179,136,255,.04) 0%,transparent 60%)}
.ai-label{font-family:'DM Mono',monospace;font-size:8px;letter-spacing:.18em;
  color:var(--lav);margin-bottom:8px}
.ai-row{margin-bottom:8px;font-size:12px;color:var(--body);line-height:1.6}
.ai-row strong{color:var(--bright)}

/* MESSAGE FEED */
.msg-item{padding:9px 12px;border-left:3px solid;border-radius:0 4px 4px 0;
  margin-bottom:5px;font-size:11px;line-height:1.5;background:var(--card)}
.msg-bull{border-left-color:var(--bull)}
.msg-bear{border-left-color:var(--bear)}
.msg-neut{border-left-color:var(--dim)}
.msg-user{font-family:'DM Mono',monospace;font-size:9px;color:var(--dim);margin-bottom:3px}
.msg-body{color:var(--body)}
.msg-meta{font-family:'DM Mono',monospace;font-size:9px;color:var(--dim);margin-top:3px}

/* REDDIT */
.rd-item{padding:8px 12px;background:var(--card);border:1px solid var(--line);
  border-radius:4px;margin-bottom:5px;font-size:11px}
.rd-title{color:var(--bright);font-weight:500;margin-bottom:3px}
.rd-meta{font-family:'DM Mono',monospace;font-size:9px;color:var(--dim)}

/* SECTION HEADER */
.sec-hdr{display:flex;align-items:center;justify-content:space-between;
  padding:10px 16px;border-bottom:1px solid var(--line);background:var(--ink)}
.sec-title{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.18em;
  color:var(--dim);text-transform:uppercase}
.sec-note{font-size:10px;color:var(--body)}

/* OVERRIDE STREAMLIT */
.stButton>button{background:transparent!important;color:var(--ice)!important;
  border:1px solid var(--ice)!important;border-radius:4px!important;
  font-family:'DM Mono',monospace!important;font-size:11px!important;
  letter-spacing:.1em!important;transition:all .2s!important}
.stButton>button:hover{background:rgba(0,184,255,.08)!important}
div[data-testid="stTextInput"] input{background:var(--card)!important;
  color:var(--bright)!important;border:1px solid var(--line)!important;
  border-radius:4px!important;font-family:'DM Mono',monospace!important}
div[data-testid="stSelectbox"] *{background:var(--card)!important;color:var(--bright)!important}
div[data-testid="stTabs"] button{font-family:'DM Mono',monospace!important;
  font-size:10px!important;letter-spacing:.1em!important;
  color:var(--dim)!important;background:transparent!important;
  border:none!important;border-bottom:2px solid transparent!important}
div[data-testid="stTabs"] button[aria-selected="true"]{color:var(--ice)!important;
  border-bottom-color:var(--ice)!important}
div[data-testid="stTabs"]{border-bottom:1px solid var(--line)!important}
div[data-testid="stSpinner"] p{color:var(--ice)!important;font-family:'DM Mono',monospace!important}
</style>
""", unsafe_allow_html=True)

# ── CLOCK ────────────────────────────────────────────────────────
try:
    from zoneinfo import ZoneInfo
    now_hkt = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Hong_Kong"))
except Exception:
    now_hkt = datetime.now(timezone.utc) + timedelta(hours=8)
time_str = now_hkt.strftime("%H:%M:%S")

# ── TOPBAR ───────────────────────────────────────────────────────
st.markdown(f"""
<div class="mi-topbar">
  <div class="mi-brand">MARKET<span>SIGNAL</span></div>
  <div class="mi-tr">
    <span class="mi-src">STOCKTWITS</span>
    <span class="mi-src">REDDIT</span>
    <span class="mi-src">YFINANCE</span>
    <div class="mi-live"><div class="mi-dot"></div>LIVE</div>
    <div class="mi-clock">{time_str} HKT</div>
  </div>
</div>""", unsafe_allow_html=True)

# ── INPUT BAR ────────────────────────────────────────────────────
col_t, col_btn = st.columns([5, 1])
with col_t:
    ticker_input = st.text_input("股票代碼", value="TSLA",
                                  placeholder="TSLA / NVDA / AAPL",
                                  label_visibility="collapsed")
with col_btn:
    refresh = st.button("▶ 掃描", use_container_width=True)

ticker = ticker_input.strip().upper() or "TSLA"
# Stocktwits uses same ticker symbol for most US stocks
st_symbol = ticker

st.markdown('<hr style="border:none;border-top:1px solid #1c2030;margin:0">', unsafe_allow_html=True)

# ── DATA LOADING ─────────────────────────────────────────────────
with st.spinner(f"⚡ 正在抓取 {ticker} 真實市場數據..."):

    # Real-time price
    price_info  = fetch_price_realtime(ticker)

    # Stocktwits stream (real messages)
    st_stream   = fetch_stocktwits_stream(st_symbol, limit=30)
    st_history  = fetch_stocktwits_history(st_symbol, pages=6)

    # All messages combined
    all_msgs = st_stream.get("messages", []) + st_history
    # Deduplicate by (username, body)
    seen = set()
    unique_msgs = []
    for m in all_msgs:
        key = (m.get("username",""), m.get("body","")[:40])
        if key not in seen:
            seen.add(key)
            unique_msgs.append(m)

    # Reddit
    reddit_result = fetch_reddit_posts(ticker, limit=25)
    reddit_posts  = reddit_result.get("posts", [])

    # Price history
    intraday_df   = fetch_intraday(ticker, period="5d", interval="15m")
    daily_df      = fetch_daily_history(ticker, period="1mo")

    # Build hourly sentiment timeseries
    hourly_df     = build_hourly_sentiment(unique_msgs, hours_back=48)
    momentum_data = compute_sentiment_momentum(hourly_df)

    # ── COMPUTE SIGNALS ──────────────────────────────────────────
    sig_mom = signal_sentiment_momentum(hourly_df)
    sig_vol = signal_volume_anomaly(hourly_df)
    sig_div = signal_divergence(hourly_df, intraday_df)
    backtest = compute_backtest_winrate(daily_df, threshold_bull=65, hold_days=2)

    # Composite signal
    composite = compute_composite_signal(
        sig_mom, sig_vol, sig_div, backtest, price_info
    )

    # Top messages for AI context
    top_msgs = tuple(
        (m["body"][:100], m["sentiment"])
        for m in sorted(unique_msgs, key=lambda x: x.get("likes",0), reverse=True)[:5]
    )

    # AI narrative
    ai_narrative = generate_signal_narrative(
        ticker, composite, sig_mom, sig_vol, sig_div, backtest, top_msgs
    )

# ── DATA SOURCE STATUS ───────────────────────────────────────────
data_ok = st_stream.get("ok", False)
msg_count = len(unique_msgs)
data_status = f"✅ {msg_count} 條真實 Stocktwits 訊息" if data_ok and msg_count > 0 \
              else f"⚠️ Stocktwits 數據有限（{msg_count} 條）—— 結果僅供參考"
st.markdown(f'<div style="padding:4px 24px;font-family:DM Mono;font-size:9px;'
            f'color:{"#00e676" if data_ok and msg_count>5 else "#ffab00"};'
            f'background:#0e1015;border-bottom:1px solid #1c2030">{data_status}</div>',
            unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# SIGNAL HERO — The thing users see first
# ════════════════════════════════════════════════════════════════
signal     = composite.get("signal", SIGNAL_HOLD)
sig_color  = composite.get("signal_color", "#4a5270")
sig_emoji  = composite.get("signal_emoji", "⚪")
price      = price_info.get("price", 0)
change_pct = price_info.get("change_pct", 0)
conf       = composite.get("confidence", 50)
entry      = composite.get("entry")
stop_loss  = composite.get("stop")
target     = composite.get("target")
rr         = composite.get("rr_ratio")
raw_score  = composite.get("raw_score", 0)
one_liner  = ai_narrative.get("one_liner", "")
backtest_txt = composite.get("backtest_txt","")
chg_color  = "#00e676" if change_pct >= 0 else "#ff3d57"
chg_sign   = "+" if change_pct >= 0 else ""

glow_map = {SIGNAL_BUY:"#00e67608", SIGNAL_SELL:"#ff3d5708",
            SIGNAL_WATCH:"#ffab0008", SIGNAL_HOLD:"#4a527008"}

# Signal badge HTML
badge_html = f"""
<div class="sig-hero" style="--glow-color:{glow_map.get(signal,'#00e67608')}">
  <div class="sig-eye">AI 交易信號 · 真實社媒數據 · {ticker}</div>
  <div class="sig-main">
    <div class="sig-badge" style="color:{sig_color};border-color:{sig_color};
         background:rgba({','.join(str(int(sig_color.lstrip('#')[i:i+2],16)) for i in (0,2,4))},.10)">
      {sig_emoji} {signal}
    </div>
    <div class="sig-right">
      <div class="sig-ticker">{ticker} · STOCKTWITS + REDDIT + YFINANCE</div>
      <div>
        <span class="sig-price">${price:,.2f}</span>
        <span class="sig-chg" style="color:{chg_color}">{chg_sign}{change_pct:.2f}%</span>
      </div>
      <div class="sig-one-liner">{one_liner}</div>
      <div class="sig-confidence">置信度 {conf}%
        {' · ' + backtest_txt if backtest_txt else ''}
      </div>
    </div>
  </div>"""

# Price targets (only for BUY/SELL)
if entry and stop_loss and target:
    badge_html += f"""
  <div class="sig-targets">
    <div class="sig-target st-entry">入場<br>${entry:,.2f}</div>
    <div class="sig-target st-stop">止損<br>${stop_loss:,.2f}</div>
    <div class="sig-target st-target">目標<br>${target:,.2f}</div>
    {"<div class='sig-target st-rr'>R:R<br>1:" + str(rr) + "</div>" if rr else ""}
  </div>"""

# Sub-signal pills
def _pill(sig_dict):
    s = sig_dict.get("signal", SIGNAL_HOLD)
    n = sig_dict.get("name","")
    st_ = sig_dict.get("strength",0)
    cls = {"BUY":"ss-buy","SELL":"ss-sell","WATCH":"ss-watch"}.get(s,"ss-hold")
    icon = {"BUY":"🟢","SELL":"🔴","WATCH":"🟡","HOLD":"⚪"}.get(s,"⚪")
    return f'<span class="sub-sig {cls}">{icon} {n} {st_}</span>'

badge_html += f"""
  <div class="sub-sigs">
    {_pill(sig_mom)}{_pill(sig_vol)}{_pill(sig_div)}
  </div>
</div>"""

st.markdown(badge_html, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4 = st.tabs(["📊 信號詳情", "📈 價格 & 情緒", "💬 真實討論", "🔁 30天回測"])

# ─────────────────────────────────────────────────────────────────
# TAB 1: SIGNAL DETAIL
# ─────────────────────────────────────────────────────────────────
with tab1:
    left, right = st.columns([2, 1], gap="small")

    with left:
        # Signal gauge
        st.markdown('<div class="sec-hdr"><div class="sec-title">綜合信號強度</div>'
                    '<div class="sec-note">-100=強烈做空  0=中性  +100=強烈做多</div></div>',
                    unsafe_allow_html=True)
        st.plotly_chart(chart_signal_gauge(raw_score, signal, height=180),
                        use_container_width=True, config={"displayModeBar":False})

        # Three sub-signals breakdown
        st.markdown('<div class="sec-hdr"><div class="sec-title">三層信號分解</div></div>',
                    unsafe_allow_html=True)
        for sig_d in [sig_mom, sig_vol, sig_div]:
            s      = sig_d.get("signal", SIGNAL_HOLD)
            color  = {"BUY":("#00e676","rgba(0,230,118,.08)"),
                      "SELL":("#ff3d57","rgba(255,61,87,.08)"),
                      "WATCH":("#ffab00","rgba(255,171,0,.08)"),
                      "HOLD":("#4a5270","rgba(74,82,112,.08)")}.get(s, ("#4a5270","rgba(0,0,0,0)"))
            st.markdown(f"""
<div class="mi-card" style="border-left:3px solid {color[0]};background:{color[1]};margin-bottom:8px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px">
    <div class="mi-card-title" style="margin:0">{sig_d.get("name","")}</div>
    <div style="font-family:'DM Mono',monospace;font-size:11px;color:{color[0]};font-weight:600">
      {s} · 強度 {sig_d.get("strength",0)}
    </div>
  </div>
  <div style="font-size:12px;color:#d4daf0;line-height:1.55">{sig_d.get("reason","")}</div>
</div>""", unsafe_allow_html=True)

    with right:
        # AI Narrative
        st.markdown(f"""
<div class="ai-block">
  <div class="ai-label">⬡ GROQ AI 信號解讀</div>
  <div class="ai-row"><strong>為什麼出現這個信號：</strong><br>{ai_narrative.get("why","")}</div>
  <div class="ai-row"><strong>⚠ 主要風險：</strong><br>{ai_narrative.get("risk","")}</div>
  <div class="ai-row"><strong>👁 需要監察：</strong><br>{ai_narrative.get("watch","")}</div>
</div>""", unsafe_allow_html=True)

        # Key metrics
        bull_cur  = momentum_data.get("current_bull", 50)
        bull_avg  = momentum_data.get("avg_bull", 50)
        vol_vel   = momentum_data.get("msg_velocity", 0)
        cur_vol   = momentum_data.get("current_vol", 0)

        metrics = [
            ("當前 Bull%",  f"{bull_cur:.1f}%",
             f"vs 24h均值 {bull_avg:.1f}%",
             "#00e676" if bull_cur > 60 else "#ff3d57" if bull_cur < 40 else "#8892aa"),
            ("訊息量速度", f"{'+' if vol_vel>=0 else ''}{vol_vel:.0f}%",
             f"本小時 {cur_vol} 條",
             "#ffab00" if abs(vol_vel)>50 else "#8892aa"),
            ("Z-Score",    f"{sig_vol.get('z_score',0):.2f}",
             "超過2.5=異常",
             "#ff3d57" if sig_vol.get('z_score',0)>2.5 else "#00e676" if sig_vol.get('z_score',0)>1 else "#8892aa"),
            ("數據來源",   f"{msg_count}條",
             "Stocktwits真實訊息",
             "#00b8ff"),
        ]
        for label, val, sub, color in metrics:
            st.markdown(f"""
<div class="mi-card">
  <div class="mi-card-title">{label}</div>
  <div class="mi-card-val" style="color:{color}">{val}</div>
  <div class="mi-card-sub">{sub}</div>
</div>""", unsafe_allow_html=True)

        # Win rate from backtest
        wr = backtest.get("win_rate")
        if wr is not None:
            wr_color = "#00e676" if wr >= 60 else "#ff3d57" if wr < 45 else "#ffab00"
            st.markdown(f"""
<div class="mi-card">
  <div class="mi-card-title">30天歷史勝率</div>
  <div class="mi-card-val" style="color:{wr_color}">{wr}%</div>
  <div class="mi-card-sub">樣本 {backtest.get("sample_size",0)} 次
    · 均回報 {backtest.get("avg_return",0):+.1f}%</div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# TAB 2: PRICE & SENTIMENT
# ─────────────────────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="sec-hdr"><div class="sec-title">Bull% 情緒時序（真實Stocktwits）</div>'
                '<div class="sec-note">每小時看漲/看跌比例</div></div>', unsafe_allow_html=True)
    st.plotly_chart(chart_sentiment_timeseries(hourly_df, height=220),
                    use_container_width=True, config={"displayModeBar":False})

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec-hdr"><div class="sec-title">訊息量（異常偵測）</div></div>',
                    unsafe_allow_html=True)
        st.plotly_chart(chart_volume_bars(hourly_df, height=160),
                        use_container_width=True, config={"displayModeBar":False})
    with c2:
        st.markdown('<div class="sec-hdr"><div class="sec-title">Reddit 情緒分佈</div></div>',
                    unsafe_allow_html=True)
        st.plotly_chart(chart_reddit_sentiment(reddit_posts, height=160),
                        use_container_width=True, config={"displayModeBar":False})

    st.markdown(f'<div class="sec-hdr"><div class="sec-title">{ticker} 股價走勢（15分鐘）</div>'
                f'<div class="sec-note">intraday · 5天</div></div>', unsafe_allow_html=True)
    st.plotly_chart(chart_price_candle(intraday_df, ticker, height=220),
                    use_container_width=True, config={"displayModeBar":False})

    st.markdown(f'<div class="sec-hdr"><div class="sec-title">股價 × Bull% 疊加</div>'
                f'<div class="sec-note">驗證社媒情緒與股價的相關性</div></div>', unsafe_allow_html=True)
    st.plotly_chart(chart_price_sentiment_overlay(intraday_df, hourly_df, ticker, height=260),
                    use_container_width=True, config={"displayModeBar":False})

# ─────────────────────────────────────────────────────────────────
# TAB 3: REAL MESSAGES
# ─────────────────────────────────────────────────────────────────
with tab3:
    c_st, c_rd = st.columns([3, 2])

    with c_st:
        st.markdown(f'<div class="sec-hdr"><div class="sec-title">Stocktwits 真實訊息</div>'
                    f'<div class="sec-note">{msg_count} 條 · 按讚數排序</div></div>',
                    unsafe_allow_html=True)
        if unique_msgs:
            top_by_likes = sorted(unique_msgs, key=lambda x: x.get("likes",0), reverse=True)[:20]
            for m in top_by_likes:
                sent  = m.get("sentiment","neutral")
                cls   = {"bullish":"msg-bull","bearish":"msg-bear"}.get(sent,"msg-neut")
                icon  = {"bullish":"🐂","bearish":"🐻"}.get(sent,"—")
                body  = m.get("body","")[:160]
                user  = m.get("username","")
                likes = m.get("likes",0)
                ts    = m.get("created_at")
                ts_str = ts.strftime("%m/%d %H:%M") if ts else ""
                st.markdown(f"""
<div class="msg-item {cls}">
  <div class="msg-user">{icon} @{user} · {ts_str}</div>
  <div class="msg-body">{body}</div>
  <div class="msg-meta">❤ {likes}</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="mi-card"><div class="mi-card-sub">Stocktwits 數據暫時無法獲取</div></div>',
                        unsafe_allow_html=True)

    with c_rd:
        st.markdown(f'<div class="sec-hdr"><div class="sec-title">Reddit 討論</div>'
                    f'<div class="sec-note">{len(reddit_posts)} 帖 · 熱門優先</div></div>',
                    unsafe_allow_html=True)
        if reddit_posts:
            for p in sorted(reddit_posts, key=lambda x: x.get("score",0), reverse=True)[:12]:
                sent  = p.get("sentiment","neutral")
                icon  = {"bullish":"🐂","bearish":"🐻"}.get(sent,"—")
                score = p.get("score",0)
                cmts  = p.get("comments",0)
                sub   = p.get("subreddit","")
                url   = p.get("url","")
                title = p.get("title","")[:100]
                st.markdown(f"""
<div class="rd-item">
  <div class="rd-title">{icon} {title}</div>
  <div class="rd-meta">r/{sub} · ▲{score} · 💬{cmts}
    {' · <a href="' + url + '" target="_blank" style="color:#00b8ff">查看</a>' if url else ''}
  </div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="mi-card"><div class="mi-card-sub">Reddit 數據暫時無法獲取</div></div>',
                        unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# TAB 4: BACKTEST
# ─────────────────────────────────────────────────────────────────
with tab4:
    wr = backtest.get("win_rate")
    n  = backtest.get("sample_size", 0)
    ar = backtest.get("avg_return")

    if wr is not None and n >= 3:
        wr_color = "#00e676" if wr>=60 else "#ff3d57" if wr<45 else "#ffab00"
        st.markdown(f"""
<div class="sig-hero" style="--glow-color:{'#00e67608' if wr>=60 else '#ff3d5708'}">
  <div class="sig-eye">30天歷史回測結論</div>
  <div class="sig-main">
    <div class="sig-badge" style="color:{wr_color};border-color:{wr_color};
         background:rgba({','.join(str(int(wr_color.lstrip('#')[i:i+2],16)) for i in (0,2,4))},.10)">
      勝率 {wr:.0f}%
    </div>
    <div class="sig-right">
      <div class="sig-ticker">基於 {n} 次相似情況 · 持倉 {backtest.get("hold_days",2)} 天</div>
      <div class="sig-one-liner">
        {'歷史上社媒看漲信號後，股價上漲機率高於隨機' if wr>=55 else '信號歷史勝率偏低，謹慎操作'}
      </div>
      <div class="sig-confidence">平均回報 {ar:+.2f}% per trade</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div class="mi-card">
  <div class="mi-card-title">回測數據</div>
  <div class="mi-card-sub">歷史數據不足（需要 30 天以上），回測結果暫不可用</div>
</div>""", unsafe_allow_html=True)

    st.markdown(f'<div class="sec-hdr"><div class="sec-title">{ticker} 30天每日回報分佈</div>'
                f'<div class="sec-note">綠點=情緒偏多日 · 紅點=情緒偏空日</div></div>',
                unsafe_allow_html=True)
    st.plotly_chart(chart_backtest_returns(daily_df, hold_days=2, height=240),
                    use_container_width=True, config={"displayModeBar":False})

    # Stats table
    if not daily_df.empty and len(daily_df) >= 5:
        df_stats = daily_df.copy()
        df_stats["日回報%"] = df_stats["Close"].pct_change() * 100
        up_days   = (df_stats["日回報%"] > 0).sum()
        down_days = (df_stats["日回報%"] < 0).sum()
        max_up    = df_stats["日回報%"].max()
        max_down  = df_stats["日回報%"].min()
        avg_ret   = df_stats["日回報%"].mean()

        st.markdown(f"""
<div class="mi-card">
  <div class="mi-card-title">{ticker} 30天統計</div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:8px">
    <div style="text-align:center">
      <div style="font-family:'Bebas Neue';font-size:24px;color:#00e676">{up_days}</div>
      <div style="font-size:10px;color:#4a5270">上漲日</div>
    </div>
    <div style="text-align:center">
      <div style="font-family:'Bebas Neue';font-size:24px;color:#ff3d57">{down_days}</div>
      <div style="font-size:10px;color:#4a5270">下跌日</div>
    </div>
    <div style="text-align:center">
      <div style="font-family:'Bebas Neue';font-size:24px;color:#{'00e676' if avg_ret>=0 else 'ff3d57'}">{avg_ret:+.2f}%</div>
      <div style="font-size:10px;color:#4a5270">平均日回報</div>
    </div>
    <div style="text-align:center">
      <div style="font-family:'DM Mono';font-size:14px;color:#00e676">{max_up:+.2f}%</div>
      <div style="font-size:10px;color:#4a5270">最大單日漲</div>
    </div>
    <div style="text-align:center">
      <div style="font-family:'DM Mono';font-size:14px;color:#ff3d57">{max_down:+.2f}%</div>
      <div style="font-size:10px;color:#4a5270">最大單日跌</div>
    </div>
    <div style="text-align:center">
      <div style="font-family:'DM Mono';font-size:14px;color:#ffab00">{wr or '—'}%</div>
      <div style="font-size:10px;color:#4a5270">信號勝率</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

# ── FOOTER ───────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:12px 24px;border-top:1px solid #1c2030;display:flex;justify-content:space-between;
  align-items:center;font-family:'DM Mono',monospace;font-size:9px;color:#4a5270;margin-top:12px">
  <div>⚠ 學術研究用途 · 非投資建議 · 數據源：Stocktwits / Reddit / yFinance</div>
  <div>更新：{time_str} HKT · Groq LLaMA 3.3</div>
</div>""", unsafe_allow_html=True)
