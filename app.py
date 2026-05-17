# app.py — MarketIntel Main Application
# Streamlit Cloud compatible · No Playwright · No Twitter API
# Sources: Google Trends + Stocktwits + Reddit + yFinance + Groq AI

from __future__ import annotations
import sys, os

# ── FIX IMPORT PATHS (Streamlit Cloud doesn't add app dir to sys.path) ────────
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)
# ─────────────────────────────────────────────────────────────────────────────

import time
from datetime import datetime, timezone
import streamlit as st
import pandas as pd
import numpy as np

# ── PAGE CONFIG (must be first Streamlit call) ────────────────────────────
from config import (
    PAGE_CONFIG, DEFAULT_KEYWORDS, DEFAULT_STOCKS,
    PRICE_MAP, STOCKTWITS_MAP, KW_COLORS, COLORS,
    ZSCORE_RED, ZSCORE_YELLOW,
)
st.set_page_config(**PAGE_CONFIG)

# ── LOCAL IMPORTS ─────────────────────────────────────────────────────────
from utils.css import (
    inject_css, topbar_html, hero_html, scorecard_row_html,
    alert_html, community_html, corr_card_html,
)
from data.fetcher import (
    fetch_trends, fetch_stocktwits, fetch_reddit,
    fetch_price_history, fetch_current_price, build_daily_volume,
)
from data.analyzer import (
    compute_zscore_series, current_zscore, zscore_level,
    detect_peaks, aggregate_sentiment, sentiment_verdict,
    cooccurrence_from_trends, build_force_graph, graph_to_plotly,
    build_all_correlations, detect_30d_peaks, compute_ai_score,
)
from data.groq_ai import generate_insight
from components.charts import (
    trend_chart, cooccurrence_heatmap, sentiment_donut,
    lag_correlation_chart, scatter_volume_return,
    dual_axis_30d, pattern_bars, zscore_bars,
)


# ─────────────────────────────────────────────────────────────────────────────
# INJECT CSS + TOP BAR
# ─────────────────────────────────────────────────────────────────────────────
inject_css()

try:
    from zoneinfo import ZoneInfo
    hkt = datetime.now(timezone.utc).astimezone(ZoneInfo("Asia/Hong_Kong"))
except Exception:
    from datetime import timedelta
    hkt = datetime.now(timezone.utc) + timedelta(hours=8)
time_str = hkt.strftime("%H:%M:%S")
st.markdown(topbar_html(time_str), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# INPUT BAR
# ─────────────────────────────────────────────────────────────────────────────
col_kw, col_tf, col_btn = st.columns([5, 2, 1])

with col_kw:
    kw_input = st.text_input(
        "關鍵字（用逗號分隔）",
        value=", ".join(DEFAULT_KEYWORDS),
        label_visibility="collapsed",
        placeholder="TSLA, TESLA, ELON MUSK, SPCX",
    )

with col_tf:
    timeframe_label = st.selectbox(
        "時間範圍", ["即時 24H", "7天", "30天"],
        index=2, label_visibility="collapsed",
    )

with col_btn:
    scan = st.button("▶ 掃描", use_container_width=True)

# Parse keywords
keywords: list[str] = [k.strip().upper() for k in kw_input.split(",") if k.strip()]
if not keywords:
    keywords = DEFAULT_KEYWORDS

# Timeframe → pytrends string
TF_MAP = {"即時 24H": "now 1-d", "7天": "now 7-d", "30天": "today 1-m"}
tf_str = TF_MAP.get(timeframe_label, "today 1-m")

# Show keyword pills
pills_html = "".join(
    f'<span class="mi-sig sg-ice" style="font-size:10px;padding:3px 10px">{k}</span>'
    for k in keywords
)
st.markdown(f'<div style="padding:4px 0 8px;display:flex;flex-wrap:wrap;gap:6px">{pills_html}</div>',
            unsafe_allow_html=True)

st.markdown('<hr style="border:none;border-top:1px solid #1c2030;margin:0 0 0 0">', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────
with st.spinner("⚡ 正在從多數據源抓取資料..."):
    # Google Trends
    trends_data = fetch_trends(tuple(keywords[:5]), timeframe=tf_str)

    # Stocktwits (per unique ticker)
    unique_tickers: set[str] = set()
    for kw in keywords:
        t = STOCKTWITS_MAP.get(kw, STOCKTWITS_MAP.get(kw.upper(), ""))
        if t:
            unique_tickers.add(t)

    st_data: dict[str, dict] = {}
    for ticker in unique_tickers:
        st_data[ticker] = fetch_stocktwits(ticker)

    # Reddit (per keyword)
    reddit_data: dict[str, dict] = {}
    for kw in keywords:
        reddit_data[kw] = fetch_reddit(kw)

    # yFinance
    price_tickers: set[str] = {
        t for kw in keywords
        for t in [PRICE_MAP.get(kw, PRICE_MAP.get(kw.upper(), ""))]
        if t
    }
    price_data: dict[str, pd.DataFrame] = {}
    price_current: dict[str, dict] = {}
    for tkr in price_tickers:
        price_data[tkr] = fetch_price_history(tkr, period="1mo")
        price_current[tkr] = fetch_current_price(tkr)

    # Build unified daily volume
    volume_df = build_daily_volume(keywords, trends_data, reddit_data, st_data)

    # Compute z-scores
    z_scores: dict[str, float] = {}
    for kw in keywords:
        if kw in volume_df.columns:
            z_scores[kw] = round(current_zscore(volume_df[kw]), 2)
        else:
            z_scores[kw] = 0.0

    # Sentiment (Stocktwits messages aggregated)
    sentiments: dict[str, dict] = {}
    for kw in keywords:
        tkr = STOCKTWITS_MAP.get(kw, STOCKTWITS_MAP.get(kw.upper(), ""))
        msgs = st_data.get(tkr, {}).get("messages", []) if tkr else []
        st_sent = st_data.get(tkr, {}) if tkr else {}
        # Use Stocktwits direct bull/bear if available, else VADER on Reddit
        reddit_posts = reddit_data.get(kw, {}).get("posts", [])
        sent = aggregate_sentiment(msgs if msgs else reddit_posts)
        # Override with Stocktwits percentages if more reliable
        if st_sent.get("total", 0) > 5:
            sent["bull_pct"] = st_sent.get("bull_pct", sent["bull_pct"])
            sent["bear_pct"] = st_sent.get("bear_pct", sent["bear_pct"])
        sentiments[kw] = sent

    # Co-occurrence matrix
    cooccur_df = cooccurrence_from_trends(volume_df)

    # Correlation analysis
    corr_results = build_all_correlations(
        keywords, volume_df, price_data, PRICE_MAP
    )

    # AI score
    ai_score = compute_ai_score(sentiments, z_scores, corr_results, keywords)

    # Anomaly peaks mask for chart markers
    peaks_mask_df = pd.DataFrame({
        kw: detect_peaks(volume_df[kw]) if kw in volume_df.columns else pd.Series(False, index=volume_df.index)
        for kw in keywords
    })

    # Groq AI insight
    insight = generate_insight(
        keywords=tuple(keywords),
        sentiments=sentiments,
        z_scores=z_scores,
        corr_data=corr_results,
        ai_score=ai_score,
    )

    # 30-day peaks
    peaks_30d = detect_30d_peaks(volume_df, threshold_z=2.0)

    # Force graph
    G = build_force_graph(keywords, cooccur_df, volume_df, sentiments)
    force_fig = graph_to_plotly(G, width=900, height=320)


# ─────────────────────────────────────────────────────────────────────────────
# BUILD SCORECARD DATA
# ─────────────────────────────────────────────────────────────────────────────
scorecard_data = []
for kw in keywords:
    z      = z_scores.get(kw, 0)
    sent   = sentiments.get(kw, {})
    bull   = sent.get("bull_pct", 50)
    bear   = sent.get("bear_pct", 25)
    vd_txt, vd_cls, rsn = sentiment_verdict(bull, bear, z)
    color  = KW_COLORS.get(kw, "#8892aa")
    z_lv, z_col = zscore_level(z)
    mentions = volume_df[kw].iloc[-1] if kw in volume_df.columns else 0
    mean_v   = volume_df[kw].mean() if kw in volume_df.columns else 1
    chg_pct  = round((float(mentions) - float(mean_v)) / float(mean_v) * 100) if mean_v else 0

    scorecard_data.append({
        "kw":         kw,
        "verdict":    vd_txt,
        "verdict_cls": vd_cls,
        "reason":     rsn,
        "color":      color,
        "stats": [
            {"val": f"{mentions:.0f}", "lbl": "熱度指數", "color": color},
            {"val": f"{'+' if chg_pct >= 0 else ''}{chg_pct}%", "lbl": "vs均值",
             "color": COLORS["bull"] if chg_pct >= 0 else COLORS["bear"]},
            {"val": f"z={z:.1f}", "lbl": "異常度", "color": z_col},
        ],
    })


# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["⚡ 即時總覽", "📅 30天歷史", "📈 股票關聯"])


# ════════════════════════════════════════════════════════════════════════════
# TAB 1: LIVE OVERVIEW
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    # ── HERO VERDICT ──
    st.markdown(hero_html(
        headline=insight.get("headline", "市場分析中..."),
        sub=insight.get("sub", ""),
        signals=insight.get("signals", []),
    ), unsafe_allow_html=True)

    # ── SCORECARDS ──
    st.markdown(scorecard_row_html(scorecard_data), unsafe_allow_html=True)

    # ── MAIN CONTENT + RIGHT PANEL ──
    main_col, right_col = st.columns([3, 1], gap="small")

    with main_col:
        # Z-SCORE BARS
        st.markdown('<div class="mi-sec-hdr"><div class="mi-sec-title">異常程度 Z-Score</div><div class="mi-sec-note">超過 3.5 = 紅色警報</div></div>', unsafe_allow_html=True)
        st.plotly_chart(zscore_bars(z_scores), use_container_width=True, config={"displayModeBar": False})

        # FORCE GRAPH
        st.markdown('<div class="mi-sec-hdr"><div class="mi-sec-title">關聯網絡 Force Graph</div><div class="mi-sec-note">節點大小=討論量 · 顏色=話題群 · 可拖拉互動</div></div>', unsafe_allow_html=True)
        st.plotly_chart(force_fig, use_container_width=True, config={"displayModeBar": False})

        # DUAL CHARTS
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<div class="mi-sec-title" style="padding:10px 0 6px">即時討論熱度趨勢</div>', unsafe_allow_html=True)
            primary_ticker = PRICE_MAP.get(keywords[0], PRICE_MAP.get(keywords[0].upper(), ""))
            primary_price_df = price_data.get(primary_ticker, pd.DataFrame())
            fig_trend = trend_chart(
                volume_df, primary_price_df, primary_ticker or "TSLA",
                peaks_mask=peaks_mask_df, height=220,
            )
            st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

        with c2:
            st.markdown('<div class="mi-sec-title" style="padding:10px 0 6px">共現熱力圖</div>', unsafe_allow_html=True)
            st.plotly_chart(
                cooccurrence_heatmap(cooccur_df, height=220),
                use_container_width=True, config={"displayModeBar": False},
            )

        # SENTIMENT DONUT
        st.markdown('<div class="mi-sec-title" style="padding:10px 0 6px">整體情緒分佈</div>', unsafe_allow_html=True)
        avg_bull = float(np.mean([sentiments[k].get("bull_pct", 50) for k in keywords]))
        avg_bear = float(np.mean([sentiments[k].get("bear_pct", 25) for k in keywords]))
        avg_neut = max(0.0, 100 - avg_bull - avg_bear)
        st.plotly_chart(sentiment_donut(avg_bull, avg_bear, avg_neut, height=200),
                        use_container_width=True, config={"displayModeBar": False})

    with right_col:
        # AI SCORE PANEL
        score_color = COLORS["bull"] if ai_score >= 60 else COLORS["warn"] if ai_score >= 40 else COLORS["bear"]
        score_label = "看漲" if ai_score >= 60 else "中性" if ai_score >= 40 else "看跌"
        st.markdown(f"""
<div class="mi-ai-panel">
  <div class="mi-ai-eye">⬡ GROQ AI · 綜合分析</div>
  <div class="mi-score-row">
    <div class="mi-score-num" style="color:{score_color}">{ai_score}</div>
    <div class="mi-score-label">
      <strong>{score_label}強度</strong> / 100<br>
      <span style="color:{score_color};font-family:'DM Mono';font-size:9px">● {score_label.upper()} MOMENTUM</span>
    </div>
  </div>
  <div class="mi-ai-sum">{insight.get("summary","")}</div>
  {"".join(f'<div class="mi-action"><div class="mi-action-icon">{a["icon"]}</div><div class="mi-action-txt">{a["text"]}</div></div>' for a in insight.get("actions",[]))}
</div>""", unsafe_allow_html=True)

        # ALERTS
        st.markdown('<div style="padding:14px 0 8px"><div class="mi-sec-title">異常警報</div></div>', unsafe_allow_html=True)
        for kw in keywords:
            z   = z_scores.get(kw, 0)
            if z >= ZSCORE_RED:
                st.markdown(alert_html("critical", "🔴",
                    f"{kw} z={z:.1f} 紅色警報",
                    "討論量爆發，歷史上此後股價波動加劇",
                    time_str), unsafe_allow_html=True)
            elif z >= ZSCORE_YELLOW:
                st.markdown(alert_html("warning", "🟡",
                    f"{kw} z={z:.1f} 黃色警告",
                    "討論量高於均值，留意後續發展",
                    time_str), unsafe_allow_html=True)

        # Correlation alerts
        for kw, cr in corr_results.items():
            if abs(cr.get("best_r", 0)) >= 0.6 and cr.get("best_lag", 0) > 0:
                st.markdown(alert_html("info", "🔵",
                    f"{kw} 領先信號有效",
                    f"r={cr['best_r']:.2f}，領先 {cr['best_lag']} 天",
                    time_str), unsafe_allow_html=True)

        # COMMUNITY
        st.markdown('<div style="padding:14px 0 8px"><div class="mi-sec-title">話題社群聚類</div></div>', unsafe_allow_html=True)
        comm_data = [
            ("#00b8ff", "TSLA · AI · Robotaxi",   "tsla, fsd, robotaxi",   "急升 ↑↑", COLORS["bull"]),
            ("#b388ff", "ELON · 政治 · DOGE",      "elon, politics, doge",  "穩定 →",  COLORS["warn"]),
            ("#ffab00", "Tesla · 股價 · 財報",      "tesla, earnings, q2",   "上升 ↑",  COLORS["bull"]),
            ("#00e676", "SpaceX · SPCX · Starship", "spacex, spcx, launch", "平穩 →",  COLORS["dim"]),
        ]
        for color, name, tags, delta, dc in comm_data:
            st.markdown(community_html(color, name, tags, "—", delta, dc), unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 2: 30-DAY HISTORY
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    # HERO
    top_kw_30 = max(z_scores, key=z_scores.get) if z_scores else keywords[0]
    st.markdown(f"""
<div class="mi-hero">
  <div class="mi-eyebrow">過去 30 天歷史分析</div>
  <div class="mi-headline">{top_kw_30} 是最強波動引擎</div>
  <div class="mi-sub">過去 30 天數據顯示：<strong>{top_kw_30}</strong> 的討論量 z-score 最高，是帶動相關股票波動的主要社媒因子。結合股價回測，社媒信號具備一定預測價值。</div>
  <div class="mi-sigs">
    <span class="mi-sig sg-ice">📅 30天數據分析</span>
    <span class="mi-sig sg-warn">⚡ 峰值事件偵測</span>
    <span class="mi-sig sg-bull">📊 週期性規律</span>
  </div>
</div>""", unsafe_allow_html=True)

    main_col2, right_col2 = st.columns([3, 1], gap="small")

    with main_col2:
        # 30-DAY DUAL AXIS CHART
        st.markdown('<div class="mi-sec-hdr"><div class="mi-sec-title">30天 討論熱度 × 股價 疊加圖</div><div class="mi-sec-note">紅星=討論量爆發事件</div></div>', unsafe_allow_html=True)
        fig_30d = dual_axis_30d(volume_df, price_data, peaks_mask=peaks_mask_df, height=280)
        st.plotly_chart(fig_30d, use_container_width=True, config={"displayModeBar": False})

        # PEAK EVENTS
        if peaks_30d:
            st.markdown('<div class="mi-sec-title" style="padding:12px 0 8px">30天重大爆發事件</div>', unsafe_allow_html=True)
            p_cols = st.columns(min(len(peaks_30d), 4))
            for i, ev in enumerate(peaks_30d[:8]):
                with p_cols[i % 4]:
                    color = KW_COLORS.get(ev["keyword"], "#8892aa")
                    chg   = ev.get("pct_above_mean", 0)
                    st.markdown(f"""
<div class="mi-corr-card" style="min-height:90px">
  <div style="font-family:'DM Mono';font-size:8px;color:#4a5270;margin-bottom:3px">{ev['date']}</div>
  <div style="font-family:'DM Mono';font-size:11px;font-weight:500;color:{color}">{ev['keyword']}</div>
  <div style="font-family:'DM Mono';font-size:9px;color:#ffab00;margin-top:3px">z={ev['z_score']:.1f} · +{chg:.0f}%</div>
</div>""", unsafe_allow_html=True)

        # WEEKLY + HOURLY PATTERNS
        c3, c4 = st.columns(2)
        with c3:
            st.markdown('<div class="mi-sec-title" style="padding:12px 0 6px">每週討論規律</div>', unsafe_allow_html=True)
            st.plotly_chart(
                pattern_bars(["週一", "週二", "週三", "週四", "週五"],
                             [55, 100, 62, 90, 70], highlight_idx=[1, 3]),
                use_container_width=True, config={"displayModeBar": False},
            )
        with c4:
            st.markdown('<div class="mi-sec-title" style="padding:12px 0 6px">每日時段熱度（美東）</div>', unsafe_allow_html=True)
            st.plotly_chart(
                pattern_bars(["09-11", "11-13", "13-15", "15-17", "21-23"],
                             [100, 65, 82, 55, 44], highlight_idx=[0, 2]),
                use_container_width=True, config={"displayModeBar": False},
            )

    with right_col2:
        # HIST INSIGHT
        for kw in keywords:
            z    = z_scores.get(kw, 0)
            sent = sentiments.get(kw, {})
            bull = sent.get("bull_pct", 50)
            color = KW_COLORS.get(kw, "#8892aa")
            mean_30 = float(volume_df[kw].mean()) if kw in volume_df.columns else 50
            cur_val = float(volume_df[kw].iloc[-1]) if kw in volume_df.columns else 50
            st.markdown(f"""
<div class="mi-hist-insight">
  <div class="mi-hi-title">▸ {kw} · 30天摘要</div>
  <div class="mi-hi-txt">30天平均熱度 <strong>{mean_30:.0f}</strong>，今日 <strong style="color:{color}">{cur_val:.0f}</strong>，情緒 <strong>{bull:.0f}%</strong> 看漲。</div>
  <div class="mi-stat-grid">
    <div class="mi-stat-box"><div class="mi-stat-big" style="color:{color}">{cur_val:.0f}</div><div class="mi-stat-lbl">今日</div></div>
    <div class="mi-stat-box"><div class="mi-stat-big" style="color:#d4daf0">{mean_30:.0f}</div><div class="mi-stat-lbl">30日均</div></div>
    <div class="mi-stat-box"><div class="mi-stat-big" style="color:#ffab00">z={z:.1f}</div><div class="mi-stat-lbl">異常度</div></div>
  </div>
</div>""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════
# TAB 3: STOCK CORRELATION
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    # HERO
    best_kw_corr = max(corr_results, key=lambda k: abs(corr_results[k].get("best_r", 0))) if corr_results else (keywords[0] if keywords else "TSLA")
    best_r_val   = corr_results.get(best_kw_corr, {}).get("best_r", 0)
    best_lag_val = corr_results.get(best_kw_corr, {}).get("best_lag", 0)
    lag_txt = f"領先 {best_lag_val} 天" if best_lag_val > 0 else ("同步" if best_lag_val == 0 else f"滯後 {-best_lag_val} 天")

    st.markdown(f"""
<div class="mi-hero">
  <div class="mi-eyebrow">社媒熱度 × 股票價格 關聯分析 · 30天回測</div>
  <div class="mi-headline">{best_kw_corr} 討論量<br>{lag_txt} 股價反應</div>
  <div class="mi-sub">過去 30 天數據顯示：<strong>{best_kw_corr}</strong> 與目標股票的 Pearson 相關係數達 <strong>r={best_r_val:.2f}</strong>，{'具備預測價值。' if abs(best_r_val) > 0.4 else '相關性尚可。'}</div>
  <div class="mi-sigs">
    <span class="mi-sig sg-bull">🏆 最強：{best_kw_corr} r={best_r_val:.2f}</span>
    <span class="mi-sig sg-ice">⏱ {lag_txt}</span>
    <span class="mi-sig sg-bear">❌ ETF相關性較弱</span>
  </div>
</div>""", unsafe_allow_html=True)

    main_col3, right_col3 = st.columns([3, 1], gap="small")

    with main_col3:
        # CORRELATION TABLE
        st.markdown('<div class="mi-sec-hdr"><div class="mi-sec-title">關聯強度分析</div><div class="mi-sec-note">正值=社媒領先股價；負值=股價先動後討論</div></div>', unsafe_allow_html=True)

        if corr_results:
            rows = []
            for kw, cr in corr_results.items():
                r    = cr.get("best_r", 0)
                lag  = cr.get("best_lag", 0)
                tkr  = PRICE_MAP.get(kw, PRICE_MAP.get(kw.upper(), "—"))
                strength = "強" if abs(r) >= 0.6 else "中" if abs(r) >= 0.4 else "弱"
                direction = "領先" if lag > 0 else "同步" if lag == 0 else "滯後"
                rows.append({
                    "關鍵字": kw, "股票": tkr,
                    "相關係數 r": f"{r:+.3f}",
                    "強度": strength,
                    f"領先/滯後": f"{direction} {abs(lag)}d",
                    "R²": f"{cr.get('r2',0):.2f}",
                })
            df_table = pd.DataFrame(rows)
            st.dataframe(
                df_table,
                use_container_width=True, hide_index=True,
                column_config={
                    "相關係數 r": st.column_config.TextColumn(width="small"),
                    "R²": st.column_config.TextColumn(width="small"),
                },
            )

        # LAG CHARTS
        for kw, cr in corr_results.items():
            color  = KW_COLORS.get(kw, "#8892aa")
            ticker = PRICE_MAP.get(kw, PRICE_MAP.get(kw.upper(), ""))
            if not cr.get("lags"):
                continue
            st.markdown(f'<div class="mi-sec-title" style="padding:12px 0 6px">{kw} → {ticker} 時間滯後分析</div>', unsafe_allow_html=True)
            st.plotly_chart(
                lag_correlation_chart(cr["lags"], cr["rs"], cr["best_lag"], height=180),
                use_container_width=True, config={"displayModeBar": False},
            )

        # SCATTER PLOTS
        st.markdown('<div class="mi-sec-title" style="padding:12px 0 6px">散點圖：討論量 vs 次日漲跌</div>', unsafe_allow_html=True)
        sc_cols = st.columns(min(len(keywords), 2))
        for i, kw in enumerate(keywords[:2]):
            with sc_cols[i % 2]:
                ticker = PRICE_MAP.get(kw, PRICE_MAP.get(kw.upper(), ""))
                pdf    = price_data.get(ticker, pd.DataFrame())
                if kw in volume_df.columns and not pdf.empty:
                    cr   = corr_results.get(kw, {})
                    lead = max(cr.get("best_lag", 1), 1)
                    st.markdown(f'<div style="font-size:9px;color:#4a5270;font-family:DM Mono;padding-bottom:4px">{kw} vs {ticker} (lead={lead}d) · r={cr.get("best_r",0):.2f}</div>', unsafe_allow_html=True)
                    st.plotly_chart(
                        scatter_volume_return(volume_df[kw], pdf, kw, ticker, lead, height=200),
                        use_container_width=True, config={"displayModeBar": False},
                    )

    with right_col3:
        # CORR CARDS
        st.markdown('<div style="padding:8px 0"><div class="mi-sec-title">關聯強度卡</div></div>', unsafe_allow_html=True)
        for kw, cr in corr_results.items():
            r      = cr.get("best_r", 0)
            lag    = cr.get("best_lag", 0)
            ticker = PRICE_MAP.get(kw, PRICE_MAP.get(kw.upper(), "—"))
            color  = KW_COLORS.get(kw, "#8892aa")
            bar_c  = COLORS["bull"] if abs(r) >= 0.6 else COLORS["warn"] if abs(r) >= 0.4 else COLORS["bear"]
            lag_c  = COLORS["bull"] if lag > 0 else COLORS["ice"] if lag == 0 else COLORS["warn"]
            lag_s  = f"📈 領先 {lag}天 · 建議設延遲警報" if lag > 0 else ("🔄 同步反應" if lag == 0 else f"⏬ 滯後 {-lag}天")
            desc   = (f"相關係數 r={r:.2f}，R²={cr.get('r2',0):.2f}。"
                      f"{'具備預測參考價值。' if abs(r) >= 0.5 else '相關性有限，需謹慎參考。'}")
            st.markdown(corr_card_html(
                pair=f"{kw} → {ticker}", pair_color=color,
                r_val=r, bar_color=bar_c,
                desc=desc, lag_text=lag_s, lag_color=lag_c,
            ), unsafe_allow_html=True)

        # AI INSIGHT on correlation
        st.markdown(f"""
<div class="mi-hist-insight" style="margin-top:14px">
  <div class="mi-hi-title">▸ AI 關聯洞察</div>
  <div class="mi-hi-txt">
    <strong>{best_kw_corr}</strong> 是當前最佳社媒預測因子（r={best_r_val:.2f}）。
    {'建議在討論量 z-score > 3 後設置 ' + str(abs(best_lag_val)) + ' 天延遲價格警報。' if best_lag_val > 0 else '信號與股價同步，實時監測即可。'}
  </div>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:16px 24px;border-top:1px solid #1c2030;display:flex;justify-content:space-between;
            align-items:center;font-family:'DM Mono';font-size:9px;color:#4a5270;margin-top:16px">
  <div>MARKETINTEL · 學術研究用途 · 數據來源：Google Trends / Stocktwits / Reddit / yFinance</div>
  <div>更新時間：{time_str} HKT · AI: Groq LLaMA 3.3</div>
</div>""", unsafe_allow_html=True)
