"""
Stock data for the watchlist: quote, company profile, key metrics and upcoming earnings.

Used by the daily snapshot (finnhub_scripts.fetch_and_store, shown in Telegram) and by the
news site, so both show the same numbers. Quotes are always fetched fresh; profile, metrics
and earnings change slowly, so callers can pass a cache file to fetch them at most every
META_TTL_S (the site rebuilds every 30 minutes and Finnhub's free tier allows 60 calls/min).

Units follow Finnhub: market_cap is in millions of USD, volume (10-day average) in millions
of shares.
"""
import json
import time
from datetime import date, timedelta
from pathlib import Path

from engine.finnhub_client import get_client, throttle

META_TTL_S = 12 * 3600
EARNINGS_DAYS_AHEAD = 120      # far enough to include every stock's next quarterly report

_PROFILE_KEYS = ("name", "finnhubIndustry", "marketCapitalization")
_METRIC_KEYS = ("peBasicExclExtraTTM", "52WeekHigh", "52WeekLow", "beta", "10DayAverageTradingVolume")


def _call(what: str, symbol: str, fn):
    try:
        throttle()
        return fn() or {}
    except Exception as e:
        print(f"⚠️ Error fetching {what} for {symbol}: {e}")
        return None  # None = failed (don't cache); {} = empty answer


def _fetch_earnings(symbol: str, days_ahead: int):
    today = date.today()
    res = _call("earnings", symbol, lambda: get_client().earnings_calendar(
        _from=today.isoformat(), to=(today + timedelta(days=days_ahead)).isoformat(), symbol=symbol))
    if res is None:
        return None
    return [
        {
            "symbol": symbol,
            "date": e.get("date"),
            "hour": e.get("hour") or "",           # bmo = before open, amc = after close
            "quarter": e.get("quarter"),
            "year": e.get("year"),
            "eps_estimate": e.get("epsEstimate"),
            "revenue_estimate": e.get("revenueEstimate"),
        }
        for e in res.get("earningsCalendar", [])
        if e.get("date")
    ]


def _fetch_meta(symbol: str, with_earnings: bool):
    profile = _call("profile", symbol, lambda: get_client().company_profile2(symbol=symbol))
    metrics = _call("financials", symbol, lambda: get_client().company_basic_financials(symbol, "all"))
    earnings = _fetch_earnings(symbol, EARNINGS_DAYS_AHEAD) if with_earnings else []
    metric = (metrics or {}).get("metric") or {}
    meta = {
        "profile": {k: (profile or {})[k] for k in _PROFILE_KEYS if k in (profile or {})},
        "metric": {k: metric[k] for k in _METRIC_KEYS if k in metric},
        "earnings": earnings or [],
    }
    complete = profile is not None and metrics is not None and earnings is not None
    return meta, complete


def _load_cache(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def stock_record(symbol: str, quote: dict, meta: dict) -> dict:
    profile, metric = meta.get("profile", {}), meta.get("metric", {})
    return {
        "price": quote.get("c") or 0,
        "change": quote.get("d") or 0,
        "change_percent": quote.get("dp") or 0,
        "high": quote.get("h") or 0,
        "low": quote.get("l") or 0,
        "open": quote.get("o") or 0,
        "previous_close": quote.get("pc") or 0,
        "quote_time": quote.get("t") or 0,
        "name": profile.get("name", symbol),
        "industry": profile.get("finnhubIndustry", "N/A"),
        "market_cap": profile.get("marketCapitalization", 0),
        "pe_ratio": metric.get("peBasicExclExtraTTM"),
        "52_week_high": metric.get("52WeekHigh"),
        "52_week_low": metric.get("52WeekLow"),
        "beta": metric.get("beta"),
        "volume": metric.get("10DayAverageTradingVolume"),
    }


def fetch_stocks(symbols, cache_path=None, with_earnings=False):
    """Return (stocks, earnings).

    stocks:   {symbol: stock_record(...)} in watchlist order.
    earnings: upcoming earnings for the next EARNINGS_DAYS_AHEAD days, soonest first
              (only when with_earnings=True).
    """
    cache = _load_cache(cache_path) if cache_path else {}
    now = time.time()
    stocks, earnings, cache_changed = {}, [], False

    for symbol in symbols:
        print(f"  → {symbol} quote & metrics...")
        quote = _call("quote", symbol, lambda: get_client().quote(symbol)) or {}

        cached = cache.get(symbol)
        fresh = cached and now - cached.get("t", 0) < META_TTL_S and (cached.get("e") or not with_earnings)
        if fresh:
            meta = cached["m"]
        else:
            meta, complete = _fetch_meta(symbol, with_earnings)
            if complete:
                cache[symbol] = {"t": now, "e": with_earnings, "m": meta}
                cache_changed = True
            elif cached:  # keep the last good values over a partial failure
                meta = {k: meta[k] or cached["m"].get(k, v) for k, v in meta.items()}

        stocks[symbol] = stock_record(symbol, quote, meta)
        earnings += meta.get("earnings", [])

    if cache_path and cache_changed:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        Path(cache_path).write_text(json.dumps(cache), encoding="utf-8")

    today = date.today().isoformat()
    earnings = sorted((e for e in earnings if e["date"] >= today), key=lambda e: (e["date"], e["symbol"]))
    return stocks, earnings


def format_market_cap(millions) -> str:
    """Finnhub reports market cap in millions of USD: 1501178 → '$1.50T'."""
    if not millions:
        return "N/A"
    if millions >= 1_000_000:
        return f"${millions / 1_000_000:.2f}T"
    if millions >= 1_000:
        return f"${millions / 1_000:.2f}B"
    return f"${millions:.0f}M"
