# data/fetcher.py — All data fetching for MarketIntel
# Streamlit Cloud compatible: no Playwright, no snscrape
# Sources: Google Trends, Stocktwits (public API), Reddit (PRAW-lite), yfinance

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import time, requests, random
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np
import streamlit as st
import yfinance as yf

try:
    from pytrends.request import TrendReq
    PYTRENDS_OK = True
except Exception:
    PYTRENDS_OK = False

from config import (
    PYTRENDS_TIMEOUT, PYTRENDS_RETRIES, REDDIT_LIMIT,
    STOCKTWITS_LIMIT, TTL_TRENDS, TTL_REDDIT, TTL_STOCKTWIT, TTL_YFINANCE,
    STOCKTWITS_SUBREDDITS, STOCKTWITS_MAP, TRENDS_GEO
)

# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE TRENDS
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=TTL_TRENDS, show_spinner=False)
def fetch_trends(keywords: tuple[str, ...], timeframe: str = "today 1-m") -> dict:
    """
    Returns:
        {
          "interest_over_time": pd.DataFrame,   # index=date, cols=keywords
          "interest_by_region": pd.DataFrame,   # index=region, cols=keywords
          "related": {kw: pd.DataFrame},
        }
    """
    if not PYTRENDS_OK:
        return _empty_trends(keywords)

    kws = list(keywords)[:5]   # Google Trends max 5
    try:
        pt = TrendReq(hl="en-US", tz=360,
                      timeout=PYTRENDS_TIMEOUT,
                      retries=PYTRENDS_RETRIES,
                      backoff_factor=0.5)
        pt.build_payload(kws, timeframe=timeframe, geo=TRENDS_GEO)
        iot = pt.interest_over_time()
        if "isPartial" in iot.columns:
            iot = iot.drop(columns=["isPartial"])

        try:
            ibr = pt.interest_by_region(resolution="COUNTRY", inc_low_vol=True)
        except Exception:
            ibr = pd.DataFrame()

        related = {}
        for kw in kws:
            try:
                time.sleep(random.uniform(0.5, 1.2))
                pt.build_payload([kw], timeframe=timeframe, geo=TRENDS_GEO)
                rq = pt.related_queries()
                related[kw] = rq.get(kw, {}).get("top", pd.DataFrame())
            except Exception:
                related[kw] = pd.DataFrame()

        return {"interest_over_time": iot, "interest_by_region": ibr, "related": related}
    except Exception as e:
        st.warning(f"Google Trends 限流，使用模擬數據。({e})")
        return _simulate_trends(keywords)


def _empty_trends(keywords):
    return {"interest_over_time": pd.DataFrame(), "interest_by_region": pd.DataFrame(), "related": {}}


def _simulate_trends(keywords):
    """Fallback: generate realistic-looking 30-day simulated trend data."""
    days = 30
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=days, freq="D")
    rng = np.random.default_rng(42)
    data = {}
    base = {"TSLA": 60, "TESLA": 50, "ELON MUSK": 70, "SPCX": 20}
    for kw in keywords:
        b = base.get(kw.upper(), 40)
        series = np.clip(b + rng.normal(0, 10, days).cumsum() * 0.3 + rng.normal(0, 8, days), 5, 100)
        # inject 2–3 spikes
        for _ in range(2):
            i = rng.integers(5, days - 2)
            series[i:i+2] = np.clip(series[i:i+2] * rng.uniform(1.8, 3.2), 0, 100)
        data[kw] = series.astype(int)
    return {
        "interest_over_time": pd.DataFrame(data, index=dates),
        "interest_by_region": pd.DataFrame(),
        "related": {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# STOCKTWITS  (public, no auth required for basic symbol streams)
# ─────────────────────────────────────────────────────────────────────────────
_ST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
}

@st.cache_data(ttl=TTL_STOCKTWIT, show_spinner=False)
def fetch_stocktwits(symbol: str, limit: int = STOCKTWITS_LIMIT) -> dict:
    """
    Returns:
        {
          "messages": [{"body", "sentiment", "created_at", "likes"}],
          "symbol": str,
          "bull_pct": float,
          "bear_pct": float,
          "total": int,
        }
    """
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
    params = {"limit": limit, "filter": "top"}
    try:
        r = requests.get(url, params=params, headers=_ST_HEADERS, timeout=10)
        if r.status_code != 200:
            return _simulate_stocktwits(symbol)
        data = r.json()
        msgs = data.get("messages", [])
        result = []
        bull = bear = 0
        for m in msgs:
            sent = None
            if m.get("entities", {}).get("sentiment"):
                sent = m["entities"]["sentiment"].get("basic", "").lower()
            if sent == "bullish":
                bull += 1
            elif sent == "bearish":
                bear += 1
            result.append({
                "body":       m.get("body", ""),
                "sentiment":  sent,
                "created_at": m.get("created_at", ""),
                "likes":      m.get("likes", {}).get("total", 0),
                "username":   m.get("user", {}).get("username", ""),
            })
        total = len(result)
        bull_pct = round(bull / total * 100, 1) if total else 50.0
        bear_pct = round(bear / total * 100, 1) if total else 30.0
        return {"messages": result, "symbol": symbol,
                "bull_pct": bull_pct, "bear_pct": bear_pct, "total": total}
    except Exception:
        return _simulate_stocktwits(symbol)


def _simulate_stocktwits(symbol: str) -> dict:
    rng = np.random.default_rng(int(time.time()) % 1000)
    bull = int(rng.integers(45, 78))
    bear = int(rng.integers(10, 35))
    return {
        "messages": [],
        "symbol": symbol,
        "bull_pct": float(bull),
        "bear_pct": float(bear),
        "total": int(rng.integers(80, 300)),
        "_simulated": True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# REDDIT  (public JSON API — no auth needed for public subreddits)
# ─────────────────────────────────────────────────────────────────────────────
_REDDIT_HEADERS = {
    "User-Agent": "MarketIntel/1.0 (academic research; contact: research@example.com)",
    "Accept": "application/json",
}

@st.cache_data(ttl=TTL_REDDIT, show_spinner=False)
def fetch_reddit(keyword: str, limit: int = REDDIT_LIMIT) -> dict:
    """
    Search Reddit for keyword across financial subreddits.
    Returns:
        {
          "posts": [{"title","score","num_comments","created_utc","subreddit","url"}],
          "total_score": int,
          "mention_count": int,
          "avg_score": float,
          "top_subreddits": {subreddit: count},
        }
    """
    subreddits = "+".join(STOCKTWITS_SUBREDDITS)
    url = f"https://www.reddit.com/r/{subreddits}/search.json"
    params = {
        "q": keyword, "sort": "hot", "t": "month",
        "limit": min(limit, 100), "restrict_sr": "true",
    }
    try:
        r = requests.get(url, params=params, headers=_REDDIT_HEADERS, timeout=12)
        if r.status_code != 200:
            return _simulate_reddit(keyword)
        data = r.json()
        children = data.get("data", {}).get("children", [])
        posts = []
        sub_count: dict[str, int] = {}
        for c in children:
            p = c.get("data", {})
            sub = p.get("subreddit", "")
            sub_count[sub] = sub_count.get(sub, 0) + 1
            posts.append({
                "title":       p.get("title", ""),
                "score":       p.get("score", 0),
                "num_comments":p.get("num_comments", 0),
                "created_utc": p.get("created_utc", 0),
                "subreddit":   sub,
                "url":         "https://reddit.com" + p.get("permalink", ""),
            })
        total_score = sum(p["score"] for p in posts)
        avg_score   = round(total_score / len(posts), 1) if posts else 0
        return {
            "posts":          posts,
            "total_score":    total_score,
            "mention_count":  len(posts),
            "avg_score":      avg_score,
            "top_subreddits": sub_count,
        }
    except Exception:
        return _simulate_reddit(keyword)


def _simulate_reddit(keyword: str) -> dict:
    rng = np.random.default_rng(hash(keyword) % 10000)
    n = int(rng.integers(20, 80))
    return {
        "posts": [],
        "total_score": int(rng.integers(5000, 50000)),
        "mention_count": n,
        "avg_score": float(rng.integers(100, 800)),
        "top_subreddits": {"wallstreetbets": n // 3, "stocks": n // 4},
        "_simulated": True,
    }


# ─────────────────────────────────────────────────────────────────────────────
# YFINANCE — price + volume history
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=TTL_YFINANCE, show_spinner=False)
def fetch_price_history(ticker: str, period: str = "1mo") -> pd.DataFrame:
    """Returns OHLCV DataFrame, index = date."""
    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, timeout=TTL_YFINANCE)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return _simulate_price(ticker)


@st.cache_data(ttl=TTL_YFINANCE, show_spinner=False)
def fetch_current_price(ticker: str) -> dict:
    """Returns {price, change_pct, volume} for display."""
    try:
        info = yf.Ticker(ticker).fast_info
        price = getattr(info, "last_price", None) or getattr(info, "regularMarketPrice", 0)
        prev  = getattr(info, "previous_close", price)
        chg   = round((price - prev) / prev * 100, 2) if prev else 0
        vol   = getattr(info, "three_month_average_volume", 0)
        return {"price": round(price, 2), "change_pct": chg, "volume": vol}
    except Exception:
        return {"price": 0.0, "change_pct": 0.0, "volume": 0}


def _simulate_price(ticker: str) -> pd.DataFrame:
    rng  = np.random.default_rng(42)
    days = 30
    dates = pd.date_range(end=datetime.now(timezone.utc), periods=days, freq="D")
    start = {"TSLA": 220, "SPCX": 11}.get(ticker.upper(), 100)
    prices = np.cumprod(1 + rng.normal(0, 0.015, days)) * start
    return pd.DataFrame({
        "Open":   prices * rng.uniform(0.99, 1.00, days),
        "High":   prices * rng.uniform(1.00, 1.02, days),
        "Low":    prices * rng.uniform(0.98, 1.00, days),
        "Close":  prices,
        "Volume": rng.integers(20_000_000, 80_000_000, days).astype(float),
    }, index=dates)


# ─────────────────────────────────────────────────────────────────────────────
# AGGREGATED MENTION VOLUME (combine Trends + Reddit + Stocktwits)
# ─────────────────────────────────────────────────────────────────────────────
def build_daily_volume(
    keywords: list[str],
    trends_data: dict,
    reddit_data: dict,      # {keyword: reddit_result}
    stocktwits_data: dict,  # {keyword: stocktwits_result}
) -> pd.DataFrame:
    """
    Combine all sources into a single normalised daily mention-volume DataFrame.
    index = date, columns = keywords, values = 0–100 normalised score.
    """
    iot: pd.DataFrame = trends_data.get("interest_over_time", pd.DataFrame())

    if iot.empty:
        days = 30
        dates = pd.date_range(end=datetime.now(timezone.utc), periods=days, freq="D")
        rng = np.random.default_rng(42)
        result = {}
        base = {"TSLA": 60, "TESLA": 50, "ELON MUSK": 75, "SPCX": 20}
        for kw in keywords:
            b = base.get(kw.upper(), 40)
            s = np.clip(b + rng.normal(0, 8, days) + rng.normal(0, 5, days).cumsum() * 0.2, 5, 100)
            result[kw] = s.astype(int)
        return pd.DataFrame(result, index=dates)

    # Keep only keyword columns that exist
    cols = [kw for kw in keywords if kw in iot.columns]
    df = iot[cols].copy() if cols else iot.copy()

    # Boost with Reddit signal (adds a small daily uniform boost on high-mention days)
    for kw in keywords:
        if kw in df.columns:
            rdata = reddit_data.get(kw, {})
            boost = min(rdata.get("mention_count", 0) / 10, 10)
            df[kw] = np.clip(df[kw] + boost, 0, 100)

    return df.fillna(0)
