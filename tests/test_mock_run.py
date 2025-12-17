from datetime import datetime, timezone
from engine.report_engine import generate_market_report

mock_snapshot = {
    "snapshot_time": datetime.now(timezone.utc).isoformat(),
    "market_session": "post-market",
    "major_index_moves": {
        "SPY": -1.1,
        "QQQ": -1.6
    },
    "top_movers": [
        {
            "symbol": "TSLA",
            "price": 248.30,
            "change_percent": -5.12,
            "volume": 138000000,
            "market_cap": 790000000000,
            "reason_hint": "Q4 vehicle delivery numbers released below consensus estimates"
        },
        {
            "symbol": "AMD",
            "price": 162.40,
            "change_percent": 3.05,
            "volume": 72000000,
            "market_cap": 262000000000,
            "reason_hint": "Reports of reduced US tariffs on select semiconductor exports to China"
        }
    ],
    "macro_events": [
        {
            "title": "US-China trade policy adjustment",
            "source": "Reuters",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "affected_sectors": ["Semiconductors"],
            "factual_summary": "US administration announced reduced tariffs on certain technology exports to China"
        }
    ],
    "news": [
        {
            "headline": "Tesla deliveries miss expectations",
            "source": "Bloomberg",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": ["TSLA"],
            "summary": "Tesla reported quarterly deliveries slightly below Wall Street estimates"
        }
    ]
}

if __name__ == "__main__":
    report = generate_market_report(mock_snapshot)
    print("\n=== MARKET REPORT ===\n")
    print(report)
