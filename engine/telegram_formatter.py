"""
Telegram formatter for market reports.
Formats snapshot data into Telegram-friendly sections.
"""
from datetime import datetime, timezone


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
    Format: [HH:MM] Source: Headline(link)
    """
    lines = []

    lines.append("📰 Market News (Last 24h)")
    lines.append("")

    market_news = snapshot.get("market_news", [])
    if not market_news:
        lines.append("No significant market news today.")
        return "\n".join(lines)

    for item in market_news[:max_items]:
        headline = item.get("headline", "")
        source = item.get("source", "Unknown")
        url = item.get("url", "")
        timestamp = item.get("timestamp", 0)

        time_str = ""
        if timestamp:
            try:
                dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                time_str = dt.strftime("%H:%M")
            except Exception:
                time_str = ""

        # Build line: [time] Source: Headline(link)
        if url:
            lines.append(f"[{time_str}] {source}: [{headline}]({url})")
        else:
            lines.append(f"[{time_str}] {source}: {headline}")

    lines.append("")
    lines.append(f"Total: {len(market_news)} market news items in last 24h")

    return "\n".join(lines)
