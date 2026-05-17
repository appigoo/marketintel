# components/charts.py — All Plotly chart builders for MarketIntel

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from config import COLORS, KW_COLORS, CLUSTER_COLORS

_BG   = COLORS["bg"]
_INK  = COLORS["ink"]
_LINE = COLORS["line"]
_DIM  = COLORS["dim"]
_BODY = COLORS["body"]
_BRIGHT = COLORS["bright"]

_FONT = dict(family="DM Mono, monospace", color=_BODY)

def _base_layout(**kwargs) -> dict:
    return dict(
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        font=_FONT,
        margin=dict(l=12, r=12, t=28, b=12),
        legend=dict(
            bgcolor=_INK, bordercolor=_LINE, borderwidth=1,
            font=dict(family="DM Mono", size=9, color=_DIM),
        ),
        xaxis=dict(gridcolor=_LINE, zerolinecolor=_LINE, tickfont=_FONT),
        yaxis=dict(gridcolor=_LINE, zerolinecolor=_LINE, tickfont=_FONT),
        **kwargs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. TREND OVER TIME  (multi-line, with anomaly markers)
# ─────────────────────────────────────────────────────────────────────────────
def trend_chart(
    volume_df: pd.DataFrame,
    price_df:  pd.DataFrame | None = None,
    ticker:    str = "TSLA",
    peaks_mask: pd.DataFrame | None = None,
    height:    int = 260,
) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": price_df is not None and not price_df.empty}]])

    for kw in volume_df.columns:
        color = KW_COLORS.get(kw, CLUSTER_COLORS[list(volume_df.columns).index(kw) % len(CLUSTER_COLORS)])
        fig.add_trace(go.Scatter(
            x=volume_df.index, y=volume_df[kw],
            name=kw, mode="lines",
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=color.replace(")", ",0.06)").replace("rgb", "rgba") if "rgb" in color else color + "10",
            hovertemplate=f"<b>{kw}</b><br>熱度: %{{y:.0f}}<br>%{{x|%m/%d}}<extra></extra>",
        ), secondary_y=False)

        # Anomaly peak markers
        if peaks_mask is not None and kw in peaks_mask.columns:
            pk_dates = volume_df.index[peaks_mask[kw]]
            pk_vals  = volume_df.loc[pk_dates, kw]
            if len(pk_dates):
                fig.add_trace(go.Scatter(
                    x=pk_dates, y=pk_vals,
                    mode="markers", showlegend=False,
                    marker=dict(symbol="triangle-up", size=10, color=color,
                                line=dict(width=1, color=_BG)),
                    hovertemplate=f"<b>⚡ 異常爆發</b><br>{kw}: %{{y:.0f}}<extra></extra>",
                ), secondary_y=False)

    # Overlay price
    if price_df is not None and not price_df.empty and "Close" in price_df.columns:
        fig.add_trace(go.Scatter(
            x=price_df.index, y=price_df["Close"],
            name=f"{ticker} 股價",
            mode="lines",
            line=dict(color="#00b8ff", width=1.5, dash="dot"),
            hovertemplate=f"<b>{ticker}</b>: $%{{y:.2f}}<extra></extra>",
        ), secondary_y=True)
        fig.update_yaxes(
            title_text=f"{ticker} ($)", secondary_y=True,
            tickfont=dict(color="#00b8ff", family="DM Mono", size=9),
            gridcolor="transparent",
        )

    fig.update_layout(
        height=height, hovermode="x unified",
        **_base_layout(
            xaxis_title=None,
            yaxis_title="討論熱度指數",
        )
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 2. CO-OCCURRENCE HEATMAP
# ─────────────────────────────────────────────────────────────────────────────
def cooccurrence_heatmap(cooccur_df: pd.DataFrame, height: int = 220) -> go.Figure:
    kws = list(cooccur_df.columns)
    mat = cooccur_df.values

    # Custom colorscale: dark → ice blue
    colorscale = [
        [0.0, _LINE],
        [0.4, "#1a3a5c"],
        [0.7, "#006699"],
        [1.0, "#00b8ff"],
    ]

    text_mat = [[f"{mat[i][j]:.2f}" for j in range(len(kws))] for i in range(len(kws))]

    fig = go.Figure(go.Heatmap(
        z=mat, x=kws, y=kws,
        text=text_mat, texttemplate="%{text}",
        textfont=dict(family="DM Mono", size=10, color=_BRIGHT),
        colorscale=colorscale,
        showscale=False,
        hoverongaps=False,
        hovertemplate="<b>%{y} ↔ %{x}</b><br>共現強度: %{z:.2f}<extra></extra>",
    ))
    fig.update_layout(
        height=height,
        **_base_layout(margin=dict(l=12, r=12, t=12, b=12)),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 3. SENTIMENT DONUT
# ─────────────────────────────────────────────────────────────────────────────
def sentiment_donut(bull: float, bear: float, neut: float, height: int = 200) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=["看漲 Bullish", "看跌 Bearish", "中性 Neutral"],
        values=[bull, bear, neut],
        hole=0.68,
        marker=dict(
            colors=[COLORS["bull"] + "cc", COLORS["bear"] + "cc", COLORS["dim"] + "cc"],
            line=dict(color=_BG, width=2),
        ),
        textfont=dict(family="DM Mono", size=9, color=_BRIGHT),
        hovertemplate="<b>%{label}</b>: %{value:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        height=height,
        showlegend=True,
        legend=dict(
            orientation="v", x=1.02, y=0.5,
            bgcolor=_BG, font=dict(family="DM Mono", size=9, color=_DIM),
        ),
        annotations=[dict(
            text=f"<b>{bull:.0f}%</b><br><span style='font-size:9px'>看漲</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="Bebas Neue", size=26, color=COLORS["bull"]),
        )],
        **_base_layout(margin=dict(l=0, r=80, t=10, b=10)),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 4. LAG CORRELATION BAR CHART
# ─────────────────────────────────────────────────────────────────────────────
def lag_correlation_chart(lags: list[int], rs: list[float],
                          best_lag: int, height: int = 200) -> go.Figure:
    colors = []
    for lag, r in zip(lags, rs):
        if lag == best_lag:
            colors.append(COLORS["bull"])
        elif r >= 0.5:
            colors.append(COLORS["warn"])
        elif r < 0:
            colors.append(COLORS["bear"])
        else:
            colors.append(_DIM)

    lag_labels = [f"{'+' if l > 0 else ''}{l}d" if l != 0 else "同步" for l in lags]

    fig = go.Figure(go.Bar(
        x=lag_labels, y=rs, marker_color=colors,
        text=[f"{r:.2f}" for r in rs],
        textfont=dict(family="DM Mono", size=8, color=_BRIGHT),
        textposition="outside",
        hovertemplate="時間偏移: %{x}<br>相關係數 r: %{y:.3f}<extra></extra>",
    ))
    fig.update_layout(
        height=height,
        yaxis=dict(range=[-1, 1.15], tickformat=".2f",
                   gridcolor=_LINE, zerolinecolor=_LINE,
                   tickfont=dict(family="DM Mono", size=8, color=_DIM)),
        xaxis=dict(gridcolor="transparent",
                   tickfont=dict(family="DM Mono", size=8, color=_DIM)),
        **_base_layout(
            annotations=[dict(
                x=f"{'+' if best_lag > 0 else ''}{best_lag}d" if best_lag != 0 else "同步",
                y=max(rs) + 0.05,
                text="★ 最佳", showarrow=False,
                font=dict(color=COLORS["bull"], size=9, family="DM Mono"),
            )] if rs else [],
        ),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 5. SCATTER (volume vs next-day return)
# ─────────────────────────────────────────────────────────────────────────────
def scatter_volume_return(
    volume_series: pd.Series,
    price_df:      pd.DataFrame,
    keyword:       str,
    ticker:        str,
    lead_days:     int = 1,
    height:        int = 220,
) -> go.Figure:
    if price_df.empty or volume_series.empty:
        return _empty_fig(height)

    ret = price_df["Close"].pct_change(lead_days).shift(-lead_days)
    common = volume_series.index.intersection(ret.index)
    if len(common) < 5:
        return _empty_fig(height)

    x = volume_series.loc[common]
    y = ret.loc[common] * 100
    df = pd.DataFrame({"vol": x, "ret": y}).dropna()

    if len(df) < 5:
        return _empty_fig(height)

    # Linear regression
    m, b = np.polyfit(df["vol"], df["ret"], 1)
    x_line = np.linspace(df["vol"].min(), df["vol"].max(), 50)
    y_line = m * x_line + b

    color = COLORS["bull"] if df["ret"].corr(df["vol"]) > 0 else COLORS["bear"]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["vol"], y=df["ret"], mode="markers",
        marker=dict(color=color, size=6, opacity=0.6,
                    line=dict(width=0.5, color=_BG)),
        hovertemplate=f"熱度: %{{x:.0f}}<br>{ticker} {lead_days}日後: %{{y:.1f}}%<extra></extra>",
        name="數據點",
    ))
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, mode="lines",
        line=dict(color=color, width=1.5, dash="dash"),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        height=height, showlegend=False,
        xaxis_title=f"{keyword} 討論熱度",
        yaxis_title=f"{ticker} {lead_days}日後漲跌 (%)",
        **_base_layout(),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 6. 30-DAY DUAL AXIS (trends + price overlaid)
# ─────────────────────────────────────────────────────────────────────────────
def dual_axis_30d(
    volume_df:  pd.DataFrame,
    price_dfs:  dict[str, pd.DataFrame],   # {ticker: df}
    peaks_mask: pd.DataFrame | None = None,
    height:     int = 280,
) -> go.Figure:
    tickers = list(price_dfs.keys())
    has_price = bool(tickers and not price_dfs[tickers[0]].empty)

    fig = make_subplots(specs=[[{"secondary_y": has_price}]])

    for kw in volume_df.columns:
        color = KW_COLORS.get(kw, "#8892aa")
        fig.add_trace(go.Scatter(
            x=volume_df.index, y=volume_df[kw],
            name=f"{kw} 討論量", mode="lines",
            line=dict(color=color + "bb", width=1.5),
            fill="tozeroy",
            fillcolor=color + "0d",
        ), secondary_y=False)
        if peaks_mask is not None and kw in peaks_mask.columns:
            pk = volume_df.index[peaks_mask[kw]]
            if len(pk):
                fig.add_trace(go.Scatter(
                    x=pk, y=volume_df.loc[pk, kw],
                    mode="markers", showlegend=False,
                    marker=dict(symbol="star", size=12, color=COLORS["bear"]),
                    hovertemplate=f"⚠ <b>爆發</b><br>{kw}: %{{y:.0f}}<extra></extra>",
                ), secondary_y=False)

    if has_price:
        tkr = tickers[0]
        pdf = price_dfs[tkr]
        if "Close" in pdf.columns:
            fig.add_trace(go.Scatter(
                x=pdf.index, y=pdf["Close"],
                name=f"{tkr} 股價",
                mode="lines",
                line=dict(color=COLORS["ice"], width=2),
            ), secondary_y=True)
            fig.update_yaxes(
                title_text=f"{tkr} ($)", secondary_y=True,
                tickfont=dict(color=COLORS["ice"], family="DM Mono", size=9),
                gridcolor="transparent",
            )

    fig.update_layout(
        height=height, hovermode="x unified",
        **_base_layout(yaxis_title="討論熱度指數"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 7. WEEKLY / HOURLY PATTERN BARS
# ─────────────────────────────────────────────────────────────────────────────
def pattern_bars(labels: list[str], values: list[float],
                 highlight_idx: list[int] | None = None,
                 color: str = COLORS["ice"], height: int = 160) -> go.Figure:
    colors = []
    for i in range(len(labels)):
        if highlight_idx and i in highlight_idx:
            colors.append(color)
        else:
            colors.append(_DIM)

    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors,
        text=[f"{v:.0f}" for v in values],
        textfont=dict(family="DM Mono", size=9, color=_BRIGHT),
        textposition="outside",
        hovertemplate="%{x}: %{y:.0f}<extra></extra>",
    ))
    fig.update_layout(
        height=height,
        yaxis=dict(showticklabels=False, gridcolor=_LINE),
        xaxis=dict(tickfont=dict(family="DM Mono", size=9, color=_DIM), gridcolor="transparent"),
        **_base_layout(margin=dict(l=8, r=8, t=8, b=8)),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# 8. ZSCORE GAUGE-LIKE BAR
# ─────────────────────────────────────────────────────────────────────────────
def zscore_bars(kw_z: dict[str, float], height: int = 160) -> go.Figure:
    keywords = list(kw_z.keys())
    z_vals   = [kw_z[k] for k in keywords]
    colors   = []
    for z in z_vals:
        if z >= 3.5:  colors.append(COLORS["bear"])
        elif z >= 2:  colors.append(COLORS["warn"])
        else:         colors.append(COLORS["bull"])

    fig = go.Figure(go.Bar(
        x=keywords, y=z_vals, marker_color=colors,
        text=[f"z={z:.1f}" for z in z_vals],
        textfont=dict(family="DM Mono", size=10, color=_BRIGHT),
        textposition="outside",
        hovertemplate="%{x}<br>z-score: %{y:.2f}<extra></extra>",
    ))
    fig.add_hline(y=3.5, line=dict(color=COLORS["bear"], dash="dash", width=1),
                  annotation_text="紅色警報 3.5", annotation_font_color=COLORS["bear"],
                  annotation_font_size=9)
    fig.add_hline(y=2.0, line=dict(color=COLORS["warn"], dash="dot", width=1),
                  annotation_text="黃色警告 2.0", annotation_font_color=COLORS["warn"],
                  annotation_font_size=9)
    fig.update_layout(
        height=height,
        yaxis=dict(range=[0, max(max(z_vals) + 0.5, 4)], gridcolor=_LINE,
                   tickfont=dict(family="DM Mono", size=8, color=_DIM)),
        xaxis=dict(tickfont=dict(family="DM Mono", size=9, color=_DIM), gridcolor="transparent"),
        **_base_layout(margin=dict(l=8, r=8, t=20, b=8)),
    )
    return fig


# ── HELPER ──────────────────────────────────────────────────────────────────
def _empty_fig(height: int = 200) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        height=height,
        annotations=[dict(text="數據不足", x=0.5, y=0.5, showarrow=False,
                          font=dict(color=_DIM, size=12, family="DM Mono"))],
        **_base_layout(),
    )
    return fig
