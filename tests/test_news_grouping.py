"""Tests for engine.news_grouping. Run: python -m unittest tests.test_news_grouping"""
import unittest

from engine.news_grouping import clean_text, group_news, rank_top, text_similarity


def item(headline, source="Yahoo", ts=1000, url=None, symbol=None, summary="", category=None):
    d = {"headline": headline, "source": source, "timestamp": ts, "summary": summary,
         "url": url or f"https://example.com/{abs(hash(headline))}"}
    if symbol:
        d["symbol"] = symbol
    if category:
        d["category"] = category
    return d


LETTER = ("Orbis Investment Management released its Q4 2025 investor letter for the International Equity Fund. "
          "The Strategy reported a positive year in 2025. A copy of the letter can be downloaded here.")


class CleanTextTests(unittest.TestCase):
    def test_repairs_replacement_characters(self):
        self.assertEqual(clean_text("Buy Microsoft�s stock while it�s down"),
                         "Buy Microsoft's stock while it's down")
        self.assertEqual(clean_text("students � not players"), "students – not players")
        self.assertEqual(clean_text("�Bearish engulfing� patterns"), "Bearish engulfing patterns")


class SimilarityTests(unittest.TestCase):
    def test_identical_ignoring_case_and_punctuation(self):
        self.assertEqual(text_similarity("Tesla Stock Jumps!", "tesla stock jumps"), 1.0)

    def test_small_edit_is_above_90(self):
        self.assertGreaterEqual(text_similarity(
            "Musk expects Europe, China to approve Tesla's FSD system next month",
            "Davos-Musk expects Europe, China to approve Tesla's FSD system next month"), 0.9)

    def test_reordered_words_are_similar(self):
        self.assertGreaterEqual(text_similarity(
            "Nvidia shares fall after earnings beat",
            "After earnings beat, Nvidia shares fall"), 0.9)

    def test_different_stories_are_not_similar(self):
        self.assertLess(text_similarity("AMD stock falls on MI450-series delay rumors",
                                        "Why Advanced Micro Devices Stock Just Dropped"), 0.9)


class GroupingTests(unittest.TestCase):
    def test_same_url_under_two_tickers_is_one_item_with_both_symbols(self):
        groups = group_news([
            item("SpaceX-xAI merger analysis", url="https://x/1", symbol="TSLA"),
            item("SpaceX-xAI merger analysis", url="https://x/1", symbol="GOOG"),
        ])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["size"], 1)
        self.assertEqual(groups[0]["symbols"], ["GOOG", "TSLA"])

    def test_near_duplicates_grouped_and_newest_with_summary_is_primary(self):
        groups = group_news([
            item("Musk expects Europe, China to approve Tesla's FSD system next month", ts=100, symbol="TSLA"),
            item("Davos-Musk expects Europe, China to approve Tesla's FSD system next month", ts=200,
                 source="Reuters", symbol="TSLA", summary="Elon Musk said on Thursday ..."),
            item("Musk expects Europe and China to approve Tesla's FSD system next month", ts=300, symbol="TSLA"),
            item("Gold prices slump", ts=50, category="market"),
        ])
        self.assertEqual(len(groups), 2)
        big = max(groups, key=lambda g: g["size"])
        self.assertEqual(big["size"], 3)
        self.assertEqual(big["primary"]["source"], "Reuters")
        self.assertEqual([s["timestamp"] for s in big["similar"]], [300, 100])

    def test_boilerplate_summary_alone_does_not_group(self):
        groups = group_news([
            item("Genmab (GMAB)'s Future Potential Underappreciated by Market", summary=LETTER),
            item("ICON PLC (ICLR) Trades Below Normal Earnings Despite Strong Fundamentals", summary=LETTER),
        ])
        self.assertEqual(len(groups), 2)

    def test_identical_summary_with_related_headlines_groups(self):
        summary = ("The stock market tested key levels to end the week while gold and silver dived in a "
                   "risk-off shift. Google, AMD, Amazon and Palantir headline another big earnings week.")
        groups = group_news([
            item("Dow Jones Futures: Market Tests Key Levels In Risk-Off Shift; Google, AMD On Tap", summary=summary),
            item("Dow Jones Futures: Risk-Off Shift For Stock Market? Google, AMD On Tap", summary=summary),
        ])
        self.assertEqual(len(groups), 1)

    def test_template_headlines_with_different_numbers_stay_separate(self):
        groups = group_news([
            item("A $2.4 Billion Fund Dumps These 3 Stocks"),
            item("A $7.2 Billion Fund Dumps These 3 Stocks"),
            item("An $11 Billion Fund Dumps These 2 Stocks"),
        ])
        self.assertEqual(len(groups), 3)

    def test_grouping_is_transitive(self):
        groups = group_news([
            item("Fed holds rates steady as inflation cools in December"),
            item("Fed holds rates steady as inflation cools in Dec."),
            item("Fed holds rates steady, inflation cools in Dec."),
        ])
        self.assertEqual(len(groups), 1)

    def test_rank_top_prefers_bigger_groups(self):
        groups = group_news([
            item("Lonely fresh story", ts=999),
            item("Big story about chips export rules", ts=10),
            item("Big story about chip export rules", ts=11),
        ])
        self.assertEqual(rank_top(groups)[0]["size"], 2)
        self.assertEqual(groups[0]["primary"]["headline"], "Lonely fresh story")  # default order: newest

    def test_empty_input(self):
        self.assertEqual(group_news([]), [])


if __name__ == "__main__":
    unittest.main()
