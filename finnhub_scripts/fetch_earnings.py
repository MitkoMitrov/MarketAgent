"""
Fetch and store earnings calendar data from Finnhub.
Fetches earnings for all configured stocks for the year 2026.
Data is cached locally and reused throughout the year.
"""
import os
import json
from datetime import datetime, timezone
from pathlib import Path
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
SYMBOLS = ["TSLA", "AMD", "QQQ", "GOOG", "NVDA", "MSTR", "SMCI", "ATP"]

# Get project root and create data directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "earnings")
os.makedirs(DATA_DIR, exist_ok=True)

EARNINGS_FILE = os.path.join(DATA_DIR, "earnings_2026.json")


def fetch_earnings_calendar(symbol, year=2026):
    """Fetch earnings calendar data for a symbol for the specified year."""
    try:
        # Earnings for the entire year
        from_date = f"{year}-01-01"
        to_date = f"{year}-12-31"
        
        earnings_data = finnhub_client.earnings_calendar(
            _from=from_date,
            to=to_date,
            symbol=symbol
        )
        return earnings_data if earnings_data else []
    except Exception as e:
        print(f"⚠️ Error fetching earnings for {symbol}: {e}")
        return []


def main():
    """Fetch and store earnings data for all symbols."""
    print("=" * 60)
    print("📅 Earnings Calendar Fetcher (2026)")
    print("=" * 60)
    
    all_earnings = {}
    
    print(f"\n🔍 Fetching earnings data for {len(SYMBOLS)} stocks...")
    
    for symbol in SYMBOLS:
        print(f"   ➜ Fetching {symbol}...", end=" ")
        earnings = fetch_earnings_calendar(symbol)
        if earnings:
            all_earnings[symbol] = earnings
            print(f"✅ Found {len(earnings)} earnings")
        else:
            all_earnings[symbol] = []
            print("⚠️ No earnings found")
    
    # Save to file with metadata
    earnings_data = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "year": 2026,
        "symbols": SYMBOLS,
        "earnings": all_earnings
    }
    
    try:
        with open(EARNINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(earnings_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Earnings data saved to: {EARNINGS_FILE}")
        
        # Print summary
        total_earnings = sum(len(e) for e in all_earnings.values())
        print(f"\n📊 Summary:")
        print(f"   Total stocks: {len(SYMBOLS)}")
        print(f"   Total earnings found: {total_earnings}")
        for symbol, earnings in all_earnings.items():
            if earnings:
                print(f"   • {symbol}: {len(earnings)} earnings")
        
    except Exception as e:
        print(f"\n❌ Error saving earnings data: {e}")


if __name__ == "__main__":
    main()
