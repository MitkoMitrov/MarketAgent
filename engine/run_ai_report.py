"""
AI-powered market report generator using OpenAI's GPT.
Loads latest Finnhub snapshot, curates data, and generates narrative report.
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

from engine.report_engine import load_latest_market_snapshot
from engine.data_curator import curate_for_ai, format_for_prompt
from engine.prompts import SYSTEM_PROMPT

# Load environment
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Add it to your .env file.")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Output settings
OUTPUT_DIR = Path("reports")
OUTPUT_DIR.mkdir(exist_ok=True)


def generate_ai_report(snapshot_data):
    """
    Send curated market data to ChatGPT and generate a professional report.
    """
    print("🤖 Curating data for AI analysis...")
    curated = curate_for_ai(snapshot_data)
    
    print("📝 Formatting data for ChatGPT prompt...")
    formatted_data = format_for_prompt(curated)
    
    print("🚀 Sending to ChatGPT (GPT-4o)...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # or "gpt-4-turbo" or "gpt-3.5-turbo" for cost savings
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Here is today's market data:\n\n{formatted_data}\n\nPlease generate a comprehensive market report."}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        report_text = response.choices[0].message.content
        return report_text
    
    except Exception as e:
        print(f"❌ Error calling OpenAI API: {e}")
        raise


def main():
    """Main execution flow."""
    print("=" * 60)
    print("🎯 AI Market Report Generator")
    print("=" * 60)
    
    # Load latest snapshot
    print("\n📂 Loading latest market snapshot...")
    snapshot, snapshot_name = load_latest_market_snapshot()
    print(f"   Loaded: {snapshot_name}")
    
    # Generate AI report
    report_text = generate_ai_report(snapshot)
    
    # Save report
    timestamp = snapshot_name.replace("market_snapshot-", "").replace(".json", "")
    output_file = OUTPUT_DIR / f"ai_report-{timestamp}.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"AI Market Report\n")
        f.write(f"Generated: {timestamp}\n")
        f.write(f"Source: {snapshot_name}\n")
        f.write("=" * 60 + "\n\n")
        f.write(report_text)
    
    print(f"\n✅ AI report generated successfully!")
    print(f"   📄 Saved to: {output_file}")
    print(f"   📊 Report length: {len(report_text)} characters")
    print("\n" + "=" * 60)
    
    # Print preview
    print("\n📖 REPORT PREVIEW:")
    print("-" * 60)
    print(report_text[:500] + "..." if len(report_text) > 500 else report_text)
    print("-" * 60)


if __name__ == "__main__":
    main()
