"""
News fetching from Finnhub: company news per symbol and filtered general market news.

All functions return items in one normalized shape:
    {"headline", "source", "summary", "url", "image", "timestamp", "symbols": [...], "category"}
where category is "company" or "market", and image is "" when there is no real thumbnail.
"""
from datetime import datetime, timedelta, timezone

from engine.finnhub_client import SYMBOLS, get_client

_POSITIVE_KEYWORDS = {
    # Macro & indices
    'gdp', 'cpi', 'pce', 'inflation', 'unemployment', 'jobs report', 'payrolls', 'ism', 'pmi',
    'fomc', 'fed', 'interest rate', 'rates', 'yields', 'treasury', 'bond', 'recession',
    's&p', 'sp500', 's&p 500', 'nasdaq', 'dow', 'vix', 'volatility',
    # Corporate actions & market events
    'earnings', 'guidance', 'revenue', 'eps', 'dividend', 'buyback', 'merger', 'acquisition', 'deal',
    'ipo', 'spac', 'antitrust', 'regulator', 'sec', 'doj', 'lawsuit', 'settlement', 'recall',
    'upgrade', 'downgrade', 'price target', 'outlook',
    # Sectors & assets
    'semiconductor', 'chip', 'ai', 'cloud', 'software', 'cybersecurity', 'energy', 'opec',
    'oil', 'gas', 'wti', 'brent', 'gold', 'silver', 'copper', 'commodities',
    'crypto', 'bitcoin', 'ethereum'
}

_NEGATIVE_KEYWORDS = {
    # Lifestyle / personal finance / career advice
    'how to', 'advice', 'tips', 'beginners', 'job seeker', 'career', 'resume', 'interview',
    'linkedin', 'years old', 'year-old', 'ice cream', 'home ', 'real estate tips', 'retire',
    'retirement', '401(k)', 'credit score', 'save money', 'budget', 'debt payoff', 'student loan',
    'frugal', 'side hustle', 'parents', 'kids', 'family', 'holiday gifts'
}


def _contains_any(text: str, terms) -> bool:
    if not text:
        return False
    tl = text.lower()
    return any(t in tl for t in terms)


def _mentions_watchlist(text: str, symbols) -> bool:
    if not text:
        return False
    tu = text.upper()
    if any(sym in tu for sym in symbols):
        return True
    return any(k in tu for k in ['S&P', 'NASDAQ', 'DOW'])


def _related_symbols(item: dict, symbols) -> list:
    related = item.get('related', '') or ''  # comma-separated tickers when present
    rel = {s.strip().upper() for s in related.split(',') if s.strip()}
    return sorted(rel.intersection(symbols))


def is_relevant_market_news(item: dict, symbols=SYMBOLS) -> bool:
    """Heuristic relevance check for market news.
    Keep if it mentions watchlist symbols/indices or contains market/macro/corporate
    action keywords, and does not contain lifestyle/personal-finance terms.
    """
    headline = item.get('headline', '') or ''
    summary = item.get('summary', '') or ''

    if _contains_any(headline, _NEGATIVE_KEYWORDS) or _contains_any(summary, _NEGATIVE_KEYWORDS):
        return False
    if _related_symbols(item, symbols):
        return True
    if _mentions_watchlist(headline, symbols) or _mentions_watchlist(summary, symbols):
        return True
    return _contains_any(headline, _POSITIVE_KEYWORDS) or _contains_any(summary, _POSITIVE_KEYWORDS)


# Publisher/source logos that Finnhub returns instead of an article image.
_PLACEHOLDER_IMAGE_MARKERS = ("/logo/", "logo.", "_logo", "yahoo_finance_en-us", "default", "placeholder")


def clean_image_url(url: str) -> str:
    """Return the article image URL, or "" for missing/non-https/logo placeholders."""
    url = (url or "").strip()
    if not url.lower().startswith("https://"):
        return ""
    if any(m in url.lower() for m in _PLACEHOLDER_IMAGE_MARKERS):
        return ""
    return url


def _normalize(raw: dict, symbols: list, category: str) -> dict:
    return {
        "headline": raw.get("headline", "") or "",
        "source": raw.get("source", "") or "",
        "summary": raw.get("summary", "") or "",
        "url": raw.get("url", "") or "",
        "image": clean_image_url(raw.get("image", "")),
        "timestamp": raw.get("datetime", 0) or 0,
        "symbols": symbols,
        "category": category,
    }


def fetch_company_news(symbol: str, hours: int = 24, limit=None) -> list:
    """Fetch all company news for one symbol from the last `hours`, newest first.

    `limit` optionally caps the number of items (None = everything Finnhub returns)."""
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        news = get_client().company_news(
            symbol,
            _from=cutoff.strftime("%Y-%m-%d"),
            to=now.strftime("%Y-%m-%d"),
        )
        news = [n for n in news if n.get('datetime', 0) >= int(cutoff.timestamp())]
        news.sort(key=lambda x: x.get('datetime', 0), reverse=True)
        if limit:
            news = news[:limit]
        return [_normalize(n, [symbol], "company") for n in news]
    except Exception as e:
        print(f"⚠️ Error fetching news for {symbol}: {e}")
        return []


def fetch_market_news(hours: int = 24, symbols=SYMBOLS) -> list:
    """Fetch general market news for the past `hours`, keeping market-relevant items only."""
    try:
        cutoff = int((datetime.now(timezone.utc) - timedelta(hours=hours)).timestamp())
        general_news = get_client().general_news('general', min_id=0)
        recent = [n for n in general_news if n.get('datetime', 0) >= cutoff]
        recent.sort(key=lambda x: x.get('datetime', 0), reverse=True)
        return [
            _normalize(n, _related_symbols(n, symbols), "market")
            for n in recent
            if is_relevant_market_news(n, symbols)
        ]
    except Exception as e:
        print(f"⚠️ Error fetching general market news: {e}")
        return []
