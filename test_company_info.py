"""
Test script to send only company information to Telegram.
Useful for testing the new company info channel independently.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv

from engine.report_engine import load_latest_market_snapshot
from engine.telegram_sender import send_message_to_topic
from engine.telegram_formatter import format_company_info

# Load environment
load_dotenv()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_TOPIC_COMPANY_INFO = os.getenv("TELEGRAM_TOPIC_COMPANY_INFO")

if not all([TELEGRAM_CHAT_ID, TELEGRAM_TOPIC_COMPANY_INFO]):
    raise ValueError("Missing Telegram config: TELEGRAM_CHAT_ID, TELEGRAM_TOPIC_COMPANY_INFO")


def main():
    """Main execution flow."""
    print("=" * 60)
    print("📊 Test: Company Info to Telegram")
    print("=" * 60)
    
    # Load latest snapshot
    print("\n📂 Loading latest market snapshot...")
    snapshot, snapshot_name = load_latest_market_snapshot()
    print(f"   Loaded: {snapshot_name}")
    
    # Format company info
    print("\n📋 Formatting company information...")
    company_info_text = format_company_info(snapshot)
    
    # Print preview
    print("\n📄 Preview of message:")
    print("-" * 60)
    print(company_info_text[:1500])
    if len(company_info_text) > 1500:
        print("\n... [message continues] ...")
    print("-" * 60)
    
    # Send to Telegram
    print(f"\n📤 Posting to Company Info (topic {TELEGRAM_TOPIC_COMPANY_INFO})...")
    result = send_message_to_topic(TELEGRAM_TOPIC_COMPANY_INFO, company_info_text, parse_mode="Markdown")
    
    if result:
        print("   ✅ Posted successfully!")
    else:
        print("   ❌ Failed to post")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
