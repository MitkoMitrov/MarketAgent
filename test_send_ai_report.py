"""
Quick test script to send AI report to Daily Reports topic.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from engine.telegram_sender import send_message_to_topic
from engine.telegram_formatter import format_daily_reports_from_ai, format_stock_summary
from engine.report_engine import load_latest_market_snapshot

load_dotenv()
topic_id = os.getenv('TELEGRAM_TOPIC_DAILY_REPORTS')

# Load snapshot
snapshot_data, snapshot_file = load_latest_market_snapshot()
print(f"📂 Loaded snapshot: {snapshot_file}")

# Load AI report
ai_report_path = Path("reports/ai_report-20251224-221312.txt")
with open(ai_report_path, 'r', encoding='utf-8') as f:
    ai_text = f.read()

# Format components
stock_summary = format_stock_summary(snapshot_data)
ai_report_part1, ai_report_part2 = format_daily_reports_from_ai(ai_text)

# Create messages
message1 = f"{stock_summary}\n\n{ai_report_part1}"
message2 = ai_report_part2

print(f"\n📏 Message 1 length: {len(message1)} chars")
print(f"📏 Message 2 length: {len(message2)} chars")
print(f"   (Telegram limit: 4096 chars per message)")

# Send message 1
print(f"\n📤 Sending message 1/2 to Daily Reports (topic {topic_id})...")
result1 = send_message_to_topic(topic_id, message1, parse_mode=None)
if result1:
    print("✅ Message 1 sent successfully!")
else:
    print("❌ Message 1 failed to send")

# Send message 2
if message2:
    print(f"\n📤 Sending message 2/2 to Daily Reports (topic {topic_id})...")
    result2 = send_message_to_topic(topic_id, message2, parse_mode=None)
    if result2:
        print("✅ Message 2 sent successfully!")
    else:
        print("❌ Message 2 failed to send")
