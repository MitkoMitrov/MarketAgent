"""
Data curation module - prepares market data for AI analysis.
Selects the most valuable insights to send to ChatGPT.
"""
from engine.news_grouping import group_news

# Distinct stories per stock sent to the AI. This fixes the prompt size (and OpenAI cost)
# no matter how many raw articles Finnhub returned.
NEWS_PER_STOCK = 5


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
    
    news_by_stock = select_news_by_stock(news, list(stocks), NEWS_PER_STOCK)
    
    # Build curated data structure
    curated = {
        "market_session": snapshot.get("market_session", "unknown"),
        "snapshot_time": snapshot.get("snapshot_time"),
        "total_stocks": len(stock_list),
        "stocks": stock_list,
        "news_by_stock": news_by_stock,
    }
    
    return curated


def select_news_by_stock(news, symbols, per_stock=NEWS_PER_STOCK):
    """Group duplicate/similar articles, then pick the top `per_stock` distinct stories per symbol.

    Stories covered by more articles come first, then the newest. Returns
    {symbol: [{"headline", "summary", "source", "articles"}]}.
    """
    groups = group_news(news)
    groups.sort(key=lambda g: (g["size"], g["latest_ts"]), reverse=True)

    selected = {sym: [] for sym in symbols}
    for g in groups:
        p = g["primary"]
        entry = {
            "headline": p["headline"],
            "summary": p["summary"],
            "source": p["source"],
            "articles": g["size"],
        }
        for sym in g["symbols"]:
            if sym in selected and len(selected[sym]) < per_stock:
                selected[sym].append(entry)
    return {sym: items for sym, items in selected.items() if items}


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
            for item in news_items[:NEWS_PER_STOCK]:
                covered = f", {item['articles']} articles" if item.get("articles", 1) > 1 else ""
                lines.append(f"    • {item['headline']} ({item['source']}{covered})")
                if item['summary']:
                    lines.append(f"      {item['summary'][:150]}...")
        else:
            lines.append(f"  📰 No recent news")
    
    return "\n".join(lines)
