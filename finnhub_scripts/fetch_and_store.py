import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import finnhub

# -----------------------------
# Load environment
# -----------------------------
load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")

# Initialize Finnhub client
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

# -----------------------------
# Settings
# -----------------------------
SYMBOLS = ["TSLA", "AMD", "TTWO", "GOOG", "NVDA", "MSTR"]  # You can add more

# Get project root and create data directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "snapshots")
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, f"market_snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")

# -----------------------------
# Helper: fetch quote
# -----------------------------
def fetch_quote(symbol):
    return finnhub_client.quote(symbol)

# -----------------------------
# Helper: fetch news (last 7 days)
# -----------------------------
def fetch_news(symbol):
    to_date = datetime.now(timezone.utc)
    from_date = to_date - timedelta(days=7)
    return finnhub_client.company_news(
        symbol,
        _from=from_date.strftime("%Y-%m-%d"),
        to=to_date.strftime("%Y-%m-%d")
    )

# -----------------------------
# Build snapshot
# -----------------------------
snapshot = {
    "snapshot_time": datetime.now(timezone.utc).isoformat(),
    "market_session": "pre-market",  # you can adjust dynamically later
    "stocks": {},
    "news": []
}

for symbol in SYMBOLS:
    quote = fetch_quote(symbol)
    snapshot["stocks"][symbol] = {
        "price": quote["c"],
        "change_percent": quote["dp"],
        "high": quote["h"],
        "low": quote["l"],
        "open": quote["o"],
        "previous_close": quote["pc"]
    }
    news_items = fetch_news(symbol)
    snapshot["news"].extend([
        {
            "symbol": symbol,
            "headline": item["headline"],
            "source": item["source"],
            "summary": item.get("summary", ""),
            "timestamp": item["datetime"]
        } for item in news_items
    ])

# -----------------------------
# Save to txt file (JSON inside)
# -----------------------------
with open(DATA_FILE, "w", encoding="utf-8") as f:
    f.write(json.dumps(snapshot, indent=2))

print(f"✅ Market snapshot saved to {DATA_FILE}")
