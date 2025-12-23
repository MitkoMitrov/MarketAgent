"""
Comprehensive Finnhub data fetcher for market analysis.
Collects: quotes, news, company profile, basic financials, and sentiment.
"""
import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import finnhub

# Load environment
load_dotenv()
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
if not FINNHUB_API_KEY:
    raise ValueError("FINNHUB_API_KEY not found in environment variables")

# Initialize Finnhub client
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

# Settings
SYMBOLS = ["TSLA", "AMD", "TTWO", "GOOG", "NVDA", "MSTR"]

# Get project root and create data directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "snapshots")
os.makedirs(DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(DATA_DIR, f"market_snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")


def fetch_quote(symbol):
    """Fetch real-time quote data."""
    try:
        return finnhub_client.quote(symbol)
    except Exception as e:
        print(f"⚠️ Error fetching quote for {symbol}: {e}")
        return {}


def fetch_company_profile(symbol):
    """Fetch company profile (name, industry, market cap, etc.)."""
    try:
        return finnhub_client.company_profile2(symbol=symbol)
    except Exception as e:
        print(f"⚠️ Error fetching profile for {symbol}: {e}")
        return {}


def fetch_basic_financials(symbol):
    """Fetch key financial metrics."""
    try:
        result = finnhub_client.company_basic_financials(symbol, 'all')
        return result.get('metric', {})
    except Exception as e:
        print(f"⚠️ Error fetching financials for {symbol}: {e}")
        return {}


def fetch_news(symbol, days=7):
    """Fetch recent company news."""
    try:
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=days)
        news = finnhub_client.company_news(
            symbol,
            _from=from_date.strftime("%Y-%m-%d"),
            to=to_date.strftime("%Y-%m-%d")
        )
        # Sort by timestamp, most recent first, limit to top 5
        news = sorted(news, key=lambda x: x.get('datetime', 0), reverse=True)[:5]
        return news
    except Exception as e:
        print(f"⚠️ Error fetching news for {symbol}: {e}")
        return []


def determine_market_session():
    """Determine current market session based on time."""
    from datetime import datetime
    now = datetime.now()
    hour = now.hour
    
    # US market hours (ET): Pre-market 4-9:30, Regular 9:30-16, After-hours 16-20
    # Simplified logic assuming local time is ET or close
    if 4 <= hour < 9:
        return "pre-market"
    elif 9 <= hour < 16:
        return "regular-hours"
    elif 16 <= hour < 20:
        return "after-hours"
    else:
        return "closed"


def build_snapshot():
    """Build comprehensive market snapshot."""
    print("📥 Fetching market data from Finnhub...")
    
    snapshot = {
        "snapshot_time": datetime.now(timezone.utc).isoformat(),
        "market_session": determine_market_session(),
        "stocks": {},
        "news": []
    }
    
    for symbol in SYMBOLS:
        print(f"  → Fetching {symbol}...")
        
        quote = fetch_quote(symbol)
        profile = fetch_company_profile(symbol)
        financials = fetch_basic_financials(symbol)
        news = fetch_news(symbol)
        
        # Curate most valuable data points
        snapshot["stocks"][symbol] = {
            # Price data
            "price": quote.get("c", 0),
            "change": quote.get("d", 0),
            "change_percent": quote.get("dp", 0),
            "high": quote.get("h", 0),
            "low": quote.get("l", 0),
            "open": quote.get("o", 0),
            "previous_close": quote.get("pc", 0),
            
            # Company info
            "name": profile.get("name", symbol),
            "industry": profile.get("finnhubIndustry", "N/A"),
            "market_cap": profile.get("marketCapitalization", 0),
            
            # Key financials (selecting most relevant)
            "pe_ratio": financials.get("peBasicExclExtraTTM", None),
            "52_week_high": financials.get("52WeekHigh", None),
            "52_week_low": financials.get("52WeekLow", None),
            "beta": financials.get("beta", None),
            "volume": financials.get("10DayAverageTradingVolume", None),
        }
        
        # Add news
        for item in news:
            snapshot["news"].append({
                "symbol": symbol,
                "headline": item.get("headline", ""),
                "source": item.get("source", ""),
                "summary": item.get("summary", ""),
                "url": item.get("url", ""),
                "timestamp": item.get("datetime", 0)
            })
    
    return snapshot


def main():
    """Main execution."""
    snapshot = build_snapshot()
    
    # Save to file
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, indent=2, fp=f)
    
    print(f"\n✅ Market snapshot saved to {DATA_FILE}")
    print(f"   Stocks: {len(snapshot['stocks'])}")
    print(f"   News items: {len(snapshot['news'])}")


if __name__ == "__main__":
    main()
