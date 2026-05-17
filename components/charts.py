# components/charts.py — Signal-focused Plotly charts
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_BG   = "#07080a"
_INK  = "#0e1015"
_LINE = "#1c2030"
_DIM  = "#4a5270"
_BODY = "#8892aa"
_BRIGHT = "#d4daf0"
_BULL = "#00e676"
_BEAR = "#ff3d57"
_WARN = "#ffab00"
_ICE  = "#00b8ff"
_LAV  = "#b388ff"
_FONT = dict(family="DM Mono, monospace", color=_BODY)

def _base(height=240, **kw) -> dict:
    d = dict(paper_bgcolor=_BG, plot_bgcolor=_BG, font=_FONT,
             margin=dict(l=8,r=8,t=28,b=8), height=height,
             xaxis=dict(gridcolor=_LINE,zerolinecolor=_LINE,tickfont=_FONT),
             yaxis=dict(gridcolor=_LINE,zerolinecolor=_LINE,tickfont=_FONT),
             legend=dict(bgcolor=_INK,bordercolor=_LINE,borderwidth=1,
                         font=dict(family="DM Mono",size=9,color=_DIM)))
    d.update(kw)
    return d

def _hex_rgba(h, a=0.1):
    h = h.lstrip("#")
    r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
    return f"rgba({r},{g},{b},{a})"

# ── 1. BULL/BEAR HOURLY AREA CHART ───────────────────────────────
def chart_sentiment_timeseries(hourly_df: pd.DataFrame, height=240) -> go.Figure:
    if hourly_df.empty:
        return _empty(height)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hourly_df.index, y=hourly_df["bull_pct"],
        name="Bull%", mode="lines", line=dict(color=_BULL,width=2),
        fill="tozeroy", fillcolor=_hex_rgba(_BULL,0.12),
        hovertemplate="Bull%: %{y:.1f}%<br>%{x|%m/%d %H:%M}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=hourly_df.index, y=hourly_df["bear_pct"],
        name="Bear%", mode="lines", line=dict(color=_BEAR,width=2),
        fill="tozeroy", fillcolor=_hex_rgba(_BEAR,0.10),
        hovertemplate="Bear%: %{y:.1f}%<br>%{x|%m/%d %H:%M}<extra></extra>",
    ))
    # 50% reference line
    fig.add_hline(y=50, line=dict(color=_DIM,dash="dot",width=1))
    # Avg line
    avg = float(hourly_df["bull_pct"].mean())
    fig.add_hline(y=avg, line=dict(color=_WARN,dash="dash",width=1),
                  annotation_text=f"24h均值 {avg:.0f}%",
                  annotation_font=dict(color=_WARN,size=9))
    fig.update_layout(**_base(height, yaxis=dict(range=[0,100],ticksuffix="%",
                              gridcolor=_LINE,tickfont=_FONT),
                              hovermode="x unified"))
    return fig

# ── 2. PRICE + SENTIMENT OVERLAY ─────────────────────────────────
def chart_price_sentiment_overlay(
    price_df: pd.DataFrame,
    hourly_df: pd.DataFrame,
    ticker: str,
    height=280,
) -> go.Figure:
    if price_df.empty:
        return _empty(height)
    fig = make_subplots(specs=[[{"secondary_y":True}]])
    # Price
    fig.add_trace(go.Scatter(
        x=price_df.index, y=price_df["Close"],
        name=f"{ticker} 股價", mode="lines",
        line=dict(color=_ICE,width=2),
        hovertemplate=f"{ticker}: $%{{y:.2f}}<extra></extra>",
    ), secondary_y=False)
    # Bull%
    if not hourly_df.empty:
        fig.add_trace(go.Bar(
            x=hourly_df.index, y=hourly_df["bull_pct"],
            name="Bull%", marker_color=[_BULL if v>=50 else _BEAR for v in hourly_df["bull_pct"]],
            opacity=0.5,
            hovertemplate="Bull%: %{y:.0f}%<extra></extra>",
        ), secondary_y=True)
        fig.update_yaxes(title_text="Bull%", secondary_y=True,
                         range=[0,100], ticksuffix="%",
                         tickfont=dict(color=_BULL,family="DM Mono",size=9),
                         gridcolor="rgba(0,0,0,0)")
    fig.update_layout(**_base(height, hovermode="x unified",
                               yaxis=dict(tickprefix="$",gridcolor=_LINE,tickfont=_FONT)))
    return fig

# ── 3. MESSAGE VOLUME BAR ─────────────────────────────────────────
def chart_volume_bars(hourly_df: pd.DataFrame, height=160) -> go.Figure:
    if hourly_df.empty:
        return _empty(height)
    mean_v = float(hourly_df["total"].mean())
    colors = [_WARN if v > mean_v*2 else _ICE if v > mean_v else _DIM
              for v in hourly_df["total"]]
    fig = go.Figure(go.Bar(
        x=hourly_df.index, y=hourly_df["total"],
        marker_color=colors,
        hovertemplate="%{y} 條訊息<br>%{x|%H:%M}<extra></extra>",
    ))
    fig.add_hline(y=mean_v, line=dict(color=_DIM,dash="dot",width=1),
                  annotation_text=f"均值 {mean_v:.0f}",
                  annotation_font=dict(color=_DIM,size=9))
    fig.update_layout(**_base(height, yaxis=dict(gridcolor=_LINE,tickfont=_FONT),
                               xaxis=dict(gridcolor="rgba(0,0,0,0)",tickfont=_FONT)))
    return fig

# ── 4. SIGNAL GAUGE ───────────────────────────────────────────────
def chart_signal_gauge(raw_score: float, signal: str, height=200) -> go.Figure:
    color = _BULL if signal=="BUY" else _BEAR if signal=="SELL" else _WARN if signal=="WATCH" else _DIM
    # Normalize -100..100 to 0..1
    norm = (raw_score + 100) / 200
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=raw_score,
        number=dict(suffix="", font=dict(family="Bebas Neue",size=36,color=color)),
        gauge=dict(
            axis=dict(range=[-100,100], tickwidth=1,
                      tickfont=dict(family="DM Mono",size=8,color=_DIM),
                      tickcolor=_DIM),
            bar=dict(color=color, thickness=0.25),
            bgcolor=_INK,
            borderwidth=1, bordercolor=_LINE,
            steps=[
                dict(range=[-100,-40], color=_hex_rgba(_BEAR,0.18)),
                dict(range=[-40,40],   color=_hex_rgba(_DIM,0.08)),
                dict(range=[40,100],   color=_hex_rgba(_BULL,0.18)),
            ],
            threshold=dict(line=dict(color=color,width=2), thickness=0.75, value=raw_score),
        ),
    ))
    fig.update_layout(paper_bgcolor=_BG, plot_bgcolor=_BG, height=height,
                      font=_FONT, margin=dict(l=20,r=20,t=20,b=10))
    return fig

# ── 5. BACKTEST SCATTER ───────────────────────────────────────────
def chart_backtest_returns(daily_df: pd.DataFrame, hold_days=2, height=220) -> go.Figure:
    if daily_df.empty or len(daily_df) < 8:
        return _empty(height)
    df = daily_df.copy()
    df["ret"] = df["Close"].pct_change(hold_days).shift(-hold_days) * 100
    df["mom"] = df["Close"].pct_change(3)
    df = df.dropna()
    pos = df[df["mom"] > 0]
    neg = df[df["mom"] <= 0]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pos.index, y=pos["ret"], mode="markers", name="情緒偏多日",
        marker=dict(color=_BULL,size=7,opacity=0.7,line=dict(width=0.5,color=_BG)),
        hovertemplate="%{x|%m/%d}: %{y:+.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=neg.index, y=neg["ret"], mode="markers", name="情緒偏空日",
        marker=dict(color=_BEAR,size=7,opacity=0.7,line=dict(width=0.5,color=_BG)),
        hovertemplate="%{x|%m/%d}: %{y:+.1f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line=dict(color=_DIM,width=1))
    fig.update_layout(**_base(height,
        yaxis=dict(ticksuffix="%",gridcolor=_LINE,tickfont=_FONT,
                   title="後續回報%"),
        xaxis=dict(gridcolor="rgba(0,0,0,0)",tickfont=_FONT),
        hovermode="closest"))
    return fig

# ── 6. REDDIT SENTIMENT BAR ──────────────────────────────────────
def chart_reddit_sentiment(posts: list, height=160) -> go.Figure:
    if not posts:
        return _empty(height)
    labels = ["看漲","中性","看跌"]
    bull = sum(1 for p in posts if p["sentiment"]=="bullish")
    neut = sum(1 for p in posts if p["sentiment"]=="neutral")
    bear = sum(1 for p in posts if p["sentiment"]=="bearish")
    fig = go.Figure(go.Bar(
        x=labels, y=[bull, neut, bear],
        marker_color=[_BULL, _DIM, _BEAR],
        text=[bull, neut, bear],
        textfont=dict(family="DM Mono",size=11,color=_BRIGHT),
        textposition="outside",
    ))
    fig.update_layout(**_base(height,
        yaxis=dict(showticklabels=False,gridcolor="rgba(0,0,0,0)"),
        xaxis=dict(tickfont=dict(family="DM Mono",size=10,color=_DIM),gridcolor="rgba(0,0,0,0)"),
        showlegend=False, margin=dict(l=8,r=8,t=8,b=8)))
    return fig

# ── 7. PRICE CANDLE (intraday) ───────────────────────────────────
def chart_price_candle(price_df: pd.DataFrame, ticker: str, height=220) -> go.Figure:
    if price_df.empty or not all(c in price_df.columns for c in ["Open","High","Low","Close"]):
        return _empty(height)
    fig = go.Figure(go.Candlestick(
        x=price_df.index,
        open=price_df["Open"], high=price_df["High"],
        low=price_df["Low"],   close=price_df["Close"],
        increasing=dict(line=dict(color=_BULL,width=1), fillcolor=_hex_rgba(_BULL,0.7)),
        decreasing=dict(line=dict(color=_BEAR,width=1), fillcolor=_hex_rgba(_BEAR,0.7)),
        name=ticker, hovertext=None,
    ))
    fig.update_layout(**_base(height,
        xaxis=dict(rangeslider=dict(visible=False),gridcolor=_LINE,tickfont=_FONT),
        yaxis=dict(tickprefix="$",gridcolor=_LINE,tickfont=_FONT)))
    return fig

def _empty(height=200) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(height=height, paper_bgcolor=_BG, plot_bgcolor=_BG,
        annotations=[dict(text="數據載入中...", x=0.5, y=0.5, showarrow=False,
                          font=dict(color=_DIM,size=12,family="DM Mono"))])
    return fig
