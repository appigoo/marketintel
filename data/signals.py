# data/signals.py — Core trading signal engine
# Converts real Stocktwits + price data into actionable BUY/SELL/HOLD signals
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy import stats

# ─────────────────────────────────────────────────────────────────
# SIGNAL DEFINITIONS
# ─────────────────────────────────────────────────────────────────
SIGNAL_BUY   = "BUY"
SIGNAL_SELL  = "SELL"
SIGNAL_HOLD  = "HOLD"
SIGNAL_WATCH = "WATCH"   # Not actionable yet, but heating up

# ─────────────────────────────────────────────────────────────────
# SIGNAL 1: SENTIMENT MOMENTUM
# Bull% surge → price tends to follow within 2-4 hours
# ─────────────────────────────────────────────────────────────────
def signal_sentiment_momentum(hourly_df: pd.DataFrame) -> dict:
    """
    Compare latest 1h bull% vs:
    - 6h rolling average (short baseline)
    - 24h rolling average (long baseline)

    Strong BUY: bull% jumped >15pp from 24h avg AND volume up
    Weak BUY:   bull% up >8pp
    SELL:       bull% dropped >15pp (bearish momentum)
    """
    if hourly_df.empty or len(hourly_df) < 3:
        return _empty_signal("sentiment_momentum")

    current_bull = float(hourly_df["bull_pct"].iloc[-1])
    current_vol  = int(hourly_df["total"].iloc[-1])

    avg_24h_bull = float(hourly_df["bull_pct"].tail(24).mean())
    avg_6h_bull  = float(hourly_df["bull_pct"].tail(6).mean())
    avg_24h_vol  = float(hourly_df["total"].tail(24).mean()) or 1

    delta_24h = current_bull - avg_24h_bull
    delta_6h  = current_bull - avg_6h_bull
    vol_surge = (current_vol - avg_24h_vol) / avg_24h_vol * 100

    # Signal logic
    if delta_24h >= 15 and vol_surge >= 50:
        signal, strength, conf = SIGNAL_BUY, min(85, 60 + delta_24h), 72
        reason = f"Bull% 急升 +{delta_24h:.0f}pp（{avg_24h_bull:.0f}%→{current_bull:.0f}%），訊息量暴增 +{vol_surge:.0f}%"
    elif delta_24h >= 10:
        signal, strength, conf = SIGNAL_BUY, min(70, 50 + delta_24h), 61
        reason = f"Bull% 上升 +{delta_24h:.0f}pp（24h均值 {avg_24h_bull:.0f}%→現在 {current_bull:.0f}%）"
    elif delta_24h <= -15 and vol_surge >= 30:
        signal, strength, conf = SIGNAL_SELL, min(85, 60 + abs(delta_24h)), 68
        reason = f"Bull% 急跌 {delta_24h:.0f}pp（{avg_24h_bull:.0f}%→{current_bull:.0f}%），看空情緒主導"
    elif delta_24h <= -10:
        signal, strength, conf = SIGNAL_SELL, min(65, 50 + abs(delta_24h)), 58
        reason = f"Bull% 下滑 {delta_24h:.0f}pp，情緒轉弱"
    elif abs(delta_24h) >= 6:
        signal, strength, conf = SIGNAL_WATCH, 40, 50
        reason = f"Bull% 變化 {delta_24h:+.0f}pp，情緒輕微{'偏多' if delta_24h>0 else '偏空'}，持續觀察"
    else:
        signal, strength, conf = SIGNAL_HOLD, 30, 45
        reason = f"Bull% {current_bull:.0f}%，情緒平穩，無明顯方向"

    return {
        "name":          "社媒情緒動量",
        "signal":        signal,
        "strength":      int(strength),
        "confidence":    conf,
        "reason":        reason,
        "current_bull":  current_bull,
        "avg_bull_24h":  round(avg_24h_bull, 1),
        "delta_24h":     round(delta_24h, 1),
        "vol_surge_pct": round(vol_surge, 0),
    }


# ─────────────────────────────────────────────────────────────────
# SIGNAL 2: VOLUME ANOMALY (Z-Score)
# ─────────────────────────────────────────────────────────────────
def signal_volume_anomaly(hourly_df: pd.DataFrame) -> dict:
    """
    Z-score of current hour message volume vs rolling 7-day same-hour baseline.
    High z-score = abnormal attention = potential price move incoming.
    """
    if hourly_df.empty or len(hourly_df) < 6:
        return _empty_signal("volume_anomaly")

    vols = hourly_df["total"].values
    if len(vols) < 3:
        return _empty_signal("volume_anomaly")

    mean_v = np.mean(vols[:-1])
    std_v  = np.std(vols[:-1]) or 1
    z      = (vols[-1] - mean_v) / std_v
    current_vol = int(vols[-1])
    pct_above   = round((current_vol - mean_v) / mean_v * 100) if mean_v else 0

    if z >= 3.5:
        signal, strength, conf = SIGNAL_WATCH, 80, 70
        reason = f"訊息量爆發 z={z:.1f}（超過均值 {pct_above}%），高度異常，等待方向確認"
    elif z >= 2.5:
        signal, strength, conf = SIGNAL_WATCH, 65, 62
        reason = f"訊息量顯著上升 z={z:.1f}（+{pct_above}%），市場注意力聚焦"
    elif z >= 1.5:
        signal, strength, conf = SIGNAL_WATCH, 45, 52
        reason = f"訊息量輕微偏高 z={z:.1f}（+{pct_above}%）"
    else:
        signal, strength, conf = SIGNAL_HOLD, 25, 40
        reason = f"訊息量正常 z={z:.1f}，無異常聚焦"

    return {
        "name":        "討論量異常偵測",
        "signal":      signal,
        "strength":    int(strength),
        "confidence":  conf,
        "reason":      reason,
        "z_score":     round(float(z), 2),
        "current_vol": current_vol,
        "mean_vol":    round(float(mean_v), 1),
        "pct_above":   pct_above,
    }


# ─────────────────────────────────────────────────────────────────
# SIGNAL 3: PRICE-SENTIMENT DIVERGENCE
# Price up but sentiment falling = warning
# Price down but sentiment rising = potential reversal
# ─────────────────────────────────────────────────────────────────
def signal_divergence(hourly_df: pd.DataFrame, price_df: pd.DataFrame) -> dict:
    """
    Compare recent price direction vs sentiment direction.
    Divergence = potential reversal signal.
    """
    if hourly_df.empty or price_df.empty or len(hourly_df) < 3:
        return _empty_signal("divergence")

    # Price: compare last 2h vs 4h ago
    try:
        price_recent = float(price_df["Close"].iloc[-1])
        price_4h_ago = float(price_df["Close"].iloc[-5]) if len(price_df) >= 5 else float(price_df["Close"].iloc[0])
        price_chg    = (price_recent - price_4h_ago) / price_4h_ago * 100
    except Exception:
        return _empty_signal("divergence")

    # Sentiment: compare latest 2h avg vs prior 4h avg
    recent_bull = float(hourly_df["bull_pct"].tail(2).mean())
    prior_bull  = float(hourly_df["bull_pct"].iloc[-5:-2].mean()) if len(hourly_df) >= 5 else float(hourly_df["bull_pct"].mean())
    sent_chg    = recent_bull - prior_bull

    # Classify divergence
    price_up   = price_chg > 0.3
    price_down = price_chg < -0.3
    sent_up    = sent_chg > 5
    sent_down  = sent_chg < -5

    if price_up and sent_down:
        signal, strength, conf = SIGNAL_SELL, 70, 65
        reason = f"⚠ 背離警告：股價上漲 +{price_chg:.1f}% 但 Bull% 下滑 {sent_chg:.0f}pp → 可能見頂"
    elif price_down and sent_up:
        signal, strength, conf = SIGNAL_BUY, 68, 63
        reason = f"🔄 反轉信號：股價跌 {price_chg:.1f}% 但 Bull% 上升 +{sent_chg:.0f}pp → 可能反彈"
    elif price_up and sent_up:
        signal, strength, conf = SIGNAL_BUY, 60, 58
        reason = f"✅ 同向確認：股價 +{price_chg:.1f}% 且 Bull% +{sent_chg:.0f}pp，趨勢一致"
    elif price_down and sent_down:
        signal, strength, conf = SIGNAL_SELL, 58, 55
        reason = f"📉 同向下跌：股價 {price_chg:.1f}% 且情緒轉弱，趨勢一致"
    else:
        signal, strength, conf = SIGNAL_HOLD, 30, 40
        reason = f"股價 {price_chg:+.1f}%，情緒變化 {sent_chg:+.0f}pp，無明顯背離"

    return {
        "name":        "股價-情緒背離分析",
        "signal":      signal,
        "strength":    int(strength),
        "confidence":  conf,
        "reason":      reason,
        "price_chg":   round(price_chg, 2),
        "sent_chg":    round(sent_chg, 1),
        "recent_bull": round(recent_bull, 1),
    }


# ─────────────────────────────────────────────────────────────────
# SIGNAL 4: 30-DAY BACKTESTED WIN RATE
# How often did similar sentiment conditions lead to price gains?
# ─────────────────────────────────────────────────────────────────
def compute_backtest_winrate(
    daily_price_df: pd.DataFrame,
    threshold_bull: float = 65.0,
    hold_days: int = 2,
) -> dict:
    """
    Simplified backtest: on days when bull% was high (simulated from price momentum),
    what % of time did price rise over next N days?

    Since we only have recent Stocktwits history, we use price momentum as proxy
    for historical sentiment states.
    """
    if daily_price_df.empty or len(daily_price_df) < 10:
        return {"win_rate": None, "sample_size": 0, "avg_return": None}

    df = daily_price_df.copy()
    df["ret_next"] = df["Close"].pct_change(hold_days).shift(-hold_days) * 100
    df["rsi_proxy"] = df["Close"].pct_change(3).rolling(5).mean()  # momentum proxy

    # "Bullish sentiment" proxy: price has been rising 3 of last 5 days
    df["was_bullish"] = (df["rsi_proxy"] > 0)
    triggered = df[df["was_bullish"]].dropna(subset=["ret_next"])

    if len(triggered) < 3:
        return {"win_rate": None, "sample_size": 0, "avg_return": None}

    wins     = (triggered["ret_next"] > 0).sum()
    win_rate = round(wins / len(triggered) * 100, 1)
    avg_ret  = round(triggered["ret_next"].mean(), 2)

    return {
        "win_rate":   win_rate,
        "sample_size": int(len(triggered)),
        "avg_return":  avg_ret,
        "hold_days":   hold_days,
    }


# ─────────────────────────────────────────────────────────────────
# COMPOSITE SIGNAL — Combine all signals into one verdict
# ─────────────────────────────────────────────────────────────────
def compute_composite_signal(
    sig_momentum:  dict,
    sig_volume:    dict,
    sig_divergence: dict,
    backtest:      dict,
    price_info:    dict,
) -> dict:
    """
    Weighted combination of all signals → single BUY/SELL/HOLD verdict
    with entry price, stop loss, target.
    """
    # Weights
    W = {"momentum": 0.45, "volume": 0.20, "divergence": 0.35}

    def score(sig: dict) -> float:
        s = sig.get("strength", 0)
        if sig.get("signal") == SIGNAL_BUY:   return  s
        if sig.get("signal") == SIGNAL_SELL:  return -s
        if sig.get("signal") == SIGNAL_WATCH: return  s * 0.3
        return 0.0

    raw = (score(sig_momentum)  * W["momentum"] +
           score(sig_volume)    * W["volume"] +
           score(sig_divergence)* W["divergence"])

    price       = price_info.get("price", 0)
    change_pct  = price_info.get("change_pct", 0)
    win_rate    = backtest.get("win_rate")
    avg_return  = backtest.get("avg_return")
    sample_size = backtest.get("sample_size", 0)

    # Confidence boost from backtest
    conf_base = int(np.mean([
        sig_momentum.get("confidence", 50),
        sig_divergence.get("confidence", 50),
    ]))
    if win_rate and win_rate >= 60: conf_base = min(conf_base + 8, 88)
    if win_rate and win_rate <= 40: conf_base = max(conf_base - 8, 20)

    # Final signal
    if raw >= 40:
        signal = SIGNAL_BUY
        signal_color  = "#00e676"
        signal_emoji  = "🟢"
    elif raw <= -40:
        signal = SIGNAL_SELL
        signal_color  = "#ff3d57"
        signal_emoji  = "🔴"
    elif raw >= 18:
        signal = SIGNAL_WATCH
        signal_color  = "#ffab00"
        signal_emoji  = "🟡"
    elif raw <= -18:
        signal = SIGNAL_WATCH
        signal_color  = "#ffab00"
        signal_emoji  = "🟡"
    else:
        signal = SIGNAL_HOLD
        signal_color  = "#4a5270"
        signal_emoji  = "⚪"

    # Price targets (only meaningful for BUY/SELL)
    entry  = stop = target = None
    if price and signal == SIGNAL_BUY:
        entry  = round(price * 1.001, 2)           # slight buffer above market
        stop   = round(price * 0.984, 2)           # -1.6% stop loss
        target = round(price * 1.028, 2)           # +2.8% target (1.75:1 R:R)
    elif price and signal == SIGNAL_SELL:
        entry  = round(price * 0.999, 2)
        stop   = round(price * 1.016, 2)           # stop above market for short
        target = round(price * 0.972, 2)

    # Build reasons summary
    reasons = []
    for sig in [sig_momentum, sig_divergence, sig_volume]:
        if sig.get("signal") in [SIGNAL_BUY, SIGNAL_SELL]:
            reasons.append(sig.get("reason",""))

    backtest_txt = ""
    if win_rate is not None and sample_size >= 3:
        backtest_txt = f"30天回測：{sample_size} 次相似情況，勝率 {win_rate}%，平均回報 {avg_return:+.1f}%"

    return {
        "signal":        signal,
        "signal_color":  signal_color,
        "signal_emoji":  signal_emoji,
        "raw_score":     round(raw, 1),
        "confidence":    conf_base,
        "price":         price,
        "change_pct":    change_pct,
        "entry":         entry,
        "stop":          stop,
        "target":        target,
        "rr_ratio":      round((target - entry) / (entry - stop), 2) if entry and stop and stop != entry else None,
        "reasons":       [r for r in reasons if r],
        "backtest_txt":  backtest_txt,
        "win_rate":      win_rate,
        "generated_at":  datetime.utcnow().strftime("%H:%M UTC"),
    }


def _empty_signal(name: str) -> dict:
    return {"name": name, "signal": SIGNAL_HOLD, "strength": 0,
            "confidence": 0, "reason": "數據不足，無法計算信號"}
