import os
from engine.report_engine import prepare_report
from engine.telegram_formatter import format_market_report_for_telegram
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

MY_STOCKS = ["TSLA", "AMD", "TTWO", "GOOG", "NVDA", "MSTR"]

def main():
    try:
        # Use proper path to data directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(project_root, "data", "snapshots")
        
        # Get the most recent snapshot file
        snapshot_files = sorted([f for f in os.listdir(data_dir) if f.startswith("market_snapshot-") and f.endswith(".json")])
        if not snapshot_files:
            raise FileNotFoundError("No snapshot files found in data/snapshots directory")
        
        finnhub_file = os.path.join(data_dir, snapshot_files[-1])
        print(f"📊 Using snapshot: {snapshot_files[-1]}")
        report = prepare_report(finnhub_file, MY_STOCKS, openai_api_key=OPENAI_API_KEY)
        telegram_message = format_market_report_for_telegram(report)
        print(telegram_message)
    except Exception as e:
        print(f"⚠️ Failed to generate report: {e}")
        fallback_report = {
            "headline": "NULL",
            "summary": "NULL",
            "stocks": {s: {"price":"NULL","change_percent":"NULL","high":"NULL","low":"NULL","previous_close":"NULL"} for s in MY_STOCKS},
            "news": [],
            "key_insights": {s: "NULL" for s in MY_STOCKS},
            "session": "NULL"
        }
        print(format_market_report_for_telegram(fallback_report))

if __name__ == "__main__":
    main()
