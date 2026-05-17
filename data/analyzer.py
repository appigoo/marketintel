# data/analyzer.py — Analysis engine for MarketIntel

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
import pandas as pd
from scipy import stats
from scipy.signal import correlate
import networkx as nx

try:
    import community as community_louvain
    LOUVAIN_OK = True
except Exception:
    LOUVAIN_OK = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
    VADER_OK = True
except Exception:
    VADER_OK = False

from config import ZSCORE_RED, ZSCORE_YELLOW, STRONG_CORR, COOCCUR_MIN


# ─────────────────────────────────────────────────────────────────────────────
# Z-SCORE ANOMALY DETECTION
# ─────────────────────────────────────────────────────────────────────────────
def compute_zscore_series(series: pd.Series, window: int = 14) -> pd.Series:
    """Rolling z-score against a rolling mean/std."""
    roll_mean = series.rolling(window, min_periods=3).mean()
    roll_std  = series.rolling(window, min_periods=3).std()
    z = (series - roll_mean) / roll_std.replace(0, 1)
    return z.fillna(0)


def current_zscore(series: pd.Series, window: int = 14) -> float:
    z = compute_zscore_series(series, window)
    return float(z.iloc[-1]) if len(z) else 0.0


def zscore_level(z: float) -> tuple[str, str]:
    """Returns (level, colour)."""
    if z >= ZSCORE_RED:
        return "紅色警報 ⚠", "#ff3d57"
    if z >= ZSCORE_YELLOW:
        return "黃色警告", "#ffab00"
    return "正常", "#00e676"


def detect_peaks(series: pd.Series, threshold_z: float = 2.0) -> pd.Series:
    """Boolean mask where z-score exceeds threshold."""
    z = compute_zscore_series(series)
    return z >= threshold_z


# ─────────────────────────────────────────────────────────────────────────────
# SENTIMENT ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def vader_sentiment(text: str) -> dict:
    if not VADER_OK or not text:
        return {"compound": 0.0, "pos": 0.0, "neg": 0.0, "neu": 1.0}
    return _vader.polarity_scores(text)


def batch_sentiment(texts: list[str]) -> pd.DataFrame:
    rows = [vader_sentiment(t) for t in texts]
    return pd.DataFrame(rows)


def aggregate_sentiment(messages: list[dict]) -> dict:
    """
    messages: [{body, sentiment}, ...]
    sentiment field is 'bullish'/'bearish'/None (from Stocktwits)
    """
    if not messages:
        return {"bull_pct": 55.0, "bear_pct": 25.0, "neut_pct": 20.0, "compound": 0.1}

    bull = sum(1 for m in messages if m.get("sentiment") == "bullish")
    bear = sum(1 for m in messages if m.get("sentiment") == "bearish")
    n    = len(messages)
    neut = n - bull - bear

    # Also run VADER on text for compound score
    compounds = [vader_sentiment(m.get("body", ""))["compound"] for m in messages]
    avg_compound = float(np.mean(compounds)) if compounds else 0.0

    return {
        "bull_pct":  round(bull / n * 100, 1),
        "bear_pct":  round(bear / n * 100, 1),
        "neut_pct":  round(neut / n * 100, 1),
        "compound":  round(avg_compound, 3),
    }


def sentiment_verdict(bull_pct: float, bear_pct: float, z: float) -> tuple[str, str, str]:
    """Returns (verdict_text, verdict_class, reason)."""
    diff = bull_pct - bear_pct
    if z > ZSCORE_RED and diff > 15:
        return "看漲", "vd-bull", f"情緒偏多（{bull_pct:.0f}%），且討論量異常爆發"
    if diff > 20:
        return "看漲", "vd-bull", f"Bullish 情緒主導（{bull_pct:.0f}%）"
    if diff > 8:
        return "偏多", "vd-bull", f"情緒偏向看漲（{bull_pct:.0f}%）"
    if diff < -15:
        return "看跌", "vd-bear", f"Bearish 情緒主導（{bear_pct:.0f}%）"
    if abs(diff) < 8 and z > ZSCORE_YELLOW:
        return "分裂", "vd-warn", "討論量爆發但情緒分歧，需留意"
    return "觀望", "vd-neut", "情緒中性，討論量平穩"


# ─────────────────────────────────────────────────────────────────────────────
# CO-OCCURRENCE MATRIX
# ─────────────────────────────────────────────────────────────────────────────
def build_cooccurrence_matrix(
    keywords: list[str],
    posts: list[dict],          # each has "title" + optional "body"
) -> pd.DataFrame:
    """
    Build normalised co-occurrence matrix from Reddit/Stocktwits posts.
    Returns DataFrame with values 0–1 (Jaccard-like normalisation).
    """
    kws_upper = [k.upper() for k in keywords]
    n = len(keywords)
    counts = np.zeros((n, n), dtype=float)

    for post in posts:
        text = (post.get("title", "") + " " + post.get("body", "")).upper()
        present = [i for i, k in enumerate(kws_upper) if k in text]
        for a in present:
            for b in present:
                counts[a][b] += 1

    # Normalise: divide by max co-occurrence
    mx = counts.max()
    normed = counts / mx if mx > 0 else counts
    np.fill_diagonal(normed, 1.0)

    return pd.DataFrame(normed, index=keywords, columns=keywords)


def cooccurrence_from_trends(volume_df: pd.DataFrame) -> pd.DataFrame:
    """
    Correlation-based co-occurrence from trend time series.
    Uses Pearson correlation as proxy for co-occurrence strength.
    """
    if volume_df.empty or len(volume_df.columns) < 2:
        kws = list(volume_df.columns) if not volume_df.empty else []
        n = len(kws)
        mat = pd.DataFrame(np.eye(n), index=kws, columns=kws)
        return mat
    return volume_df.corr(method="pearson").clip(0, 1).fillna(0)


# ─────────────────────────────────────────────────────────────────────────────
# FORCE GRAPH  (networkx)
# ─────────────────────────────────────────────────────────────────────────────
def build_force_graph(
    keywords: list[str],
    cooccur_df: pd.DataFrame,
    volume_df:  pd.DataFrame,
    sentiment:  dict[str, dict],   # {kw: {bull_pct, bear_pct, compound}}
    min_edge:   float = 0.25,
) -> nx.Graph:
    G = nx.Graph()

    # Compute current volume (last day normalised)
    last_vol: dict[str, float] = {}
    if not volume_df.empty:
        last_row = volume_df.iloc[-1]
        mx = last_row.max() or 1
        for kw in keywords:
            last_vol[kw] = float(last_row.get(kw, 0)) / mx

    for kw in keywords:
        sent = sentiment.get(kw, {})
        G.add_node(
            kw,
            size=20 + int(last_vol.get(kw, 0.5) * 30),
            bull_pct=sent.get("bull_pct", 50),
            compound=sent.get("compound", 0),
            group="keyword",
        )

    # Add secondary topic nodes from related queries
    secondary = {
        "TSLA": ["ROBOTAXI", "FSD", "OPTIMUS", "EARNINGS"],
        "TESLA": ["EARNINGS", "AI"],
        "ELON MUSK": ["DOGE", "POLITICS", "xAI", "SPACEX"],
        "SPCX": ["STARSHIP", "SPACEX"],
    }
    for kw in keywords:
        for sec in secondary.get(kw.upper(), []):
            if sec not in G.nodes:
                G.add_node(sec, size=12, bull_pct=50, compound=0, group="secondary")
            G.add_edge(kw, sec, weight=0.4)

    # Add edges from co-occurrence matrix
    kws = [k for k in keywords if k in cooccur_df.index]
    for i, a in enumerate(kws):
        for j, b in enumerate(kws):
            if j <= i:
                continue
            w = float(cooccur_df.loc[a, b])
            if w >= min_edge:
                G.add_edge(a, b, weight=round(w, 3))

    # Community detection
    if LOUVAIN_OK and len(G.nodes) > 1:
        try:
            partition = community_louvain.best_partition(G)
            nx.set_node_attributes(G, partition, "community")
        except Exception:
            for i, node in enumerate(G.nodes):
                G.nodes[node]["community"] = i % 5
    else:
        for i, node in enumerate(G.nodes):
            G.nodes[node]["community"] = i % 5

    return G


def graph_to_plotly(G: nx.Graph, width: int = 800, height: int = 400) -> dict:
    """
    Convert networkx graph to Plotly figure dict for st.plotly_chart.
    Uses spring layout.
    """
    import plotly.graph_objects as go

    COMMUNITY_COLS = ["#00b8ff", "#b388ff", "#ff3d57", "#00e676", "#ffab00",
                      "#ff6b35", "#00e5ff", "#ea80fc"]

    pos = nx.spring_layout(G, seed=42, k=2.5 / max(len(G.nodes) ** 0.5, 1))

    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    node_x, node_y, node_text, node_size, node_color, hover_text = [], [], [], [], [], []
    for node in G.nodes():
        x, y = pos[node]
        d = G.nodes[node]
        node_x.append(x); node_y.append(y)
        node_text.append(node)
        node_size.append(d.get("size", 15))
        comm = d.get("community", 0)
        node_color.append(COMMUNITY_COLS[comm % len(COMMUNITY_COLS)])
        bull = d.get("bull_pct", 50)
        hover_text.append(
            f"<b>{node}</b><br>"
            f"看漲情緒: {bull:.0f}%<br>"
            f"話題群: {comm}"
        )

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1, color="#1c2030"),
        hoverinfo="none",
    )
    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=node_text, textposition="top center",
        textfont=dict(family="DM Mono", size=10, color="#d4daf0"),
        hoverinfo="text", hovertext=hover_text,
        marker=dict(
            size=node_size, color=node_color,
            line=dict(width=1.5, color="#1c2030"),
            opacity=0.9,
        ),
    )

    fig = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            paper_bgcolor="#07080a", plot_bgcolor="#07080a",
            width=width, height=height,
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            hovermode="closest",
            font=dict(family="DM Mono", color="#8892aa"),
        ),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# PRICE × VOLUME CORRELATION
# ─────────────────────────────────────────────────────────────────────────────
def compute_price_correlation(
    volume_df: pd.DataFrame,
    price_df:  pd.DataFrame,
    keyword:   str,
    ticker:    str,
    max_lag:   int = 5,        # days
) -> dict:
    """
    Computes Pearson r between keyword volume and ticker daily return
    at different lags (−max_lag … +max_lag days).
    Positive lag = volume leads price.

    Returns {
        "best_lag": int,     days (positive = social leads)
        "best_r":   float,
        "lags":     list[int],
        "rs":       list[float],
        "r_sync":   float,   same-day r
        "r2":       float,
    }
    """
    if volume_df.empty or price_df.empty:
        return _empty_corr()

    try:
        # Align on date
        vol  = volume_df[keyword].dropna() if keyword in volume_df.columns else pd.Series(dtype=float)
        ret  = price_df["Close"].pct_change().dropna()

        if vol.empty or ret.empty:
            return _empty_corr()

        # Normalise both indices to date-only (strip timezone / time component)
        vol.index = pd.to_datetime(vol.index).normalize().tz_localize(None)
        ret.index = pd.to_datetime(ret.index).normalize().tz_localize(None)

        common = vol.index.intersection(ret.index)
        if len(common) < 8:
            return _empty_corr()

        vol = vol.loc[common]
        ret = ret.loc[common]

        lags, rs = [], []
        for lag in range(-max_lag, max_lag + 1):
            if lag >= 0:
                v_shift = vol.shift(lag).dropna()
                r_align = ret.loc[v_shift.index]
            else:
                r_shift = ret.shift(-lag).dropna()
                v_shift = vol.loc[r_shift.index]
                r_align = r_shift

            idx = v_shift.index.intersection(r_align.index)
            if len(idx) < 8:
                lags.append(lag); rs.append(0.0)
                continue
            r_val, _ = stats.pearsonr(v_shift.loc[idx], r_align.loc[idx])
            lags.append(lag); rs.append(round(float(r_val), 3))

        best_idx = int(np.argmax(np.abs(rs)))
        best_lag = lags[best_idx]
        best_r   = rs[best_idx]
        r_sync   = rs[lags.index(0)] if 0 in lags else 0.0

        return {
            "best_lag": best_lag,
            "best_r":   best_r,
            "lags":     lags,
            "rs":       rs,
            "r_sync":   r_sync,
            "r2":       round(best_r ** 2, 3),
            "keyword":  keyword,
            "ticker":   ticker,
        }
    except Exception:
        return _empty_corr()


def _empty_corr() -> dict:
    return {"best_lag": 0, "best_r": 0.0, "lags": list(range(-5, 6)),
            "rs": [0.0] * 11, "r_sync": 0.0, "r2": 0.0}


def build_all_correlations(
    keywords:   list[str],
    volume_df:  pd.DataFrame,
    price_data: dict[str, pd.DataFrame],   # {ticker: price_df}
    price_map:  dict[str, str],            # {keyword: ticker}
) -> dict[str, dict]:
    """Build correlation result for each keyword→ticker pair."""
    results = {}
    for kw in keywords:
        ticker = price_map.get(kw.upper(), price_map.get(kw))
        if not ticker or ticker not in price_data:
            continue
        results[kw] = compute_price_correlation(
            volume_df, price_data[ticker], kw, ticker
        )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 30-DAY PEAK EVENT DETECTION
# ─────────────────────────────────────────────────────────────────────────────
def detect_30d_peaks(volume_df: pd.DataFrame, threshold_z: float = 2.0) -> list[dict]:
    """
    Returns list of peak events sorted by peak magnitude, for display.
    [{date, keyword, z_score, value, pct_above_mean}]
    """
    events = []
    for kw in volume_df.columns:
        series = volume_df[kw].dropna()
        z = compute_zscore_series(series)
        peaks = z[z >= threshold_z]
        for date, zval in peaks.items():
            mean_val = float(series.mean()) or 1
            val      = float(series.get(date, 0))
            events.append({
                "date":         pd.Timestamp(date).strftime("%m/%d"),
                "keyword":      kw,
                "z_score":      round(float(zval), 1),
                "value":        round(val, 1),
                "pct_above_mean": round((val - mean_val) / mean_val * 100, 0),
            })
    events.sort(key=lambda x: x["z_score"], reverse=True)
    return events[:8]


# ─────────────────────────────────────────────────────────────────────────────
# AI SCORE (heuristic bullish strength 0–100)
# ─────────────────────────────────────────────────────────────────────────────
def compute_ai_score(
    sentiments: dict[str, dict],
    z_scores:   dict[str, float],
    corr_data:  dict[str, dict],
    keywords:   list[str],
) -> int:
    """Weighted heuristic score 0–100."""
    if not keywords:
        return 50

    weights = {"sentiment": 0.40, "momentum": 0.35, "correlation": 0.25}
    sent_score = np.mean([
        sentiments.get(kw, {}).get("bull_pct", 50) for kw in keywords
    ])
    z_vals = [min(abs(z_scores.get(kw, 0)), 5) for kw in keywords]
    mom_score = 50 + float(np.mean(z_vals)) * 8

    r_vals = [abs(corr_data.get(kw, {}).get("best_r", 0)) for kw in keywords]
    corr_score = float(np.mean(r_vals)) * 100 if r_vals else 50

    raw = (sent_score * weights["sentiment"] +
           mom_score  * weights["momentum"]  +
           corr_score * weights["correlation"])
    return int(np.clip(raw, 0, 100))
