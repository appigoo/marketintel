# data/groq_ai.py — Groq AI insight generation

from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import streamlit as st
from config import GROQ_MODEL, GROQ_TOKENS, TTL_GROQ

try:
    from groq import Groq
    GROQ_OK = True
except Exception:
    GROQ_OK = False


def _get_client():
    api_key = st.secrets.get("GROQ_API_KEY", "")
    if not api_key or not GROQ_OK:
        return None
    return Groq(api_key=api_key)


@st.cache_data(ttl=TTL_GROQ, show_spinner=False)
def generate_insight(
    keywords:   tuple[str, ...],
    sentiments: dict,      # {kw: {bull_pct, bear_pct, compound}}
    z_scores:   dict,      # {kw: float}
    corr_data:  dict,      # {kw: {best_r, best_lag}}
    ai_score:   int,
    lang:       str = "zh-TW",
) -> dict:
    """
    Returns {
        "headline": str,
        "sub": str,
        "summary": str,
        "actions": [{"icon", "text"}],
        "signals": [{"icon", "text", "cls"}],
    }
    """
    client = _get_client()
    if client is None:
        return _fallback_insight(keywords, sentiments, z_scores, corr_data, ai_score)

    context = _build_context(keywords, sentiments, z_scores, corr_data, ai_score)
    prompt  = _build_prompt(context, lang)

    try:
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=GROQ_TOKENS,
            temperature=0.3,
        )
        raw = resp.choices[0].message.content.strip()
        return _parse_response(raw, keywords, sentiments, z_scores, ai_score)
    except Exception as e:
        st.warning(f"Groq AI 暫時不可用，使用自動分析。({e})")
        return _fallback_insight(keywords, sentiments, z_scores, corr_data, ai_score)


# ── PROMPT BUILDER ──────────────────────────────────────────────────────────
def _build_context(keywords, sentiments, z_scores, corr_data, ai_score) -> str:
    lines = [f"AI分析評分: {ai_score}/100\n"]
    for kw in keywords:
        s = sentiments.get(kw, {})
        z = z_scores.get(kw, 0)
        c = corr_data.get(kw, {})
        lines.append(
            f"[{kw}] 看漲={s.get('bull_pct',50):.0f}% 看跌={s.get('bear_pct',25):.0f}% "
            f"z-score={z:.1f} 最佳相關r={c.get('best_r',0):.2f} 領先={c.get('best_lag',0)}天"
        )
    return "\n".join(lines)


def _build_prompt(context: str, lang: str) -> str:
    return f"""你是一個金融社媒輿情分析師，請根據以下數據生成分析報告（繁體中文）。

數據：
{context}

請按以下JSON格式輸出（不要加```json標記）：
{{
  "headline": "一句話核心結論（15字內，用於大標題）",
  "sub": "2-3句補充說明（含具體數字和原因）",
  "summary": "3-4句AI洞察（分析關聯性、風險、建議關注點）",
  "actions": [
    {{"icon": "🎯", "text": "操作建議一"}},
    {{"icon": "⚠️", "text": "風險提示"}},
    {{"icon": "👁", "text": "監察重點"}}
  ],
  "signals": [
    {{"icon": "🚀", "text": "信號描述", "cls": "sg-bull"}},
    {{"icon": "⚡", "text": "信號描述", "cls": "sg-warn"}}
  ]
}}

cls 只能用：sg-bull（看漲）、sg-bear（看跌）、sg-warn（警告）、sg-ice（中性/資訊）、sg-lav（特殊）"""


def _parse_response(raw: str, keywords, sentiments, z_scores, ai_score) -> dict:
    import json, re
    try:
        # Strip any markdown fences
        cleaned = re.sub(r"```[a-z]*", "", raw).strip()
        data = json.loads(cleaned)
        # Validate required keys
        for key in ["headline", "sub", "summary", "actions", "signals"]:
            if key not in data:
                raise ValueError(f"Missing key: {key}")
        return data
    except Exception:
        return _fallback_insight(keywords, sentiments, z_scores, {}, ai_score)


# ── FALLBACK (rule-based, no AI needed) ─────────────────────────────────────
def _fallback_insight(keywords, sentiments, z_scores, corr_data, ai_score) -> dict:
    # Find highest z-score keyword
    top_kw  = max(z_scores, key=z_scores.get) if z_scores else (keywords[0] if keywords else "TSLA")
    top_z   = z_scores.get(top_kw, 0)
    top_s   = sentiments.get(top_kw, {})
    bull    = top_s.get("bull_pct", 55)
    bear    = top_s.get("bear_pct", 25)

    # Headline
    if top_z >= 3.5:
        headline = f"{top_kw} 討論量異常爆發"
    elif bull > 65:
        headline = f"市場情緒偏向看漲"
    elif bear > 50:
        headline = f"市場情緒轉向看跌"
    else:
        headline = f"市場觀望，注意力分散"

    # Sub
    sub_parts = []
    for kw in keywords[:3]:
        z = z_scores.get(kw, 0)
        s = sentiments.get(kw, {})
        b = s.get("bull_pct", 50)
        if z > 2:
            sub_parts.append(f"<strong>{kw}</strong> 討論量急升（z={z:.1f}），情緒 {b:.0f}% 看漲")
        else:
            sub_parts.append(f"<strong>{kw}</strong> 情緒 {b:.0f}% 看漲，熱度平穩")
    sub = "。".join(sub_parts) + "。"

    # Summary
    best_kw = keywords[0] if keywords else "TSLA"
    best_r  = corr_data.get(best_kw, {}).get("best_r", 0)
    summary = (
        f"根據多源數據分析，<strong>{top_kw}</strong> 是當前最活躍話題。"
        f"{'社媒討論量與股價相關性顯著（r=' + str(round(best_r,2)) + '），具備預測價值。' if abs(best_r) > 0.4 else '社媒信號與股價相關性尚待觀察。'}"
        f"建議重點監測 z-score 超過 3 的異常爆發事件，並結合股價走勢確認信號有效性。"
    )

    # Signals
    signals = []
    for kw in keywords:
        z = z_scores.get(kw, 0)
        s = sentiments.get(kw, {})
        b = s.get("bull_pct", 50)
        if z >= 3.5:
            signals.append({"icon": "⚡", "text": f"{kw} 異常爆發 z={z:.1f}", "cls": "sg-warn"})
        elif b > 65:
            signals.append({"icon": "🚀", "text": f"{kw} 看漲情緒 {b:.0f}%", "cls": "sg-bull"})
        elif b < 40:
            signals.append({"icon": "🔻", "text": f"{kw} 情緒偏弱", "cls": "sg-bear"})
        else:
            signals.append({"icon": "🔵", "text": f"{kw} 情緒中性", "cls": "sg-ice"})

    actions = [
        {"icon": "🎯", "text": f"重點監測 <strong>{top_kw}</strong> 相關新聞持續性"},
        {"icon": "⚠️", "text": "z-score 超過 3.5 時設價格警報"},
        {"icon": "👁",  "text": "結合 yFinance 股價確認社媒信號"},
    ]

    return {
        "headline": headline,
        "sub":      sub,
        "summary":  summary,
        "actions":  actions,
        "signals":  signals,
    }
