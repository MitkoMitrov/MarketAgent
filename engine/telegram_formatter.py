"""
Telegram formatter for market reports.
Formats snapshot data into Telegram-friendly sections.
"""
from datetime import datetime, timezone

from engine.market_data import format_market_cap
from engine.news_grouping import group_news


def format_daily_reports_from_ai(ai_report_text):
    """Format the AI-generated market report for the Daily Reports topic.
    Removes the header and splits into two parts at '💡 Market Insights' section.
    Returns tuple: (part1, part2)
    """
    if not ai_report_text:
        return ("⚠️ No AI report available.", "")

    # Split into lines and skip header (AI Market Report, Generated, Source, ====)
    lines = ai_report_text.strip().split('\n')
    
    # Find where content starts (after the separator line ====)
    content_start = 0
    for i, line in enumerate(lines):
        if '=' * 10 in line:  # Found separator
            content_start = i + 1
            break
    
    # Get full content without header
    content_lines = lines[content_start:]
    
    # Find the split point: "💡 Market Insights" header
    split_index = None
    for i, line in enumerate(content_lines):
        if '💡 Market Insights' in line:
            split_index = i
            break
    
    if split_index is None:
        # If no split point found, return all as part 1
        return ('\n'.join(content_lines).strip(), "")
    
    # Part 1: Everything up to (but not including) Market Insights header
    part1_lines = content_lines[:split_index]
    
    # Part 2: From Market Insights header to the end
    part2_lines = content_lines[split_index:]
    
    part1 = '\n'.join(part1_lines).strip()
    part2 = '\n'.join(part2_lines).strip()
    
    return (part1, part2)


def format_stock_summary(snapshot):
    """
    Format a quick stock summary section.
    Shows: Symbol with green circle for gains, red for losses.
    """
    lines = []
    lines.append("Today's Stock Moves:")
    
    stocks = snapshot.get("stocks", {})
    if not stocks:
        return ""
    
    for symbol, data in stocks.items():
        price = data.get("price", 0)
        change_pct = data.get("change_percent", 0)
        
        # Green circle for positive, red for negative
        if change_pct > 0:
            emoji = "🟢"
        elif change_pct < 0:
            emoji = "🔴"
        else:
            emoji = "⚪"
        
        lines.append(f"{emoji} {symbol} ${price:.2f} | {change_pct:+.2f}%")
    
    return "\n".join(lines)


def format_market_news(snapshot, max_items=10):
    """
    Format general market news for the Market News topic.
    Duplicate/similar stories are grouped; one line per story, newest first.
    Format: [dd/mm/yyyy HH:MM] Source: Headline(link) · +N similar
    """
    lines = ["📰 Market News (Last 24h)", ""]

    market_news = snapshot.get("market_news", [])
    if not market_news:
        lines.append("No significant market news today.")
        return "\n".join(lines)

    groups = group_news([dict(n, symbols=[], category="market") for n in market_news])

    for group in groups[:max_items]:
        item = group["primary"]
        headline = item.get("headline", "")
        source = item.get("source") or "Unknown"
        url = item.get("url", "")
        timestamp = item.get("timestamp", 0)

        time_str = ""
        if timestamp:
            try:
                time_str = datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%d/%m/%Y %H:%M")
            except Exception:
                time_str = ""

        line = f"[{time_str}] {source}: [{headline}]({url})" if url else f"[{time_str}] {source}: {headline}"
        if group["similar"]:
            line += f" · +{len(group['similar'])} similar"
        lines.append(line)

    lines.append("")
    lines.append(f"Total: {len(groups)} stories ({len(market_news)} articles) in last 24h")

    return "\n".join(lines)


def format_company_info(snapshot):
    """
    Format detailed company information for each stock.
    Shows: price, change, high, low, PE ratio, 52-week high/low, volume, market cap, beta.
    Returns: formatted message per company.
    """
    from datetime import datetime, timezone
    
    lines = []
    
    # Add current date and time at the beginning
    current_time = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    lines.append(f"*Company Information & Metrics*")
    lines.append(f"Updated: {current_time}")
    lines.append("")

    stocks = snapshot.get("stocks", {})
    if not stocks:
        return ""

    for symbol, data in stocks.items():
        name = data.get("name", symbol)
        price = data.get("price", 0)
        change = data.get("change", 0)
        change_pct = data.get("change_percent", 0)
        high = data.get("high", 0)
        low = data.get("low", 0)
        pe_ratio = data.get("pe_ratio")
        week_52_high = data.get("52_week_high", 0)
        week_52_low = data.get("52_week_low", 0)
        volume = data.get("volume", 0)
        market_cap = data.get("market_cap", 0)
        beta = data.get("beta", 0)
        industry = data.get("industry", "N/A")
        
        # Determine emoji based on change
        if change_pct > 0:
            emoji = "🟢"
        elif change_pct < 0:
            emoji = "🔴"
        else:
            emoji = "⚪"
        
        # Build company section
        lines.append(f"*{symbol}*")
        lines.append("")
        
        # Price info
        lines.append(f"• *Price:* ${price:.2f} | Change: {change:+.2f} ({change_pct:+.2f}%)")
        
        # Today's range
        lines.append(f"• *Today's Range:* ${low:.2f} - ${high:.2f}")
        
        # 52-week range
        lines.append(f"• *52-Week Range:* ${week_52_low:.2f} - ${week_52_high:.2f}")
        
        # Trading metrics
        lines.append(f"• *Volume:* {volume:.2f}M")
        lines.append(f"• *Market Cap:* {format_market_cap(market_cap)}")
        
        # Valuation metrics
        if pe_ratio:
            lines.append(f"• *P/E Ratio:* {pe_ratio:.2f}")
        else:
            lines.append(f"• *P/E Ratio:* N/A")
        
        lines.append(f"• *Beta:* {beta:.2f}")
        
        lines.append("")

    return "\n".join(lines)
