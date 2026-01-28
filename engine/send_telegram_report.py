"""
Send market report to Telegram topics.
Loads latest snapshot, formats into Daily Reports + Market News sections, and posts to topics.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

from engine.report_engine import load_latest_market_snapshot
from engine.telegram_sender import send_message_to_topic
from engine.telegram_formatter import format_daily_reports_from_ai, format_stock_summary, format_market_news, format_company_info

# Load environment
load_dotenv()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_TOPIC_DAILY_REPORTS = os.getenv("TELEGRAM_TOPIC_DAILY_REPORTS")
TELEGRAM_TOPIC_MARKET_NEWS = os.getenv("TELEGRAM_TOPIC_MARKET_NEWS")
TELEGRAM_TOPIC_COMPANY_INFO = os.getenv("TELEGRAM_TOPIC_COMPANY_INFO")
MARKET_SESSION = os.getenv("MARKET_SESSION", "after-market")  # Default to after-market for reports

if not all([TELEGRAM_CHAT_ID, TELEGRAM_TOPIC_DAILY_REPORTS, TELEGRAM_TOPIC_MARKET_NEWS, TELEGRAM_TOPIC_COMPANY_INFO]):
    raise ValueError("Missing Telegram config: TELEGRAM_CHAT_ID, TELEGRAM_TOPIC_DAILY_REPORTS, TELEGRAM_TOPIC_MARKET_NEWS, TELEGRAM_TOPIC_COMPANY_INFO")


# Helpers
def load_latest_ai_report():
    """Load the latest AI report text from reports/ directory."""
    reports_dir = Path("reports")
    reports = sorted(reports_dir.glob("ai_report-*.txt"), reverse=True)
    if not reports:
        return ("⚠️ No AI report found. Run run_ai_report first.", None)
    latest = reports[0]
    try:
        with open(latest, "r", encoding="utf-8") as f:
            content = f.read()
        return (content, latest.name)
    except Exception as e:
        return (f"⚠️ Failed to read AI report: {e}", latest.name)


def send_telegram_report(snapshot_data):
    """
    Load a snapshot and send formatted reports to Telegram topics.
    
    Args:
        snapshot_data (dict): Market snapshot dictionary (from load_latest_market_snapshot).
    """
    print("📢 Sending Telegram report...")
    
    # Get market session label
    session_label = "📈 PRE-MARKET" if MARKET_SESSION == "pre-market" else "📉 AFTER-MARKET"
    
    # Load latest AI report text (fallback to notice if missing)
    ai_report_text, ai_report_name = load_latest_ai_report()

    # Format stock summary
    stock_summary = format_stock_summary(snapshot_data)
    
    # Format AI report - returns (part1, part2) tuple
    ai_report_part1, ai_report_part2 = format_daily_reports_from_ai(ai_report_text)
    
    # Add market session label to first message
    daily_report_msg1 = f"{session_label}\n\n{stock_summary}\n\n{ai_report_part1}"
    
    # Message 2: second part of AI report (includes Market Insights header)
    daily_report_msg2 = ai_report_part2
    
    # Format for Market News topic
    market_news_text = format_market_news(snapshot_data, max_items=10)
    
    # Format for Company Info topic
    company_info_text = format_company_info(snapshot_data)
    
    # Send to Daily Reports topic (2 messages)
    print(f"\n📤 Posting to Daily Reports (topic {TELEGRAM_TOPIC_DAILY_REPORTS})... [{MARKET_SESSION.upper()}]")
    print("   Sending message 1/2...")
    result1 = send_message_to_topic(TELEGRAM_TOPIC_DAILY_REPORTS, daily_report_msg1, parse_mode=None)
    if result1:
        print("   ✅ Message 1 posted successfully")
    else:
        print("   ❌ Message 1 failed to post")
    
    if daily_report_msg2:
        print("   Sending message 2/2...")
        result2 = send_message_to_topic(TELEGRAM_TOPIC_DAILY_REPORTS, daily_report_msg2, parse_mode=None)
        if result2:
            print("   ✅ Message 2 posted successfully")
        else:
            print("   ❌ Message 2 failed to post")
    
    print(f"\n📤 Posting to Market News (topic {TELEGRAM_TOPIC_MARKET_NEWS})...")
    result3 = send_message_to_topic(TELEGRAM_TOPIC_MARKET_NEWS, market_news_text, parse_mode="Markdown")
    if result3:
        print("   ✅ Posted successfully")
    else:
        print("   ❌ Failed to post")
    
    print(f"\n📤 Posting to Company Info (topic {TELEGRAM_TOPIC_COMPANY_INFO})...")
    result4 = send_message_to_topic(TELEGRAM_TOPIC_COMPANY_INFO, company_info_text, parse_mode="Markdown")
    if result4:
        print("   ✅ Posted successfully")
    else:
        print("   ❌ Failed to post")
    
    print("\n" + "=" * 60)


def main():
    """Main execution flow."""
    print("=" * 60)
    print("📢 Telegram Market Report Sender")
    print("=" * 60)
    
    # Load latest snapshot
    print("\n📂 Loading latest market snapshot...")
    snapshot, snapshot_name = load_latest_market_snapshot()
    print(f"   Loaded: {snapshot_name}")
    
    # Send to Telegram
    send_telegram_report(snapshot)
    
    print("\n✅ Telegram report sent!\n")


if __name__ == "__main__":
    main()


# Helpers
def load_latest_ai_report():
    """Load the latest AI report text from reports/ directory."""
    reports_dir = Path("reports")
    reports = sorted(reports_dir.glob("ai_report-*.txt"), reverse=True)
    if not reports:
        return ("⚠️ No AI report found. Run run_ai_report first.", None)
    latest = reports[0]
    try:
        with open(latest, "r", encoding="utf-8") as f:
            content = f.read()
        return (content, latest.name)
    except Exception as e:
        return (f"⚠️ Failed to read AI report: {e}", latest.name)
