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
SYMBOLS = ["QQQ", "TSLA", "AMD", "GOOG", "NVDA", "MSTR", "SMCI"]

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


def fetch_news(symbol, days=1):
    """Fetch recent company news (default: today), return up to 10 most recent."""
    try:
        to_date = datetime.now(timezone.utc)
        from_date = to_date - timedelta(days=days)
        news = finnhub_client.company_news(
            symbol,
            _from=from_date.strftime("%Y-%m-%d"),
            to=to_date.strftime("%Y-%m-%d")
        )
        news = sorted(news, key=lambda x: x.get('datetime', 0), reverse=True)[:10]
        return news
    except Exception as e:
        print(f"⚠️ Error fetching news for {symbol}: {e}")
        return []

# --- Market news relevance filtering helpers ---
def _contains_any(text: str, terms) -> bool:
    if not text:
        return False
    tl = text.lower()
    return any(t in tl for t in terms)

_POSITIVE_KEYWORDS = {
    # Macro & indices
    'gdp', 'cpi', 'pce', 'inflation', 'unemployment', 'jobs report', 'payrolls', 'ism', 'pmi',
    'fomc', 'fed', 'interest rate', 'rates', 'yields', 'treasury', 'bond', 'recession',
    's&p', 'sp500', 's&p 500', 'nasdaq', 'dow', 'vix', 'volatility',
    # Corporate actions & market events
    'earnings', 'guidance', 'revenue', 'eps', 'dividend', 'buyback', 'merger', 'acquisition', 'deal',
    'ipo', 'spac', 'antitrust', 'regulator', 'sec', 'doj', 'lawsuit', 'settlement', 'recall',
    'upgrade', 'downgrade', 'price target', 'outlook',
    # Sectors & assets
    'semiconductor', 'chip', 'ai', 'cloud', 'software', 'cybersecurity', 'energy', 'opec',
    'oil', 'gas', 'wti', 'brent', 'gold', 'silver', 'copper', 'commodities',
    'crypto', 'bitcoin', 'ethereum'
}

_NEGATIVE_KEYWORDS = {
    # Lifestyle / personal finance / career advice
    'how to', 'advice', 'tips', 'beginners', 'job seeker', 'career', 'resume', 'interview',
    'linkedin', 'years old', 'year-old', 'ice cream', 'home ', 'real estate tips', 'retire',
    'retirement', '401(k)', 'credit score', 'save money', 'budget', 'debt payoff', 'student loan',
    'frugal', 'side hustle', 'parents', 'kids', 'family', 'holiday gifts'
}


def _mentions_watchlist(text: str, symbols) -> bool:
    if not text:
        return False
    tl = text.upper()
    for sym in symbols:
        if sym in tl:
            return True
    return any(k in tl for k in ['S&P', 'NASDAQ', 'DOW'])


def _is_relevant_market_news(item: dict, symbols) -> bool:
    """Heuristic relevance check for market news.
    Keep if mentions watchlist symbols/indices or contains market/macro/corporate action keywords,
    and does not contain lifestyle/personal-finance terms.
    """
    headline = item.get('headline', '') or ''
    summary = item.get('summary', '') or ''
    related = item.get('related', '') or ''  # comma-separated tickers when present

    if _contains_any(headline, _NEGATIVE_KEYWORDS) or _contains_any(summary, _NEGATIVE_KEYWORDS):
        return False

    if related:
        rel_syms = {s.strip().upper() for s in related.split(',') if s.strip()}
        if rel_syms.intersection(set(symbols)):
            return True

    if _mentions_watchlist(headline, symbols) or _mentions_watchlist(summary, symbols):
        return True

    if _contains_any(headline, _POSITIVE_KEYWORDS) or _contains_any(summary, _POSITIVE_KEYWORDS):
        return True

    return False


def fetch_market_news(hours=24):
    """Fetch general market news for the past `hours` and keep market-relevant items only."""
    try:
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(hours=hours)

        general_news = finnhub_client.general_news('general', min_id=0)
        recent = [
            item for item in general_news
            if item.get('datetime', 0) >= int(cutoff.timestamp())
        ]
        recent = sorted(recent, key=lambda x: x.get('datetime', 0), reverse=True)
        filtered = [item for item in recent if _is_relevant_market_news(item, SYMBOLS)]
        return filtered
    except Exception as e:
        print(f"⚠️ Error fetching general market news: {e}")
        return []


def determine_market_session():
    """Determine current market session based on time."""
    now = datetime.now()
    hour = now.hour
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
        "news": [],
        "market_news": []
    }

    for symbol in SYMBOLS:
        print(f"  → Fetching {symbol}...")

        quote = fetch_quote(symbol)
        profile = fetch_company_profile(symbol)
        financials = fetch_basic_financials(symbol)
        news = fetch_news(symbol)

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

        for item in news:
            snapshot["news"].append({
                "symbol": symbol,
                "headline": item.get("headline", ""),
                "source": item.get("source", ""),
                "summary": item.get("summary", ""),
                "url": item.get("url", ""),
                "timestamp": item.get("datetime", 0)
            })


    market_news = fetch_market_news(hours=24)
    for item in market_news:
        snapshot["market_news"].append({
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

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(snapshot, indent=2, fp=f)

    print(f"\n✅ Market snapshot saved to {DATA_FILE}")
    print(f"   Stocks: {len(snapshot['stocks'])}")
    print(f"   News items: {len(snapshot['news'])}")
    print(f"   Market news items (24h): {len(snapshot['market_news'])}")


if __name__ == "__main__":
    main()
