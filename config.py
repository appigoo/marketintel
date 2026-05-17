# config.py — MarketIntel Central Configuration

# ── COLOUR SYSTEM (matches HTML preview) ──────────────────────────────────────
COLORS = {
    "bg":       "#07080a",
    "ink":      "#0e1015",
    "card":     "#12151b",
    "line":     "#1c2030",
    "dim":      "#4a5270",
    "body":     "#8892aa",
    "bright":   "#d4daf0",
    "white":    "#eef2ff",
    "bull":     "#00e676",
    "bear":     "#ff3d57",
    "warn":     "#ffab00",
    "ice":      "#00b8ff",
    "lav":      "#b388ff",
}

# Keyword → colour mapping (consistent across all charts)
KW_COLORS = {
    "$TSLA":     "#00b8ff",
    "TSLA":      "#00b8ff",
    "TESLA":     "#ffab00",
    "ELON MUSK": "#b388ff",
    "ELON":      "#b388ff",
    "SPCX":      "#00e676",
}

# Community / cluster colours
CLUSTER_COLORS = ["#00b8ff", "#b388ff", "#ff3d57", "#00e676", "#ffab00"]

# ── STREAMLIT PAGE CONFIG ─────────────────────────────────────────────────────
PAGE_CONFIG = dict(
    page_title="MarketIntel — 社媒輿情分析",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── DATA FETCH SETTINGS ───────────────────────────────────────────────────────
PYTRENDS_TIMEOUT   = (10, 25)   # (connect, read) seconds
PYTRENDS_RETRIES   = 2
REDDIT_LIMIT       = 100        # posts per subreddit per keyword
STOCKTWITS_LIMIT   = 30         # messages per symbol
NEWS_PAGE_SIZE     = 20
YFINANCE_TIMEOUT   = 10

STOCKTWITS_SUBREDDITS = ["wallstreetbets", "stocks", "investing", "options", "SecurityAnalysis"]

# ── CACHE TTLs ────────────────────────────────────────────────────────────────
TTL_TRENDS    = 3600      # 1 hour
TTL_REDDIT    = 1800      # 30 min
TTL_STOCKTWIT = 900       # 15 min
TTL_YFINANCE  = 300       # 5 min
TTL_GROQ      = 1800      # 30 min

# ── ANALYSIS THRESHOLDS ───────────────────────────────────────────────────────
ZSCORE_RED    = 3.5
ZSCORE_YELLOW = 2.0
COOCCUR_MIN   = 5         # minimum shared appearances to form an edge
STRONG_CORR   = 0.6
WEAK_CORR     = 0.35

# ── GROQ ─────────────────────────────────────────────────────────────────────
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_TOKENS  = 600

# ── DEFAULT KEYWORDS ─────────────────────────────────────────────────────────
DEFAULT_KEYWORDS = ["TSLA", "TESLA", "ELON MUSK", "SPCX"]
DEFAULT_STOCKS   = {"TSLA": "TSLA", "TESLA": "TSLA", "ELON MUSK": "TSLA", "SPCX": "SPCX"}

# Keyword → Stocktwits symbol mapping
STOCKTWITS_MAP = {
    "TSLA":      "TSLA",
    "$TSLA":     "TSLA",
    "TESLA":     "TSLA",
    "ELON MUSK": "TSLA",
    "SPCX":      "SPCX",
}

# Keyword → stock ticker for price correlation
PRICE_MAP = {
    "TSLA":      "TSLA",
    "$TSLA":     "TSLA",
    "TESLA":     "TSLA",
    "ELON MUSK": "TSLA",
    "ELON":      "TSLA",
    "SPCX":      "SPCX",
}

# Google Trends geo
TRENDS_GEO = ""   # worldwide
