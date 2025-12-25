"""
Data curation module - prepares market data for AI analysis.
Selects the most valuable insights to send to ChatGPT.
"""
from datetime import datetime


def curate_for_ai(snapshot):
    """
    Extract and format the most valuable data for AI analysis.
    Returns a clean, structured summary optimized for LLM consumption.
    """
    stocks = snapshot.get("stocks", {})
    news = snapshot.get("news", [])
    
    # Build stock list with all relevant data
    stock_list = []
    for symbol, data in stocks.items():
        stock_list.append({
            "symbol": symbol,
            "name": data.get("name", symbol),
            "price": data.get("price", 0),
            "change_percent": data.get("change_percent", 0),
            "industry": data.get("industry", "N/A"),
            "market_cap": data.get("market_cap", 0),
            "pe_ratio": data.get("pe_ratio"),
            "52_week_high": data.get("52_week_high"),
            "52_week_low": data.get("52_week_low"),
            "beta": data.get("beta"),
        })
    
    # Group news by stock
    news_by_stock = {}
    for item in news:
        symbol = item.get("symbol")
        if symbol not in news_by_stock:
            news_by_stock[symbol] = []
        news_by_stock[symbol].append({
            "headline": item.get("headline"),
            "summary": item.get("summary", ""),
            "source": item.get("source"),
        })
    
    # Build curated data structure
    curated = {
        "market_session": snapshot.get("market_session", "unknown"),
        "snapshot_time": snapshot.get("snapshot_time"),
        "total_stocks": len(stock_list),
        "stocks": stock_list,
        "news_by_stock": news_by_stock,
    }
    
    return curated


def format_for_prompt(curated_data):
    """
    Format curated data into a readable text format for the AI prompt.
    """
    lines = []
    lines.append(f"📊 Market Session: {curated_data['market_session']}")
    lines.append(f"⏰ Snapshot Time: {curated_data['snapshot_time']}\n")
    
    lines.append("� STOCK BRIEFING:")
    for stock in curated_data["stocks"]:
        symbol = stock["symbol"]
        lines.append(f"\n{symbol} - {stock['name']}")
        lines.append(f"  💰 Price: ${stock['price']:.2f} | Change: {stock['change_percent']:+.2f}%")
        
        # Add news briefing for this stock
        news_items = curated_data.get("news_by_stock", {}).get(symbol, [])
        if news_items:
            lines.append(f"  📰 Recent News:")
            for item in news_items[:5]:  # Show up to 5 news items per stock
                lines.append(f"    • {item['headline']} ({item['source']})")
                if item['summary']:
                    lines.append(f"      {item['summary'][:150]}...")
        else:
            lines.append(f"  📰 No recent news")
    
    return "\n".join(lines)
