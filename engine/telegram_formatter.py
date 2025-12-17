def format_market_report_for_telegram(report):
    lines = []

    lines.append(f"📊 *{report.get('session', 'NULL').capitalize()} Report* 📊")
    lines.append(f"*Headline:* {report.get('headline', 'NULL')}")
    lines.append(f"*Summary:* {report.get('summary', 'NULL')}\n")

    # Stocks table
    stocks = report.get("stocks", {})
    if stocks:
        lines.append("*Stocks:*")
        for symbol, data in stocks.items():
            price = data.get("price", "NULL")
            change = data.get("change_percent", "NULL")
            high = data.get("high", "NULL")
            low = data.get("low", "NULL")
            prev = data.get("previous_close", "NULL")
            lines.append(f"- {symbol}: Price={price}, Change%={change}, High={high}, Low={low}, Prev Close={prev}")
        lines.append("")

    # Top news
    news_list = report.get("news", [])
    if news_list:
        lines.append("*News Highlights:*")
        for news in news_list:
            symbol = news.get("symbol", "NULL")
            headline = news.get("headline", "NULL")
            source = news.get("source", "NULL")
            summary = news.get("summary", "NULL")
            lines.append(f"- {symbol} | {headline} ({source})\n  {summary[:250]}...")
        lines.append("")

    # Key insights
    key_insights = report.get("key_insights", {})
    if key_insights:
        lines.append("*Key Insights:*")
        for symbol, insight in key_insights.items():
            lines.append(f"- {symbol}: {insight}")

    return "\n".join(lines)
