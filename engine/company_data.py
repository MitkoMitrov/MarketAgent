"""
Company detail data for the news site (all on Finnhub's free tier, cached for COMPANY_TTL_S):

  insider trades (SEC Form 4) and insider sentiment (MSPR), analyst recommendation trends,
  earnings surprises, peers, SEC filings, quarterly financials (from SEC XBRL), lobbying,
  H-1B visa applications and US government contracts.

Every fetcher returns small, already-summarised JSON so the cache and the page stay light.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import median

from engine.finnhub_client import api_get

COMPANY_TTL_S = 12 * 3600
# SEC-based data (insiders, filings, financials, lobbying, H-1B, contracts) is filed under one
# share class: Alphabet's under GOOGL, so GOOG needs the alias.
SEC_ALIASES = {"GOOG": "GOOGL"}
INSIDER_DAYS = 90
FILINGS_DAYS = 120
MAX_TRADES = 60
MAX_FILINGS = 25

INSIDER_CODES = {
    "P": "Buy", "S": "Sale", "M": "Option exercise", "X": "Option exercise", "C": "Conversion",
    "A": "Grant / award", "F": "Tax withholding", "G": "Gift", "D": "Returned to company",
    "J": "Other", "W": "Inheritance", "I": "Discretionary", "K": "Equity swap", "V": "Voluntary report",
}

FORM_LABELS = {
    "8-K": "Major event", "8-K/A": "Major event (amended)", "10-Q": "Quarterly report",
    "10-K": "Annual report", "10-K/A": "Annual report (amended)", "4": "Insider trade",
    "4/A": "Insider trade (amended)", "3": "New insider", "5": "Insider trades (annual)",
    "144": "Planned insider sale", "13F-HR": "Fund holdings", "N-PX": "Proxy votes",
    "DEF 14A": "Proxy statement", "S-8": "Employee stock plan", "S-3": "Securities offering",
    "SC 13G": "5%+ shareholder", "SC 13G/A": "5%+ shareholder", "SC 13D": "5%+ activist stake",
    "SCHEDULE 13G": "5%+ shareholder", "SCHEDULE 13G/A": "5%+ shareholder", "SCHEDULE 13D": "5%+ activist stake",
    "SCHEDULE 13D/A": "5%+ activist stake", "DEFA14A": "Proxy material", "PX14A6G": "Shareholder proxy note",
    "10-Q/A": "Quarterly report (amended)", "S-3ASR": "Securities offering", "FWP": "Offering terms",
    "424B2": "Offering prospectus", "424B5": "Offering prospectus", "11-K": "Employee plan report",
}

_REVENUE = ("us-gaap_Revenues", "us-gaap_RevenueFromContractWithCustomerExcludingAssessedTax",
            "us-gaap_SalesRevenueNet", "us-gaap_RevenueFromContractWithCustomerIncludingAssessedTax")
_GROSS = ("us-gaap_GrossProfit",)
_COST = ("us-gaap_CostOfRevenue", "us-gaap_CostOfGoodsAndServicesSold")
_OPERATING = ("us-gaap_OperatingIncomeLoss",)
_NET = ("us-gaap_NetIncomeLoss", "us-gaap_ProfitLoss", "us-gaap_NetIncomeLossAvailableToCommonStockholdersBasic")


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def _name(raw: str) -> str:
    return " ".join(w.capitalize() if w.isupper() else w for w in (raw or "").split())


# ---------- insiders ----------

def insider_trades(symbol: str) -> dict:
    rows = api_get("/stock/insider-transactions", symbol=symbol, **{"from": _days_ago(INSIDER_DAYS)}).get("data") or []
    trades = []
    for x in rows:
        code = x.get("transactionCode") or ""
        shares = x.get("change") or 0
        price = x.get("transactionPrice") or 0
        trades.append({
            "name": _name(x.get("name", "")),
            "date": x.get("transactionDate") or x.get("filingDate") or "",
            "filed": x.get("filingDate") or "",
            "code": code,
            "type": INSIDER_CODES.get(code, code or "Other"),
            "shares": shares,
            "price": price,
            "value": round(abs(shares) * price),
            "held_after": x.get("share"),
            "derivative": bool(x.get("isDerivative")),
        })
    trades.sort(key=lambda t: (t["date"], t["filed"]), reverse=True)
    buys = [t for t in trades if t["code"] == "P"]
    sells = [t for t in trades if t["code"] == "S"]
    summary = {
        "days": INSIDER_DAYS,
        "buys": len(buys), "sells": len(sells),
        "buy_value": sum(t["value"] for t in buys), "sell_value": sum(t["value"] for t in sells),
        "buyers": len({t["name"] for t in buys}), "sellers": len({t["name"] for t in sells}),
        "transactions": len(trades),
    }
    summary["net_value"] = summary["buy_value"] - summary["sell_value"]
    return {"summary": summary, "trades": trades[:MAX_TRADES]}


def insider_sentiment(symbol: str) -> list:
    rows = api_get("/stock/insider-sentiment", symbol=symbol,
                   **{"from": _days_ago(400), "to": date.today().isoformat()}).get("data") or []
    out = [{"month": f"{r['year']}-{r['month']:02d}", "mspr": round(r.get("mspr") or 0, 1), "change": r.get("change") or 0}
           for r in rows if r.get("year") and r.get("month")]
    return sorted(out, key=lambda r: r["month"])[-12:]


# ---------- analysts & earnings ----------

def recommendations(symbol: str) -> list:
    rows = api_get("/stock/recommendation", symbol=symbol) or []
    rows = sorted(rows, key=lambda r: r.get("period", ""), reverse=True)[:6]
    return [{"period": r.get("period"), "strong_buy": r.get("strongBuy", 0), "buy": r.get("buy", 0),
             "hold": r.get("hold", 0), "sell": r.get("sell", 0), "strong_sell": r.get("strongSell", 0)} for r in rows]


def earnings_surprises(symbol: str) -> list:
    rows = api_get("/stock/earnings", symbol=symbol) or []
    rows = sorted(rows, key=lambda r: r.get("period", ""), reverse=True)[:4]
    return [{"period": r.get("period"), "year": r.get("year"), "quarter": r.get("quarter"),
             "actual": r.get("actual"), "estimate": r.get("estimate"),
             "surprise_pct": None if r.get("surprisePercent") is None else round(r["surprisePercent"], 2)}
            for r in rows]


def peers(symbol: str) -> list:
    seen, out = {symbol, *[a for k, a in SEC_ALIASES.items() if k == symbol]}, []
    for p in api_get("/stock/peers", symbol=symbol) or []:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return out[:10]


# ---------- filings & financials ----------

def filings(symbol: str) -> list:
    rows = api_get("/stock/filings", symbol=symbol, **{"from": _days_ago(FILINGS_DAYS)}) or []
    rows = sorted(rows, key=lambda r: r.get("acceptedDate", ""), reverse=True)[:MAX_FILINGS]
    return [{"form": r.get("form", ""), "label": FORM_LABELS.get(r.get("form", ""), ""),
             "date": (r.get("filedDate") or "")[:10], "url": r.get("filingUrl") or r.get("reportUrl") or ""}
            for r in rows]


def _value(report: dict, concepts, largest=False):
    items = report.get("ic") or []
    for concept in concepts:
        vals = [x.get("value") for x in items if x.get("concept") == concept and isinstance(x.get("value"), (int, float))]
        if vals:
            return max(vals) if largest else vals[0]
    return None


def _statement_values(report: dict) -> dict:
    revenue = _value(report, _REVENUE, largest=True)
    gross = _value(report, _GROSS)
    if gross is None and revenue is not None:
        cost = _value(report, _COST, largest=True)
        gross = None if cost is None else revenue - cost
    return {"revenue": revenue, "gross_profit": gross,
            "operating_income": _value(report, _OPERATING), "net_income": _value(report, _NET)}


def quarterly_financials(symbol: str, quarters: int = 8) -> list:
    """Per-quarter revenue / gross profit / operating income / net income.

    10-Q income statements are year-to-date, so each quarter = YTD minus the previous YTD of
    the same fiscal year; Q4 = annual (10-K) minus the Q3 year-to-date figure."""
    filings_ = []
    for freq in ("quarterly", "annual"):
        for r in (api_get("/stock/financials-reported", symbol=symbol, freq=freq).get("data") or [])[:12]:
            filings_.append({"start": (r.get("startDate") or "")[:10], "end": (r.get("endDate") or "")[:10],
                             "year": r.get("year"), "quarter": r.get("quarter") if freq == "quarterly" else 4,
                             "values": _statement_values(r.get("report") or {})})

    by_year = defaultdict(list)
    for f in filings_:
        if f["start"] and f["end"]:
            by_year[f["start"]].append(f)

    out = []
    for start, items in by_year.items():
        items.sort(key=lambda f: f["end"])
        prev = None
        for f in items:
            since = prev["end"] if prev else start
            months = (date.fromisoformat(f["end"]) - date.fromisoformat(since)).days / 30.4
            if months > 4:
                prev = f  # the previous quarter is missing: can't split the YTD figure
                continue
            row = {"period": f["end"], "year": f["year"], "quarter": f["quarter"]}
            for k, v in f["values"].items():
                pv = prev["values"].get(k) if prev else 0
                row[k] = None if v is None or pv is None else v - pv
            out.append(row)
            prev = f

    out = [r for r in out if r.get("revenue") is not None or r.get("net_income") is not None]
    out.sort(key=lambda r: r["period"], reverse=True)
    if out and out[0]["period"] < (date.today() - timedelta(days=400)).isoformat():
        return []  # stale data (wrong share class / no longer filing)
    out = out[:quarters]
    for r in out:
        rev = r.get("revenue")
        r["gross_margin"] = round(100 * r["gross_profit"] / rev, 1) if rev and r.get("gross_profit") is not None else None
        r["operating_margin"] = round(100 * r["operating_income"] / rev, 1) if rev and r.get("operating_income") is not None else None
        r["net_margin"] = round(100 * r["net_income"] / rev, 1) if rev and r.get("net_income") is not None else None
    # Year-over-year revenue growth when the same quarter a year earlier is available.
    by_q = {(r["year"], r["quarter"]): r for r in out}
    for r in out:
        last = by_q.get((r["year"] - 1, r["quarter"])) if r.get("year") else None
        r["revenue_yoy"] = (round(100 * (r["revenue"] / last["revenue"] - 1), 1)
                            if last and r.get("revenue") and last.get("revenue") else None)
    return out


# ---------- lobbying, H-1B, government contracts ----------

def lobbying(symbol: str) -> dict:
    rows = api_get("/stock/lobbying", symbol=symbol,
                   **{"from": _days_ago(730), "to": date.today().isoformat()}).get("data") or []
    per_q = defaultdict(float)
    for r in rows:
        amount = r.get("income") or r.get("expenses") or 0
        if r.get("year") and r.get("period"):
            per_q[f"{r['year']} {r['period']}"] += amount
    quarters = sorted(per_q.items(), reverse=True)[:8]
    latest = max(rows, key=lambda r: (r.get("year") or 0, r.get("period") or ""), default=None)
    return {
        "quarters": [{"period": k, "amount": round(v)} for k, v in quarters],
        "last_4q": round(sum(v for _, v in quarters[:4])),
        "filings": len(rows),
        "description": (latest or {}).get("description", ""),
        "latest_url": (latest or {}).get("documentUrl", ""),
    }


def visa_applications(symbol: str) -> dict:
    rows = api_get("/stock/visa-application", symbol=symbol,
                   **{"from": _days_ago(365), "to": date.today().isoformat()}).get("data") or []
    titles = Counter(_name(r.get("jobTitle", "")).strip() for r in rows if r.get("jobTitle"))
    states = Counter(r.get("worksiteState") for r in rows if r.get("worksiteState"))
    wages = [r["wageRangeFrom"] for r in rows
             if (r.get("wageUnitOfPay") or "").lower().startswith("year") and (r.get("wageRangeFrom") or 0) > 0]
    by_q = Counter(f"{r['year']} Q{r['quarter']}" for r in rows if r.get("year") and r.get("quarter"))
    return {
        "count": len(rows),
        "capped": len(rows) >= 500,  # Finnhub returns at most 500 rows
        "certified": sum(1 for r in rows if (r.get("caseStatus") or "").lower().startswith("certified")),
        "median_wage": round(median(wages)) if wages else None,
        "top_titles": titles.most_common(6),
        "top_states": states.most_common(5),
        "by_quarter": sorted(by_q.items()),
    }


def government_contracts(symbol: str) -> dict:
    rows = api_get("/stock/usa-spending", symbol=symbol,
                   **{"from": _days_ago(730), "to": date.today().isoformat()}).get("data") or []
    rows = sorted(rows, key=lambda r: r.get("totalValue") or 0, reverse=True)
    return {
        "count": len(rows),
        "total": round(sum(r.get("totalValue") or 0 for r in rows)),
        "top": [{"agency": r.get("awardingAgencyName", ""), "office": r.get("awardingOfficeName", ""),
                 "recipient": r.get("recipientName", ""), "amount": r.get("totalValue") or 0,
                 "date": r.get("actionDate", ""), "description": r.get("awardDescription") or r.get("naicsDescription") or "",
                 "url": r.get("permalink", "")} for r in rows[:6]],
    }


SEC_SECTIONS = {"insiders", "insider_sentiment", "filings", "financials", "lobbying", "h1b", "gov_contracts"}

SECTIONS = {
    "insiders": insider_trades,
    "insider_sentiment": insider_sentiment,
    "analysts": recommendations,
    "earnings_history": earnings_surprises,
    "peers": peers,
    "filings": filings,
    "financials": quarterly_financials,
    "lobbying": lobbying,
    "h1b": visa_applications,
    "gov_contracts": government_contracts,
}


def fetch_company_details(symbol: str, cache) -> dict:
    """All sections for one company; each section is cached separately in `cache` (SlowCache)."""
    print(f"  → {symbol} company details...")
    out = {}
    for name, fn in SECTIONS.items():
        sym = SEC_ALIASES.get(symbol, symbol) if name in SEC_SECTIONS else symbol
        out[name] = cache.get(f"company:{sym}:{name}", COMPANY_TTL_S, lambda fn=fn, sym=sym: fn(sym))
    return out


def card_summary(details: dict) -> dict:
    """The few numbers shown on the watchlist card."""
    analysts = (details.get("analysts") or [None])[0]
    insiders = (details.get("insiders") or {}).get("summary")
    sentiment = details.get("insider_sentiment") or []
    return {
        "analysts": analysts,
        "earnings_history": details.get("earnings_history") or [],
        "insiders": insiders,
        "insider_mspr": sentiment[-1] if sentiment else None,
    }
