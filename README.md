# MarketIntel — 社媒輿情 Force Graph 分析系統

> 學術研究用途 · Streamlit Cloud 穩定運行 · 不需要 X/Twitter API

## 功能

| Tab | 功能 |
|-----|------|
| ⚡ 即時總覽 | AI 結論先行 · Force Graph 關聯網絡 · Z-Score 異常偵測 · 情緒分析 |
| 📅 30天歷史 | 討論量 × 股價疊加圖 · 峰值事件偵測 · 週期性規律 |
| 📈 股票關聯 | Pearson 相關係數 · 時間滯後分析 · 散點回測 |

## 數據來源（不需要 X/Twitter API）

| 來源 | 用途 | 免費 |
|------|------|------|
| Google Trends (`pytrends`) | 搜尋熱度趨勢 | ✅ |
| Stocktwits 公開 API | 股票投資者討論 + 情緒 | ✅ |
| Reddit 公開 JSON API | 深度討論輿情 | ✅ |
| yFinance | 股價歷史數據 | ✅ |
| Groq AI | 自動生成市場洞察 | ✅ 免費額度 |

## 部署到 Streamlit Cloud

1. Fork 此 repo 到你的 GitHub
2. 前往 [share.streamlit.io](https://share.streamlit.io)
3. 選擇 repo，Main file path: `app.py`
4. 在 App Settings → Secrets 填入：
```toml
GROQ_API_KEY = "gsk_..."
```
5. Deploy ✅

## 本地開發

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# 填入你的 GROQ_API_KEY
streamlit run app.py
```

## 架構

```
marketintel/
├── app.py                  # 主程式入口
├── config.py               # 所有配置常數
├── requirements.txt
├── .streamlit/
│   ├── config.toml         # 主題設定
│   └── secrets.toml        # API Keys（本地）
├── data/
│   ├── fetcher.py          # 數據抓取（Trends/Stocktwits/Reddit/yFinance）
│   ├── analyzer.py         # 分析引擎（Z-Score/相關性/Force Graph/情緒）
│   └── groq_ai.py          # Groq AI 洞察生成
├── components/
│   └── charts.py           # 所有 Plotly 圖表
└── utils/
    └── css.py              # CSS 注入 + HTML 組件
```

## 注意事項

- Google Trends 有限流保護，每次掃描間隔建議 > 30 秒
- Stocktwits 公開 API 無需認證，但有速率限制
- 所有 API 呼叫有 fallback 模擬數據，即使受限也能正常展示
- Groq API 免費額度每日 14,400 請求，足夠使用
