# data/fetcher.py — Real data: Stocktwits + Reddit + yFinance + Google Trends
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

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
    VADER_OK = True
except Exception:
    VADER_OK = False

_ST_HDR = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://stocktwits.com",
}
_RD_HDR = {"User-Agent": "MarketSignal/1.0 (academic)","Accept":"application/json"}

# ── helpers ──────────────────────────────────────────────────────
def _resolve_sent(st_sent, body):
    vc = _vader.polarity_scores(body)["compound"] if VADER_OK and body else 0.0
    if st_sent == "bullish":   return "bullish", vc
    if st_sent == "bearish":   return "bearish", vc
    if vc >= 0.05:             return "bullish", vc
    if vc <= -0.05:            return "bearish", vc
    return "neutral", vc

def _parse_dt(s):
    try:    return datetime.fromisoformat(s.replace("Z","+00:00")).replace(tzinfo=None)
    except: return datetime.utcnow()

# ── STOCKTWITS ────────────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def fetch_stocktwits_stream(symbol: str, limit: int = 30) -> dict:
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json"
    try:
        r = requests.get(url, params={"limit": limit}, headers=_ST_HDR, timeout=12)
        if r.status_code != 200:
            return {"ok": False, "messages": [], "symbol": symbol, "error": f"HTTP {r.status_code}"}
        msgs = r.json().get("messages", [])
        parsed = []
        for m in msgs:
            body = m.get("body","")
            ent  = m.get("entities",{})
            raw  = ent.get("sentiment",{}).get("basic","").lower() if ent.get("sentiment") else None
            sent, vc = _resolve_sent(raw, body)
            parsed.append({
                "body":       body, "sentiment": sent, "created_at": _parse_dt(m.get("created_at","")),
                "likes":      m.get("likes",{}).get("total",0),
                "username":   m.get("user",{}).get("username",""),
                "followers":  m.get("user",{}).get("followers",0),
                "vader":      round(vc,3),
            })
        return {"ok": True, "messages": parsed, "symbol": symbol, "fetched_at": datetime.utcnow()}
    except Exception as e:
        return {"ok": False, "messages": [], "symbol": symbol, "error": str(e)}

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_stocktwits_history(symbol: str, pages: int = 8) -> list:
    """Paginate Stocktwits for more history (older messages)."""
    all_msgs, max_id = [], None
    for _ in range(pages):
        params = {"limit": 30}
        if max_id: params["max"] = max_id
        try:
            r = requests.get(f"https://api.stocktwits.com/api/2/streams/symbol/{symbol}.json",
                             params=params, headers=_ST_HDR, timeout=12)
            if r.status_code != 200: break
            msgs = r.json().get("messages", [])
            if not msgs: break
            for m in msgs:
                body = m.get("body","")
                ent  = m.get("entities",{})
                raw  = ent.get("sentiment",{}).get("basic","").lower() if ent.get("sentiment") else None
                sent, vc = _resolve_sent(raw, body)
                all_msgs.append({
                    "body": body, "sentiment": sent,
                    "created_at": _parse_dt(m.get("created_at","")),
                    "likes": m.get("likes",{}).get("total",0),
                    "username": m.get("user",{}).get("username",""),
                    "followers": m.get("user",{}).get("followers",0),
                    "vader": round(vc,3),
                })
            max_id = msgs[-1].get("id")
            time.sleep(random.uniform(0.2, 0.5))
        except Exception:
            break
    return all_msgs

# ── REDDIT ────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def fetch_reddit_posts(keyword: str, limit: int = 25) -> dict:
    subs = "wallstreetbets+stocks+investing+options+TSLA+StockMarket"
    params = {"q": keyword, "sort": "hot", "t": "day", "limit": limit, "restrict_sr": "true"}
    try:
        r = requests.get(f"https://www.reddit.com/r/{subs}/search.json",
                         params=params, headers=_RD_HDR, timeout=12)
        if r.status_code != 200:
            return {"ok": False, "posts": [], "keyword": keyword}
        posts = []
        for c in r.json().get("data",{}).get("children",[]):
            p = c.get("data",{})
            title = p.get("title","")
            vc = _vader.polarity_scores(title)["compound"] if VADER_OK else 0.0
            posts.append({
                "title": title, "score": p.get("score",0),
                "comments": p.get("num_comments",0),
                "created_at": datetime.fromtimestamp(p.get("created_utc",0)),
                "subreddit": p.get("subreddit",""),
                "url": "https://reddit.com" + p.get("permalink",""),
                "vader": round(vc,3),
                "sentiment": "bullish" if vc>0.05 else "bearish" if vc<-0.05 else "neutral",
            })
        return {"ok": True, "posts": posts, "keyword": keyword}
    except Exception as e:
        return {"ok": False, "posts": [], "keyword": keyword, "error": str(e)}

# ── YFINANCE ─────────────────────────────────────────────────────
@st.cache_data(ttl=120, show_spinner=False)
def fetch_price_realtime(ticker: str) -> dict:
    try:
        info  = yf.Ticker(ticker).fast_info
        price = float(getattr(info,"last_price",0) or getattr(info,"regularMarketPrice",0))
        prev  = float(getattr(info,"previous_close",price) or price)
        chg   = round((price-prev)/prev*100,2) if prev else 0.0
        return {"ok":True,"ticker":ticker,"price":round(price,2),"change_pct":chg,"prev_close":round(prev,2)}
    except Exception as e:
        return {"ok":False,"ticker":ticker,"price":0.0,"change_pct":0.0,"error":str(e)}

@st.cache_data(ttl=300, show_spinner=False)
def fetch_intraday(ticker: str, period: str = "5d", interval: str = "15m") -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False, timeout=15)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df.index = pd.to_datetime(df.index).tz_localize(None) if df.index.tz else pd.to_datetime(df.index)
        return df.dropna()
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=600, show_spinner=False)
def fetch_daily_history(ticker: str, period: str = "1mo") -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, timeout=15)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
        df.index = pd.to_datetime(df.index).normalize().tz_localize(None)
        return df.dropna()
    except Exception:
        return pd.DataFrame()

# ── GOOGLE TRENDS ─────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_trends_7d(keywords: tuple) -> pd.DataFrame:
    if not PYTRENDS_OK: return pd.DataFrame()
    try:
        pt = TrendReq(hl="en-US", tz=360, timeout=(10,25), retries=2, backoff_factor=0.5)
        pt.build_payload(list(keywords)[:5], timeframe="now 7-d", geo="")
        df = pt.interest_over_time()
        if "isPartial" in df.columns: df = df.drop(columns=["isPartial"])
        return df
    except Exception:
        return pd.DataFrame()

# ── HOURLY SENTIMENT TIMESERIES ───────────────────────────────────
def build_hourly_sentiment(messages: list, hours_back: int = 48) -> pd.DataFrame:
    """Aggregate Stocktwits messages into hourly bull/bear timeseries."""
    if not messages: return pd.DataFrame()
    now     = datetime.utcnow()
    cutoff  = now - timedelta(hours=hours_back)
    rows    = []
    for m in messages:
        dt = m["created_at"]
        if hasattr(dt,"tzinfo") and dt.tzinfo: dt = dt.replace(tzinfo=None)
        if dt < cutoff: continue
        rows.append({"hour": dt.replace(minute=0,second=0,microsecond=0),
                     "sentiment": m["sentiment"], "likes": m.get("likes",0)})
    if not rows: return pd.DataFrame()
    df = pd.DataFrame(rows)
    result = []
    for hour, grp in df.groupby("hour"):
        total = len(grp)
        bull  = (grp["sentiment"]=="bullish").sum()
        bear  = (grp["sentiment"]=="bearish").sum()
        result.append({
            "hour": hour, "bull_count": int(bull), "bear_count": int(bear),
            "total": int(total),
            "bull_pct": round(bull/total*100,1) if total else 50.0,
            "bear_pct": round(bear/total*100,1) if total else 25.0,
        })
    return pd.DataFrame(result).set_index("hour").sort_index()

def compute_sentiment_momentum(hourly_df: pd.DataFrame) -> dict:
    """Latest hour bull% vs rolling average — core signal input."""
    if hourly_df.empty or len(hourly_df) < 2:
        return {"momentum":0.0,"current_bull":50.0,"avg_bull":50.0,
                "direction":"neutral","msg_velocity":0,"current_vol":0,"avg_vol":0}
    current_bull = float(hourly_df["bull_pct"].iloc[-1])
    avg_bull     = float(hourly_df["bull_pct"].mean())
    momentum     = current_bull - avg_bull
    current_vol  = int(hourly_df["total"].iloc[-1])
    avg_vol      = float(hourly_df["total"].mean()) or 1
    velocity_pct = round((current_vol - avg_vol) / avg_vol * 100)
    direction    = "bullish" if momentum>5 else "bearish" if momentum<-5 else "neutral"
    return {"momentum":round(momentum,1),"current_bull":current_bull,
            "avg_bull":round(avg_bull,1),"direction":direction,
            "msg_velocity":velocity_pct,"current_vol":current_vol,"avg_vol":round(avg_vol,1)}
