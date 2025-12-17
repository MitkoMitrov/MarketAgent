import json
import os
from openai import OpenAI

def load_finnhub_data(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_ai_summary(filtered_stocks, news, session, my_stocks, client):
    ai_input = {
        "session": session,
        "stocks": filtered_stocks,
        "news": news[:5]  # top 5 news for AI
    }

    prompt = f"""
    You are a professional market analyst. Based on this JSON, create:
    - Headline (1 line)
    - Summary (short paragraph)
    - Key insights per stock (why each stock moved)
    Format strictly as JSON:
    {{
        "headline": "...",
        "summary": "...",
        "key_insights": {{
            {', '.join([f'"{s}": "..."' for s in my_stocks])}
        }}
    }}
    JSON data:
    {json.dumps(ai_input)}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"⚠️ AI call failed: {e}")
        return {
            "headline": "NULL",
            "summary": "NULL",
            "key_insights": {s: "NULL" for s in my_stocks}
        }

def prepare_report(filepath, my_stocks, openai_api_key):
    client = OpenAI(api_key=openai_api_key)
    data = load_finnhub_data(filepath)

    session = data.get("market_session", "NULL")
    stocks_data = data.get("stocks", {})
    news_data = data.get("news", [])

    # Filter stocks
    filtered_stocks = {
        s: stocks_data.get(s, {
            "price": "NULL",
            "change_percent": "NULL",
            "high": "NULL",
            "low": "NULL",
            "previous_close": "NULL"
        })
        for s in my_stocks
    }

    ai_summary = generate_ai_summary(filtered_stocks, news_data, session, my_stocks, client)

    report = {
        "session": session,
        "headline": ai_summary.get("headline", "NULL"),
        "summary": ai_summary.get("summary", "NULL"),
        "stocks": filtered_stocks,
        "news": news_data[:3],
        "key_insights": ai_summary.get("key_insights", {})
    }

    return report
