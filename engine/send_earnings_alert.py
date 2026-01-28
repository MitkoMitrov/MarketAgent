"""
Send earnings alerts to Telegram.
Checks for upcoming earnings and posts to dedicated topic.
Only runs on pre-market session.
"""
import os
from dotenv import load_dotenv

from engine.earnings_checker import get_upcoming_earnings, format_earnings_alert
from engine.telegram_sender import send_message_to_topic

# Load environment
load_dotenv()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_TOPIC_EARNINGS = os.getenv("TELEGRAM_TOPIC_EARNINGS")
MARKET_SESSION = os.getenv("MARKET_SESSION", "pre-market")

if not all([TELEGRAM_CHAT_ID, TELEGRAM_TOPIC_EARNINGS]):
    raise ValueError("Missing Telegram config: TELEGRAM_CHAT_ID, TELEGRAM_TOPIC_EARNINGS")


def send_earnings_alert():
    """
    Check for upcoming earnings and send alerts to Telegram.
    Only sends during pre-market session (15:30 UTC).
    """
    # Earnings alerts only run during pre-market
    if MARKET_SESSION != "pre-market":
        print("📅 Earnings alerts skipped (only runs on pre-market)")
        return False
    
    print("📅 Checking for upcoming earnings...")
    
    # Check for all earnings in next 7 days
    earnings = get_upcoming_earnings(days_ahead=7)
    
    if earnings:
        message = format_earnings_alert(earnings, days_ahead=7, market_session=MARKET_SESSION)
        
        if message:
            print(f"\n📤 Found {len(earnings)} upcoming earnings")
            print(f"   Posting to Earnings topic {TELEGRAM_TOPIC_EARNINGS}...")
            
            result = send_message_to_topic(
                TELEGRAM_TOPIC_EARNINGS,
                message,
                parse_mode="Markdown"
            )
            
            if result:
                print(f"   ✅ Posted successfully")
                return True
            else:
                print(f"   ❌ Failed to post")
                return False
    else:
        print("✅ No upcoming earnings to report")
        return False


def main():
    """Main execution flow."""
    print("=" * 60)
    print("📅 Earnings Alert Sender")
    print("=" * 60)
    print()
    
    send_earnings_alert()
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
