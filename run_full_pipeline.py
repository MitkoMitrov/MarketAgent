"""
Full MarketAgent Pipeline
Runs the complete end-to-end workflow:
1. Fetch market data from Finnhub
2. Generate AI report with OpenAI
3. Send reports to Telegram
"""
import sys
import subprocess
from pathlib import Path
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas_market_calendars as mcal


def run_step(step_name, command, description):
    """Run a pipeline step and handle errors."""
    print("\n" + "=" * 60)
    print(f"🚀 STEP: {step_name}")
    print(f"   {description}")
    print("=" * 60)
    
    # Use the virtual environment Python if in a venv
    python_exe = sys.executable
    if command.startswith("python "):
        command = command.replace("python ", f'"{python_exe}" ', 1)
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=False,
            text=True
        )
        print(f"\n✅ {step_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {step_name} failed with exit code {e.returncode}")
        return False


def _parse_non_working_dates():
    """Parse non-working dates from env (comma-separated YYYY-MM-DD)."""
    raw = os.getenv("NON_WORKING_DATES", "").strip()
    if not raw:
        return set()
    return {part.strip() for part in raw.split(",") if part.strip()}


def is_working_day():
    """Return True if today is a US market (NYSE) working day."""
    tz = ZoneInfo("America/New_York")
    today = datetime.now(tz).date()

    non_working = _parse_non_working_dates()
    if today.isoformat() in non_working:
        return False

    cal = mcal.get_calendar("NYSE")
    schedule = cal.schedule(start_date=today.isoformat(), end_date=today.isoformat())
    return not schedule.empty


def main():
    """Execute the full pipeline."""
    print("=" * 60)
    print("📊 MARKETAGENT FULL PIPELINE")
    print("=" * 60)
    print("This will:")
    print("  1. Fetch latest market data from Finnhub")
    print("  2. Generate AI market report with OpenAI")
    print("  3. Send reports to Telegram topics")
    print("  4. Check and send earnings alerts")
    print("=" * 60)

    working_day = is_working_day()
    if working_day:
        print("📅 Working day detected (US/NYSE)")
    else:
        print("📅 Non-working day detected (weekend/holiday). Market News only.")
    
    # Step 1: Fetch data
    if not run_step(
        "1/4 - Fetch Market Data",
        "python -m finnhub_scripts.fetch_and_store",
        "Fetching quotes, news, and market data from Finnhub..."
    ):
        print("\n⚠️  Pipeline stopped due to data fetch failure")
        sys.exit(1)
    
    if working_day:
        # Step 2: Generate AI report
        if not run_step(
            "2/4 - Generate AI Report",
            "python -m engine.run_ai_report",
            "Generating market analysis report with OpenAI GPT-4..."
        ):
            print("\n⚠️  Pipeline stopped due to AI report generation failure")
            sys.exit(1)

        # Step 3: Send to Telegram
        os.environ.pop("MARKET_NEWS_ONLY", None)
        if not run_step(
            "3/4 - Send to Telegram",
            "python -m engine.send_telegram_report",
            "Posting reports to Telegram group topics..."
        ):
            print("\n⚠️  Pipeline stopped due to Telegram send failure")
            sys.exit(1)

        # Step 4: Send earnings alerts
        if not run_step(
            "4/4 - Send Earnings Alerts",
            "python -m engine.send_earnings_alert",
            "Checking and sending upcoming earnings alerts..."
        ):
            print("\n⚠️  Pipeline step failed but continuing...")
    else:
        # Non-working day: Market news only
        os.environ["MARKET_NEWS_ONLY"] = "1"
        if not run_step(
            "2/2 - Send Market News Only",
            "python -m engine.send_telegram_report",
            "Posting only Market News to Telegram..."
        ):
            print("\n⚠️  Pipeline stopped due to Telegram send failure")
            sys.exit(1)
    
    # Success
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE!")
    print("=" * 60)
    print("📊 Market data fetched")
    if working_day:
        print("🤖 AI report generated")
        print("📢 Reports sent to Telegram")
        print("📅 Earnings alerts sent (if any)")
    else:
        print("📰 Market news sent to Telegram")
    print("=" * 60)


if __name__ == "__main__":
    main()
