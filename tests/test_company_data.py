"""Tests for company details, market overview helpers and the slow cache (no network).
Run: python -m unittest tests.test_company_data
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from engine import company_data, market_overview
from engine.slow_cache import SlowCache


def statement(revenue, net, gross=None, cost=None):
    ic = [{"concept": "us-gaap_Revenues", "value": revenue}, {"concept": "us-gaap_NetIncomeLoss", "value": net}]
    if gross is not None:
        ic.append({"concept": "us-gaap_GrossProfit", "value": gross})
    if cost is not None:
        ic.append({"concept": "us-gaap_CostOfRevenue", "value": cost})
    return {"ic": ic}


def filing(start, end, year, quarter, report):
    return {"startDate": start + " 00:00:00", "endDate": end + " 00:00:00", "year": year, "quarter": quarter, "report": report}


class FinancialsTests(unittest.TestCase):
    def fake_api(self, quarterly, annual):
        def api_get(path, **params):
            return {"data": quarterly if params.get("freq") == "quarterly" else annual}
        return api_get

    def test_ytd_statements_become_quarters(self):
        # Fiscal year 2026: Q1 100, Q2 120, Q3 150, Q4 = 600 - 370 = 230 (10-Q figures are year-to-date).
        quarterly = [
            filing("2026-01-01", "2026-09-30", 2026, 3, statement(370, 37, cost=185)),
            filing("2026-01-01", "2026-06-30", 2026, 2, statement(220, 22, cost=110)),
            filing("2026-01-01", "2026-03-31", 2026, 1, statement(100, 10, cost=50)),
            filing("2025-01-01", "2025-09-30", 2025, 3, statement(240, 24, gross=120)),  # Q1-Q2 2025 missing
        ]
        annual = [filing("2026-01-01", "2026-12-31", 2026, 0, statement(600, 70, cost=300))]
        with mock.patch.object(company_data, "api_get", self.fake_api(quarterly, annual)), \
             mock.patch.object(company_data, "date", mock.Mock(today=lambda: __import__("datetime").date(2027, 1, 15),
                                                               fromisoformat=__import__("datetime").date.fromisoformat)):
            rows = company_data.quarterly_financials("X")
        self.assertEqual([(r["quarter"], r["revenue"], r["net_income"]) for r in rows],
                         [(4, 230, 33), (3, 150, 15), (2, 120, 12), (1, 100, 10)])
        self.assertEqual(rows[0]["gross_margin"], 50.0)  # revenue - cost of revenue
        self.assertEqual(rows[0]["net_margin"], 14.3)


class InsiderTests(unittest.TestCase):
    def test_summary_counts_only_open_market_trades(self):
        rows = [
            {"name": "DOE JOHN", "change": -1000, "transactionPrice": 50, "transactionCode": "S", "transactionDate": "2026-11-01"},
            {"name": "DOE JOHN", "change": -500, "transactionPrice": 52, "transactionCode": "S", "transactionDate": "2026-11-03"},
            {"name": "ROE JANE", "change": 200, "transactionPrice": 49, "transactionCode": "P", "transactionDate": "2026-10-01"},
            {"name": "ROE JANE", "change": 10000, "transactionPrice": 0, "transactionCode": "A", "transactionDate": "2026-10-02"},
        ]
        with mock.patch.object(company_data, "api_get", return_value={"data": rows}):
            out = company_data.insider_trades("X")
        s = out["summary"]
        self.assertEqual((s["sells"], s["sell_value"], s["sellers"]), (2, 76000, 1))
        self.assertEqual((s["buys"], s["buy_value"], s["net_value"]), (1, 9800, -66200))
        self.assertEqual(out["trades"][0]["date"], "2026-11-03")  # newest first
        self.assertEqual(out["trades"][0]["name"], "Doe John")
        self.assertEqual([t["type"] for t in out["trades"]][2:], ["Grant / award", "Buy"])

    def test_sec_alias_used_for_goog(self):
        cache = SlowCache()
        seen = []
        fake = {name: (lambda sym, name=name: seen.append((name, sym)) or []) for name in company_data.SECTIONS}
        with mock.patch.dict(company_data.SECTIONS, fake):
            company_data.fetch_company_details("GOOG", cache)
        self.assertIn(("filings", "GOOGL"), seen)
        self.assertIn(("analysts", "GOOG"), seen)


class SlowCacheTests(unittest.TestCase):
    def test_failure_returns_last_good_value_and_is_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            cache = SlowCache(path)
            self.assertEqual(cache.get("k", 3600, lambda: [1]), [1])
            cache.save()
            cache = SlowCache(path)
            self.assertEqual(cache.get("k", 3600, lambda: 1 / 0), [1])  # fresh: not refetched
            cache.data["k"]["t"] = 0  # expire
            self.assertEqual(cache.get("k", 3600, lambda: 1 / 0), [1])  # failed: old value kept
            self.assertEqual(cache.data["k"]["t"], 0)

    def test_overview_reuses_known_quotes(self):
        calls = []

        def api_get(path, **params):
            calls.append((path, params.get("symbol")))
            if path == "/quote":
                return {"c": 10, "d": 1, "dp": 11.1, "h": 10, "l": 9, "pc": 9, "t": 1}
            if path == "/stock/market-status":
                return {"isOpen": False, "session": "pre-market"}
            return {}
        with mock.patch.object(market_overview, "api_get", api_get):
            ov = market_overview.fetch_overview(SlowCache(), {"QQQ": {"price": 600, "change_percent": -0.7}})
        self.assertNotIn(("/quote", "QQQ"), calls)
        self.assertEqual(next(t for t in ov["indices"] if t["symbol"] == "QQQ")["price"], 600)
        self.assertEqual(ov["status"]["session"], "pre-market")
        self.assertEqual(len(ov["sectors"]), len(market_overview.SECTORS))
        self.assertEqual(ov["economy"][3]["tiles"][0]["symbol"], "BTC-USD")


if __name__ == "__main__":
    unittest.main()
