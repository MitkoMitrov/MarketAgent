"""
US market and economy overview for the news site (Finnhub free tier only).

Every run (30 min): market status + quotes for index, sector and macro ETFs and crypto.
Cached (SlowCache): market holidays, IPO calendar, market-wide earnings calendar, FDA
advisory committee calendar.

Finnhub's free plan has no index, bond-yield, forex or commodity quotes, so widely traded
ETFs stand in for them (labelled as such on the page): e.g. SPY for the S&P 500, TLT for
long-term Treasuries, GLD for gold, UUP for the US dollar.
"""
from datetime import date, timedelta

from engine.finnhub_client import api_get

INDICES = [
    ("SPY", "S&P 500"), ("DIA", "Dow Jones"), ("QQQ", "Nasdaq 100"), ("IWM", "Russell 2000"),
    ("VIXY", "Volatility (VIX futures)"),
]
SECTORS = [
    ("XLK", "Technology"), ("XLC", "Communication"), ("XLY", "Consumer Discretionary"),
    ("XLP", "Consumer Staples"), ("XLE", "Energy"), ("XLF", "Financials"), ("XLV", "Health Care"),
    ("XLI", "Industrials"), ("XLB", "Materials"), ("XLRE", "Real Estate"), ("XLU", "Utilities"),
]
ECONOMY = [
    ("rates", "Interest rates (Treasury bond ETFs)",
     "Bond prices move opposite to yields: bonds up means rates are falling.",
     [("SHY", "1–3 year Treasuries"), ("IEF", "7–10 year Treasuries"), ("TLT", "20+ year Treasuries")]),
    ("commodities", "Commodities", "",
     [("GLD", "Gold"), ("SLV", "Silver"), ("USO", "Crude oil"), ("UNG", "Natural gas")]),
    ("currency", "US dollar", "Dollar strength against a basket of major currencies.",
     [("UUP", "US Dollar Index")]),
    ("crypto", "Crypto", "", [("COINBASE:BTC-USD", "Bitcoin"), ("COINBASE:ETH-USD", "Ethereum")]),
    ("volatility", "Fear gauge", "Rises when investors expect bigger market swings.",
     [("VIXY", "VIX short-term futures")]),
]

CALENDAR_TTL_S = 6 * 3600
HOLIDAYS_TTL_S = 24 * 3600
BIG_COMPANY_REVENUE = 1e9  # market-wide earnings: companies expecting ≥ $1B quarterly revenue
EARNINGS_WEEK_DAYS = 7


def _quote(symbol: str, known: dict):
    if symbol in known:
        return known[symbol]
    try:
        q = api_get("/quote", symbol=symbol)
    except Exception as e:
        print(f"⚠️ quote {symbol}: {e}")
        return None
    if not q or not q.get("c"):
        return None
    known[symbol] = {"price": q.get("c"), "change": q.get("d"), "change_percent": q.get("dp"),
                     "high": q.get("h"), "low": q.get("l"), "previous_close": q.get("pc"), "time": q.get("t")}
    return known[symbol]


def _tiles(pairs, known):
    out = []
    for symbol, name in pairs:
        q = _quote(symbol, known)
        if q:
            out.append(dict(q, symbol=symbol.split(":")[-1], name=name))
    return out


def market_status() -> dict:
    try:
        s = api_get("/stock/market-status", exchange="US")
        return {"is_open": bool(s.get("isOpen")), "session": s.get("session"), "holiday": s.get("holiday"), "time": s.get("t")}
    except Exception as e:
        print(f"⚠️ market status: {e}")
        return {}


def _holidays():
    today = date.today().isoformat()
    rows = api_get("/stock/market-holiday", exchange="US").get("data") or []
    rows = [{"name": r.get("eventName", ""), "date": r.get("atDate", ""), "hours": r.get("tradingHour", "")}
            for r in rows if (r.get("atDate") or "") >= today]
    return sorted(rows, key=lambda r: r["date"])[:8]


def _ipos():
    today = date.today()
    rows = api_get("/calendar/ipo", **{"from": (today - timedelta(days=14)).isoformat(),
                                        "to": (today + timedelta(days=45)).isoformat()}).get("ipoCalendar") or []
    out = [{"date": r.get("date", ""), "symbol": r.get("symbol") or "", "name": r.get("name") or "",
            "exchange": r.get("exchange") or "", "price": r.get("price") or "", "shares": r.get("numberOfShares"),
            "value": r.get("totalSharesValue"), "status": r.get("status") or ""}
           for r in rows if r.get("status") != "withdrawn" and r.get("name")]
    return sorted(out, key=lambda r: r["date"])


def _earnings_week():
    today = date.today()
    rows = api_get("/calendar/earnings", **{"from": today.isoformat(),
                                             "to": (today + timedelta(days=EARNINGS_WEEK_DAYS)).isoformat()}
                   ).get("earningsCalendar") or []
    out = [{"symbol": r.get("symbol"), "date": r.get("date"), "hour": r.get("hour") or "",
            "eps_estimate": r.get("epsEstimate"), "revenue_estimate": r.get("revenueEstimate"),
            "quarter": r.get("quarter"), "year": r.get("year")}
           for r in rows if (r.get("revenueEstimate") or 0) >= BIG_COMPANY_REVENUE and r.get("symbol")]
    return sorted(out, key=lambda r: (r["date"], -(r["revenue_estimate"] or 0)))


def _fda():
    today = date.today().isoformat()
    rows = api_get("/fda-advisory-committee-calendar") or []
    out = [{"start": r.get("fromDate", ""), "end": r.get("toDate", ""), "title": r.get("eventDescription", ""),
            "url": r.get("url", "")} for r in rows if (r.get("toDate") or r.get("fromDate") or "") >= today]
    return sorted(out, key=lambda r: r["start"])[:20]


def fetch_overview(cache, known_quotes: dict = None) -> dict:
    """known_quotes: {symbol: quote} already fetched this run (e.g. QQQ from the watchlist)."""
    known = dict(known_quotes or {})
    print("  → market status, indices, sectors, macro ETFs...")
    return {
        "status": market_status(),
        "indices": _tiles(INDICES, known),
        "sectors": _tiles(SECTORS, known),
        "economy": [{"id": gid, "title": title, "hint": hint, "tiles": _tiles(pairs, known)}
                    for gid, title, hint, pairs in ECONOMY],
        "holidays": cache.get("market:holidays", HOLIDAYS_TTL_S, _holidays) or [],
        "ipos": cache.get("market:ipos", CALENDAR_TTL_S, _ipos) or [],
        "earnings_week": cache.get("market:earnings_week", CALENDAR_TTL_S, _earnings_week) or [],
        "fda": cache.get("market:fda", HOLIDAYS_TTL_S, _fda) or [],
    }
