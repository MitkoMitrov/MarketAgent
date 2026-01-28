"""
Check for upcoming earnings calls and format for Telegram.
Loaded earnings data once at startup and checks for events within specified days.
"""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


def load_earnings_data():
    """Load cached earnings data from file."""
    PROJECT_ROOT = Path(__file__).parent.parent
    earnings_file = PROJECT_ROOT / "data" / "earnings" / "earnings_2026.json"
    
    if not earnings_file.exists():
        return None
    
    try:
        with open(earnings_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading earnings data: {e}")
        return None


def get_upcoming_earnings(days_ahead=7):
    """
    Get earnings calls happening in the next N days.
    
    Args:
        days_ahead: Number of days to look ahead (1, 3, or 7)
    
    Returns:
        List of upcoming earnings with symbol and date
    """
    earnings_data = load_earnings_data()
    if not earnings_data:
        return []
    
    upcoming = []
    now = datetime.now(timezone.utc)
    # Get start of today (to include today's earnings even if time has passed)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    future_date = today_start + timedelta(days=days_ahead)
    
    for symbol, data in earnings_data.get("earnings", {}).items():
        # Handle both formats: direct list or nested earningsCalendar
        if isinstance(data, dict) and "earningsCalendar" in data:
            earnings_list = data["earningsCalendar"]
        elif isinstance(data, list):
            earnings_list = data
        else:
            continue
        
        if not earnings_list:
            continue
        
        for earning in earnings_list:
            # Handle different date formats
            date_str = earning.get("date") or earning.get("datetime")
            if not date_str:
                continue
            
            try:
                # Parse date (Finnhub returns YYYY-MM-DD format)
                if "T" in str(date_str):
                    earn_date = datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
                else:
                    earn_date = datetime.strptime(str(date_str), "%Y-%m-%d").replace(tzinfo=timezone.utc)
                
                # Check if within range (from start of today to future_date)
                if today_start <= earn_date <= future_date:
                    upcoming.append({
                        "symbol": symbol,
                        "date": earn_date,
                        "epsEstimate": earning.get("epsEstimate"),
                        "epsActual": earning.get("epsActual"),
                        "revenueEstimate": earning.get("revenueEstimate"),
                        "revenueActual": earning.get("revenueActual"),
                        "quarter": earning.get("quarter"),
                        "year": earning.get("year")
                    })
            except Exception as e:
                print(f"⚠️ Error parsing date {date_str} for {symbol}: {e}")
                continue
    
    # Sort by date
    upcoming.sort(key=lambda x: x["date"])
    return upcoming


def format_earnings_alert(upcoming_earnings, days_ahead=7, market_session="pre-market"):
    """
    Format upcoming earnings for Telegram alert.
    
    Args:
        upcoming_earnings: List of upcoming earnings
        days_ahead: Number of days being checked
        market_session: Either 'pre-market' or 'after-market'
    
    Returns:
        Formatted message string
    """
    if not upcoming_earnings:
        return None
    
    lines = []
    
    # Get session label
    session_label = "📈 PRE-MARKET" if market_session == "pre-market" else "📉 AFTER-MARKET"
    
    # Header with current date and time
    current_time = datetime.now(timezone.utc)
    current_date = current_time.strftime("%d/%m/%Y")
    current_time_str = current_time.strftime("%H:%M UTC")
    
    lines.append(f"*📅 Upcoming Earnings Calls*")
    lines.append(f"{session_label} | {current_date} {current_time_str}")
    lines.append(f"Next {days_ahead} days")
    lines.append("")
    
    for earning in upcoming_earnings:
        symbol = earning["symbol"]
        date = earning["date"]
        # Format: day/month/year (e.g., 01/01/2026)
        date_str = date.strftime("%d/%m/%Y")
        
        # Calculate days until earnings (compare dates, not datetimes)
        now = datetime.now(timezone.utc)
        today_date = now.date()
        earn_date_only = date.date()
        days_until = (earn_date_only - today_date).days
        
        if days_until == 0:
            time_indicator = "🔴 TODAY"
        elif days_until == 1:
            time_indicator = "🟡 TOMORROW"
        else:
            time_indicator = f"🟢 in {days_until} days"
        
        lines.append(f"*{symbol}*")
        lines.append(f"• Date: {date_str}")
        lines.append(f"• Days until: {time_indicator}")
        
        # EPS estimates if available
        if earning.get("epsEstimate"):
            lines.append(f"• EPS Estimate: {earning['epsEstimate']}")
        
        # Revenue estimates if available
        if earning.get("revenueEstimate"):
            lines.append(f"• Revenue Estimate: ${earning['revenueEstimate']/1e9:.2f}B")
        
        lines.append("")
    
    return "\n".join(lines)


def main():
    """Test: Check for earnings in next 7 days."""
    print("=" * 60)
    print("📅 Earnings Alert Checker")
    print("=" * 60)
    
    # Check for earnings in different timeframes
    for days in [1, 3, 7]:
        earnings = get_upcoming_earnings(days_ahead=days)
        if earnings:
            print(f"\n🔔 Earnings in next {days} day(s): {len(earnings)} events")
            message = format_earnings_alert(earnings, days_ahead=days)
            if message:
                print("\nFormatted message:")
                print("-" * 60)
                print(message)
                print("-" * 60)
        else:
            print(f"\n✅ No earnings in next {days} day(s)")


if __name__ == "__main__":
    main()
