# data/groq_ai.py — Groq AI signal narrative generator
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json, re
import streamlit as st

try:
    from groq import Groq
    GROQ_OK = True
except Exception:
    GROQ_OK = False

GROQ_MODEL  = "llama-3.3-70b-versatile"
GROQ_TOKENS = 500

def _client():
    key = st.secrets.get("GROQ_API_KEY","")
    return Groq(api_key=key) if key and GROQ_OK else None

@st.cache_data(ttl=1200, show_spinner=False)
def generate_signal_narrative(
    ticker:    str,
    composite: dict,
    sig_mom:   dict,
    sig_vol:   dict,
    sig_div:   dict,
    backtest:  dict,
    top_msgs:  tuple,   # tuple of (body, sentiment) for top 5 messages
) -> dict:
    """Generate AI narrative for the composite signal."""
    client = _client()
    if not client:
        return _rule_narrative(ticker, composite, sig_mom, sig_vol, sig_div, backtest)

    signal   = composite.get("signal","HOLD")
    price    = composite.get("price",0)
    entry    = composite.get("entry")
    stop     = composite.get("stop")
    target   = composite.get("target")
    conf     = composite.get("confidence",50)
    win_rate = backtest.get("win_rate")
    bull_pct = sig_mom.get("current_bull",50)
    delta    = sig_mom.get("delta_24h",0)
    z        = sig_vol.get("z_score",0)
    msgs_txt = "\n".join([f"- [{s}] {b[:80]}" for b,s in top_msgs[:5]])

    prompt = f"""你是一個香港散戶用的股票信號分析師。用繁體中文，簡潔直接。

股票：{ticker}  現價：${price}  信號：{signal}  置信度：{conf}%
Bull情緒：{bull_pct}%（vs 24h均值變化：{delta:+.0f}pp）
訊息量異常：z={z:.1f}
{'入場：$'+str(entry)+'  止損：$'+str(stop)+'  目標：$'+str(target) if entry else ''}
{'30天勝率：'+str(win_rate)+'%' if win_rate else ''}

最新市場討論樣本：
{msgs_txt}

請輸出JSON（不加markdown）：
{{
  "one_liner": "一句話信號結論（20字內）",
  "why": "為什麼出現這個信號（2句，含具體數字）",
  "risk": "主要風險（1句）",
  "watch": "需要監察的指標（1句）"
}}"""

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role":"user","content":prompt}],
            max_tokens=GROQ_TOKENS, temperature=0.2,
        )
        raw = resp.choices[0].message.content.strip()
        cleaned = re.sub(r"```[a-z]*","",raw).strip()
        data = json.loads(cleaned)
        for k in ["one_liner","why","risk","watch"]:
            if k not in data: raise ValueError(f"Missing {k}")
        return data
    except Exception:
        return _rule_narrative(ticker, composite, sig_mom, sig_vol, sig_div, backtest)

def _rule_narrative(ticker, composite, sig_mom, sig_vol, sig_div, backtest) -> dict:
    signal   = composite.get("signal","HOLD")
    bull_pct = sig_mom.get("current_bull",50)
    delta    = sig_mom.get("delta_24h",0)
    z        = sig_vol.get("z_score",0)
    win_rate = backtest.get("win_rate")
    price    = composite.get("price",0)
    entry    = composite.get("entry")
    stop     = composite.get("stop")
    target   = composite.get("target")

    if signal == "BUY":
        one_liner = f"{ticker} 社媒情緒看漲，短線買入信號"
        why = f"Stocktwits Bull% 升至 {bull_pct:.0f}%，較 24h 均值高 {delta:+.0f}pp；訊息量異常指數 z={z:.1f}。"
        risk = f"若 Bull% 回落至 {max(bull_pct-12,45):.0f}% 以下，信號失效，需止損。"
    elif signal == "SELL":
        one_liner = f"{ticker} 情緒轉空，考慮減倉或做空"
        why = f"Stocktwits Bull% 跌至 {bull_pct:.0f}%，較 24h 均值低 {abs(delta):.0f}pp；市場情緒明顯轉弱。"
        risk = "社媒情緒反轉快，若 Bull% 重回升軌需及時止損。"
    elif signal == "WATCH":
        one_liner = f"{ticker} 訊息量異常，等待方向確認"
        why = f"訊息量 z-score={z:.1f}，遠高於正常水平，但 Bull%={bull_pct:.0f}% 方向未明確。"
        risk = "異常訊息量可能是噪音或大事件前兆，方向未確認前勿重倉。"
    else:
        one_liner = f"{ticker} 無明顯信號，繼續觀望"
        why = f"Bull%={bull_pct:.0f}%，訊息量 z={z:.1f}，均在正常範圍，無明顯買賣機會。"
        risk = "市場平靜期等待突破，設置警報於關鍵價位。"

    wr_txt = f"30天相似情況勝率 {win_rate}%" if win_rate else "歷史數據不足"
    watch  = f"監察 Bull% 是否維持 >{max(bull_pct-5,50):.0f}%，訊息量是否持續，以及 {ticker} 能否守住 ${stop or price:.2f}。"

    return {"one_liner": one_liner, "why": why + f"（{wr_txt}）", "risk": risk, "watch": watch}
