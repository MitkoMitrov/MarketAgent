"""Tests for engine.market_data (fake Finnhub client, no network).
Run: python -m unittest tests.test_market_data
"""
import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from engine import market_data
from engine.market_data import fetch_stocks, format_market_cap


class FakeClient:
    def __init__(self, fail_profile=False):
        self.calls = []
        self.fail_profile = fail_profile

    def quote(self, symbol):
        self.calls.append(("quote", symbol))
        return {"c": 100.0, "d": 2.0, "dp": 2.04, "h": 101.0, "l": 97.0, "o": 98.0, "pc": 98.0, "t": 1}

    def company_profile2(self, symbol):
        self.calls.append(("profile", symbol))
        if self.fail_profile:
            raise RuntimeError("429")
        return {"name": f"{symbol} Inc", "finnhubIndustry": "Semiconductors", "marketCapitalization": 1_501_178.4,
                "logo": "https://example.com/logo.png"}

    def company_basic_financials(self, symbol, metric):
        self.calls.append(("financials", symbol))
        return {"metric": {"peBasicExclExtraTTM": 45.2, "52WeekHigh": 150.0, "52WeekLow": 80.0, "beta": 1.5,
                           "10DayAverageTradingVolume": 38.4, "unused": 1}}

    def earnings_calendar(self, _from, to, symbol):
        self.calls.append(("earnings", symbol))
        soon = (date.today() + timedelta(days=3)).isoformat()
        return {"earningsCalendar": [{"date": soon, "hour": "amc", "quarter": 4, "year": 2026,
                                      "epsEstimate": 0.46, "revenueEstimate": 29.6e9, "symbol": symbol}]}


def kinds(client):
    return [c[0] for c in client.calls]


class MarketDataTests(unittest.TestCase):
    def test_market_cap_is_in_millions(self):
        self.assertEqual(format_market_cap(1_501_178.4), "$1.50T")
        self.assertEqual(format_market_cap(40_757.2), "$40.76B")
        self.assertEqual(format_market_cap(512), "$512M")
        self.assertEqual(format_market_cap(0), "N/A")

    def test_record_and_slow_data_cache(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(market_data, "get_client", return_value=client):
            cache = Path(tmp) / "meta.json"
            stocks, earnings = fetch_stocks(["NVDA", "AMD"], cache_path=cache, with_earnings=True)
            self.assertEqual(list(stocks), ["NVDA", "AMD"])
            nvda = stocks["NVDA"]
            self.assertEqual((nvda["price"], nvda["change_percent"], nvda["pe_ratio"]), (100.0, 2.04, 45.2))
            self.assertEqual((nvda["name"], nvda["market_cap"], nvda["volume"]), ("NVDA Inc", 1_501_178.4, 38.4))
            self.assertEqual([e["symbol"] for e in earnings], ["AMD", "NVDA"])  # same date: by symbol
            self.assertEqual(earnings[0]["hour"], "amc")
            # Only the fields we use are cached.
            self.assertNotIn("logo", json.loads(cache.read_text())["NVDA"]["m"]["profile"])

            # Second run: quotes again, everything else from the cache.
            client.calls.clear()
            stocks2, earnings2 = fetch_stocks(["NVDA", "AMD"], cache_path=cache, with_earnings=True)
            self.assertEqual(kinds(client), ["quote", "quote"])
            self.assertEqual(stocks2["NVDA"]["pe_ratio"], 45.2)
            self.assertEqual(len(earnings2), 2)

    def test_failed_profile_is_not_cached_and_keeps_old_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp) / "meta.json"
            with mock.patch.object(market_data, "get_client", return_value=FakeClient()):
                fetch_stocks(["NVDA"], cache_path=cache)
            # Expire the cache, then fail the profile call: old name/market cap stay.
            data = json.loads(cache.read_text())
            data["NVDA"]["t"] = 0
            cache.write_text(json.dumps(data))
            failing = FakeClient(fail_profile=True)
            with mock.patch.object(market_data, "get_client", return_value=failing):
                stocks, _ = fetch_stocks(["NVDA"], cache_path=cache)
            self.assertEqual(stocks["NVDA"]["name"], "NVDA Inc")
            self.assertEqual(json.loads(cache.read_text())["NVDA"]["t"], 0)  # not overwritten
            # Next run retries.
            with mock.patch.object(market_data, "get_client", return_value=failing):
                fetch_stocks(["NVDA"], cache_path=cache)
            self.assertIn("profile", kinds(failing)[2:])


if __name__ == "__main__":
    unittest.main()
