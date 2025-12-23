# engine/report_engine.py
import json
from pathlib import Path

DATA_DIR = Path("data/snapshots")


def load_latest_market_snapshot():
    """Load the latest market snapshot JSON file from the snapshots directory."""
    files = sorted(DATA_DIR.glob("market_snapshot-*.json"), reverse=True)
    if not files:
        raise FileNotFoundError("No market snapshot files found in data/snapshots/")
    latest_file = files[0]
    with open(latest_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data, latest_file.name


def _normalize_stocks(snapshot):
    """Return a list of stock dicts with keys: symbol, price, change_percent.

    Supports two shapes:
    - snapshot["stocks"] as a dict: {SYMBOL: {price, change_percent, ...}}
    - snapshot["top_movers"] as a list: [{symbol, price, change_percent, ...}]
    """
    stocks = snapshot.get("stocks")
    if isinstance(stocks, dict):
        return [
            {
                "symbol": sym,
                "price": info.get("price") or info.get("c"),
                "change_percent": info.get("change_percent") or info.get("dp", 0.0),
            }
            for sym, info in stocks.items()
        ]
    if isinstance(stocks, list):
        return [
            {
                "symbol": s.get("symbol"),
                "price": s.get("price") or s.get("Price"),
                "change_percent": s.get("change_percent") or s.get("Change%", 0.0),
            }
            for s in stocks
        ]
    movers = snapshot.get("top_movers", [])
    if isinstance(movers, list):
        return [
            {
                "symbol": s.get("symbol"),
                "price": s.get("price"),
                "change_percent": s.get("change_percent", 0.0),
            }
            for s in movers
        ]
    return []


def analyze_market_snapshot(snapshot):
    """
    Generate a structured summary of the snapshot:
    - Top gainers/losers
    - Summary statistics
    - Basic insights
    """
    stocks = _normalize_stocks(snapshot)
    if not stocks:
        return {
            "total_stocks": 0,
            "avg_change": 0.0,
            "top_gainers": [],
            "top_losers": [],
        }

    sorted_stocks = sorted(stocks, key=lambda x: x.get("change_percent", 0.0), reverse=True)
    top_gainers = sorted_stocks[:5]
    top_losers = sorted_stocks[-5:]

    avg_change = sum(s.get("change_percent", 0.0) for s in stocks) / len(stocks)

    analysis = {
        "total_stocks": len(stocks),
        "avg_change": avg_change,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
    }
    return analysis


def generate_market_report(snapshot):
    """Produce a readable market report string from a snapshot.

    Designed to work with the mock snapshot in tests and the Finnhub snapshot.
    """
    session = snapshot.get("market_session") or snapshot.get("session", "unknown")
    lines = [f"📊 Market Report — Session: {session}"]

    indices = snapshot.get("major_index_moves", {})
    if indices:
        lines.append("\n📈 Major Indices:")
        for idx, move in indices.items():
            try:
                lines.append(f"- {idx}: {float(move):+.2f}%")
            except Exception:
                lines.append(f"- {idx}: {move}")

    stocks = _normalize_stocks(snapshot)
    if stocks:
        sorted_stocks = sorted(stocks, key=lambda x: x.get("change_percent", 0.0), reverse=True)
        top = sorted_stocks[:5]
        bottom = sorted_stocks[-5:]
        lines.append("\n🔼 Top Movers:")
        for s in top:
            lines.append(f"- {s['symbol']}: {s['price']} ({s['change_percent']:+.2f}%)")
        lines.append("\n🔽 Bottom Movers:")
        for s in bottom:
            lines.append(f"- {s['symbol']}: {s['price']} ({s['change_percent']:+.2f}%)")

    macro_events = snapshot.get("macro_events", [])
    if macro_events:
        lines.append("\n📰 Macro Events:")
        for e in macro_events:
            title = e.get("title")
            source = e.get("source")
            lines.append(f"- {title} ({source})")

    news_items = snapshot.get("news", [])
    if news_items:
        lines.append("\n🗞 News:")
        for n in news_items[:5]:
            lines.append(f"- {n.get('headline')} — {n.get('source')}")

    return "\n".join(lines)
