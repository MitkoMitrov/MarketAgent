"""Tests for AI curation, report storage and the site builder.
Run: python -m unittest tests.test_pipeline_parts
"""
import json
import tempfile
import unittest
from pathlib import Path

from engine.build_news_site import main as build_site
from engine.data_curator import NEWS_PER_STOCK, curate_for_ai, format_for_prompt
from engine.news_fetcher import clean_image_url
from engine.report_store import build_report_record, save_record


def news(symbol, headline, ts, summary="", url=None, image=""):
    return {"symbol": symbol, "headline": headline, "source": "Yahoo", "summary": summary,
            "url": url or f"https://example.com/{symbol}/{ts}", "image": image, "timestamp": ts}


class CurationTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {
            "market_session": "after-hours", "snapshot_time": "2026-11-18T21:30:00+00:00",
            "stocks": {"NVDA": {"name": "NVIDIA", "price": 190.5, "change_percent": 3.2},
                       "AMD": {"name": "AMD", "price": 150.0, "change_percent": -1.1}},
            "news": [news("NVDA", h, ts) for ts, h in enumerate([
                        "Nvidia opens a new research lab in Tokyo", "Analysts debate chip export rules",
                        "Data center spending keeps climbing", "Jensen Huang speaks at a robotics fair",
                        "Supplier shares jump on AI demand", "Options traders bet on volatility",
                        "Gaming GPU prices fall before holidays", "Cloud providers sign multi-year deals"])]
                    + [news("NVDA", h, 100 + i, url=f"https://x/{i}") for i, h in enumerate([
                        "Nvidia beats estimates and raises guidance",
                        "Nvidia beats estimates and raises its guidance",
                        "Nvidia beats estimates, raises guidance"])]
                    + [news("AMD", "Nvidia beats estimates and raises guidance", 50, url="https://x/0")],
        }

    def test_caps_stories_per_stock_and_dedupes(self):
        curated = curate_for_ai(self.snapshot)
        nvda = curated["news_by_stock"]["NVDA"]
        self.assertEqual(len(nvda), NEWS_PER_STOCK)
        headlines = [n["headline"] for n in nvda]
        self.assertEqual(len(headlines), len(set(headlines)))
        # The story covered 3 times comes first; its newest article is the headline.
        self.assertEqual(nvda[0]["headline"], "Nvidia beats estimates, raises guidance")
        self.assertEqual(nvda[0]["articles"], 3)
        # Same URL listed under AMD too: AMD gets the story as well.
        self.assertEqual(curated["news_by_stock"]["AMD"][0]["headline"], "Nvidia beats estimates, raises guidance")

    def test_prompt_mentions_coverage(self):
        prompt = format_for_prompt(curate_for_ai(self.snapshot))
        self.assertIn("Nvidia beats estimates, raises guidance (Yahoo, 3 articles)", prompt)
        self.assertIn("Cloud providers sign multi-year deals (Yahoo)\n", prompt)


class ImageTests(unittest.TestCase):
    def test_logo_and_insecure_images_are_dropped(self):
        self.assertEqual(clean_image_url("https://static2.finnhub.io/file/finnhub/logo/reuters_logo.jpeg"), "")
        self.assertEqual(clean_image_url("https://s.yimg.com/rz/stage/p/yahoo_finance_en-US_h_p_finance_2.png"), "")
        self.assertEqual(clean_image_url("http://example.com/a.jpg"), "")
        self.assertEqual(clean_image_url("https://cdn.example.com/photo.jpg"), "https://cdn.example.com/photo.jpg")


class TelegramCompanyInfoTests(unittest.TestCase):
    def test_market_cap_shown_in_trillions(self):
        from engine.telegram_formatter import format_company_info
        text = format_company_info({"stocks": {"TSLA": {
            "price": 380.11, "change": 0.37, "change_percent": 0.1, "high": 382.8, "low": 374.1,
            "pe_ratio": 445.8, "52_week_high": 498.8, "52_week_low": 297.4, "volume": 38.4,
            "market_cap": 1_501_178.4, "beta": 1.78}}})
        self.assertIn("*Market Cap:* $1.50T", text)


class ReportStoreTests(unittest.TestCase):
    def test_record_and_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            snaps = tmp / "snaps"
            snaps.mkdir()
            (snaps / "market_snapshot-20261118-213000.json").write_text(json.dumps({
                "snapshot_time": "2026-11-18T21:30:00+00:00",
                "stocks": {"NVDA": {"name": "NVIDIA", "price": 190.5, "change": 6.0, "change_percent": 3.2}},
            }), encoding="utf-8")
            report = tmp / "ai_report-20261118-213000.txt"
            report.write_text("AI Market Report\nGenerated: 20261118-213000\n"
                              "Source: market_snapshot-20261118-213000.json\n" + "=" * 60 + "\n\n📊 Executive Summary\nText.",
                              encoding="utf-8")

            record = build_report_record(report, "after-market", snapshots_dir=snaps)
            self.assertEqual(record["id"], "2026-11-18-after-market")  # New York date
            self.assertEqual(record["stocks"][0]["symbol"], "NVDA")
            self.assertTrue(record["text"].startswith("📊 Executive Summary"))

            data = tmp / "data"
            save_record(record, data)
            save_record(dict(record, text="updated"), data)  # same id: replaced, not duplicated
            save_record(dict(record, id="2026-11-19-after-market", date="2026-11-19"), data)
            index = json.loads((data / "reports" / "index.json").read_text(encoding="utf-8"))["reports"]
            self.assertEqual([e["id"] for e in index], ["2026-11-19-after-market", "2026-11-18-after-market"])
            stored = json.loads((data / "reports" / "2026-11-18-after-market.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["text"], "updated")


class BuildSiteTests(unittest.TestCase):
    def test_build_from_snapshot_with_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            snap = tmp / "snap.json"
            snap.write_text(json.dumps({
                "news": [news("NVDA", "Nvidia beats estimates and raises guidance", 10, image="https://cdn.example.com/n.jpg"),
                         news("NVDA", "Nvidia beats estimates, raises guidance", 11)],
                "market_news": [{"headline": "Fed holds rates", "source": "CNBC", "summary": "", "url": "https://c/1",
                                 "image": "", "timestamp": 12}],
                "stocks": {"NVDA": {"name": "NVIDIA", "price": 190.5, "change_percent": 3.2, "pe_ratio": 45.2}},
            }), encoding="utf-8")
            data = tmp / "data"
            save_record({"id": "2026-11-18-after-market", "date": "2026-11-18", "session": "after-market",
                         "stocks": [], "text": "x"}, data)

            out = tmp / "site"
            self.assertEqual(build_site(["--out", str(out), "--snapshot", str(snap), "--data-dir", str(data)]), 0)
            payload = json.loads((out / "news.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["total_groups"], 2)
            nvda = next(g for g in payload["groups"] if g["symbols"] == ["NVDA"])
            self.assertEqual(nvda["size"], 2)
            self.assertEqual(nvda["image"], "https://cdn.example.com/n.jpg")
            self.assertEqual(payload["stocks"], [{"name": "NVIDIA", "price": 190.5, "change_percent": 3.2,
                                                  "pe_ratio": 45.2, "symbol": "NVDA"}])
            self.assertEqual(payload["earnings"], [])
            self.assertTrue((out / "index.html").exists())
            self.assertTrue((out / "reports" / "index.json").exists())


if __name__ == "__main__":
    unittest.main()
