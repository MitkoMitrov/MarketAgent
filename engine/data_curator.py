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
    
    # Sort stocks by absolute percent change to identify biggest movers
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
    
    # Sort by absolute change percent
    stock_list.sort(key=lambda x: abs(x.get("change_percent", 0)), reverse=True)
    
    # Identify top gainers and losers
    sorted_by_change = sorted(stock_list, key=lambda x: x.get("change_percent", 0), reverse=True)
    top_gainers = sorted_by_change[:3]
    top_losers = sorted_by_change[-3:]
    
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
        "top_movers": stock_list[:5],  # Top 5 biggest absolute movers
        "top_gainers": top_gainers,
        "top_losers": top_losers,
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
    
    lines.append("🔥 TOP MOVERS (by absolute change):")
    for stock in curated_data["top_movers"]:
        lines.append(f"  • {stock['symbol']} ({stock['name']})")
        lines.append(f"    Price: ${stock['price']:.2f} | Change: {stock['change_percent']:+.2f}%")
        lines.append(f"    Industry: {stock['industry']} | Market Cap: ${stock['market_cap']:.1f}B")
        if stock['pe_ratio']:
            lines.append(f"    P/E Ratio: {stock['pe_ratio']:.2f}")
        if stock['52_week_high'] and stock['52_week_low']:
            lines.append(f"    52-Week Range: ${stock['52_week_low']:.2f} - ${stock['52_week_high']:.2f}")
        lines.append("")
    
    lines.append("\n🔼 TOP GAINERS:")
    for stock in curated_data["top_gainers"]:
        lines.append(f"  • {stock['symbol']}: {stock['change_percent']:+.2f}% (${stock['price']:.2f})")
    
    lines.append("\n🔽 TOP LOSERS:")
    for stock in curated_data["top_losers"]:
        lines.append(f"  • {stock['symbol']}: {stock['change_percent']:+.2f}% (${stock['price']:.2f})")
    
    lines.append("\n📰 RECENT NEWS BY STOCK:")
    for symbol, news_items in curated_data["news_by_stock"].items():
        if news_items:
            lines.append(f"\n{symbol}:")
            for item in news_items[:3]:  # Limit to top 3 news per stock
                lines.append(f"  • {item['headline']} ({item['source']})")
                if item['summary']:
                    lines.append(f"    {item['summary'][:150]}...")
    
    return "\n".join(lines)
