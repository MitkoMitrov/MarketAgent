"""
Comprehensive Finnhub data fetcher for market analysis.
Collects: quotes, news, company profile and basic financials, and saves a snapshot JSON.

Run from the project root:  python -m finnhub_scripts.fetch_and_store
"""
import os
import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from engine.finnhub_client import SYMBOLS, get_client
from engine.news_fetcher import fetch_company_news, fetch_market_news

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "snapshots")


def fetch_quote(symbol):
    """Fetch real-time quote data."""
    try:
        return get_client().quote(symbol)
    except Exception as e:
        print(f"⚠️ Error fetching quote for {symbol}: {e}")
        return {}


def fetch_company_profile(symbol):
    """Fetch company profile (name, industry, market cap, etc.)."""
    try:
        return get_client().company_profile2(symbol=symbol)
    except Exception as e:
        print(f"⚠️ Error fetching profile for {symbol}: {e}")
        return {}


def fetch_basic_financials(symbol):
    """Fetch key financial metrics."""
    try:
        return get_client().company_basic_financials(symbol, 'all').get('metric', {})
    except Exception as e:
        print(f"⚠️ Error fetching financials for {symbol}: {e}")
        return {}


def determine_market_session():
    """Determine current US market session from New York time."""
    hour = datetime.now(ZoneInfo("America/New_York")).hour
    if 4 <= hour < 9:
        return "pre-market"
    elif 9 <= hour < 16:
        return "regular-hours"
    elif 16 <= hour < 20:
        return "after-hours"
    return "closed"


def build_snapshot():
    """Build comprehensive market snapshot."""
    print("📥 Fetching market data from Finnhub...")

    snapshot = {
        "snapshot_time": datetime.now(timezone.utc).isoformat(),
        "market_session": determine_market_session(),
        "stocks": {},
        "news": [],
        "market_news": []
    }

    for symbol in SYMBOLS:
        print(f"  → Fetching {symbol}...")

        quote = fetch_quote(symbol)
        profile = fetch_company_profile(symbol)
        financials = fetch_basic_financials(symbol)

        snapshot["stocks"][symbol] = {
            "price": quote.get("c", 0),
            "change": quote.get("d", 0),
            "change_percent": quote.get("dp", 0),
            "high": quote.get("h", 0),
            "low": quote.get("l", 0),
            "open": quote.get("o", 0),
            "previous_close": quote.get("pc", 0),
            "name": profile.get("name", symbol),
            "industry": profile.get("finnhubIndustry", "N/A"),
            "market_cap": profile.get("marketCapitalization", 0),
            "pe_ratio": financials.get("peBasicExclExtraTTM", None),
            "52_week_high": financials.get("52WeekHigh", None),
            "52_week_low": financials.get("52WeekLow", None),
            "beta": financials.get("beta", None),
            "volume": financials.get("10DayAverageTradingVolume", None),
        }

        for item in fetch_company_news(symbol):
            snapshot["news"].append({
                "symbol": symbol,
                "headline": item["headline"],
                "source": item["source"],
                "summary": item["summary"],
                "url": item["url"],
                "timestamp": item["timestamp"],
            })

    for item in fetch_market_news(hours=24):
        snapshot["market_news"].append({
            "headline": item["headline"],
            "source": item["source"],
            "summary": item["summary"],
            "url": item["url"],
            "timestamp": item["timestamp"],
        })

    return snapshot


def main():
    """Main execution."""
    snapshot = build_snapshot()

    os.makedirs(DATA_DIR, exist_ok=True)
    data_file = os.path.join(DATA_DIR, f"market_snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    with open(data_file, "w", encoding="utf-8") as f:
        json.dump(snapshot, indent=2, fp=f)

    print(f"\n✅ Market snapshot saved to {data_file}")
    print(f"   Stocks: {len(snapshot['stocks'])}")
    print(f"   News items: {len(snapshot['news'])}")
    print(f"   Market news items (24h): {len(snapshot['market_news'])}")


if __name__ == "__main__":
    main()
