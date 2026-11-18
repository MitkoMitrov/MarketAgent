"""
Group duplicate / near-duplicate news items (text similarity only, no API calls).

Algorithm
---------
1. Clean text (Finnhub sometimes ships U+FFFD in place of apostrophes/quotes).
2. Merge exact duplicates: same URL, or identical normalized headline. Their
   symbols are unioned (the same Yahoo article is often listed under TSLA *and* GOOG).
3. Compare every remaining pair of articles. Two articles are "similar" when
   their headlines are >= `threshold` similar, or their summaries are >= `threshold`
   similar AND their headlines are at least 60% similar. Headlines that both contain
   numbers must contain the same numbers. Similarity is the higher of:
     - character similarity of the normalized text  (catches small edits)
     - character similarity of the word-sorted text (catches reordered words)
   Cheap upper-bound checks skip most pairs before the expensive comparison.
4. Union-find joins similar pairs into groups (so A~B and B~C ends up as one group).
5. In each group the primary item is the newest article that has a summary; the
   rest are listed as "similar".
"""
import re
from collections import Counter
from difflib import SequenceMatcher

DEFAULT_THRESHOLD = 0.90
_MIN_SUMMARY_LEN = 80  # shorter summaries are too generic to compare
_SUMMARY_MATCH_MIN_HEADLINE = 0.60  # headline similarity required when matching on summary

_APOSTROPHE_RE = re.compile(r"(?<=\w)�(?=(?:s|t|re|ve|ll|d|m)\b)", re.IGNORECASE)
_SPACED_DASH_RE = re.compile(r"\s�\s")
_NON_ALNUM_RE = re.compile(r"[^a-z0-9$%]+")
_SPACES_RE = re.compile(r"\s+")
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)*")


def clean_text(text: str) -> str:
    """Repair common mojibake (U+FFFD) and collapse whitespace."""
    if not text:
        return ""
    if "â\u0080" in text or "Ã" in text:
        # UTF-8 bytes that were decoded as Latin-1 upstream ("didnâ\x80\x99t" -> "didn’t").
        try:
            text = text.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    text = _APOSTROPHE_RE.sub("'", text)
    text = _SPACED_DASH_RE.sub(" – ", text)
    text = text.replace("�", " ").replace("\xa0", " ")
    return _SPACES_RE.sub(" ", text).strip()


def normalize(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace."""
    text = clean_text(text).lower().replace("'", "")
    return _SPACES_RE.sub(" ", _NON_ALNUM_RE.sub(" ", text)).strip()


def text_similarity(a: str, b: str, threshold: float = 0.0) -> float:
    """Similarity in [0, 1] of two texts (order-sensitive and word-order-insensitive).

    Results below `threshold` may be reported as 0.0 (fast path)."""
    return _Text(normalize(a)).similarity(_Text(normalize(b)), threshold)


class _Text:
    """A normalized text prepared for fast repeated comparisons."""
    __slots__ = ("plain", "sorted", "length", "chars")

    def __init__(self, text: str):
        self.plain = text
        self.sorted = " ".join(sorted(text.split()))
        self.length = len(text)
        self.chars = Counter(text)  # same multiset for plain and word-sorted text

    def __bool__(self):
        return self.length > 0

    def similarity(self, other: "_Text", threshold: float) -> float:
        """max(plain ratio, word-sorted ratio); 0.0 when cheap bounds rule out `threshold`."""
        if not self.length or not other.length:
            return 0.0
        total = self.length + other.length
        # Upper bound 1: length difference.
        if 2.0 * min(self.length, other.length) / total < threshold:
            return 0.0
        # Upper bound 2: shared characters (independent of order).
        small, big = (self.chars, other.chars) if len(self.chars) <= len(other.chars) else (other.chars, self.chars)
        shared = sum(min(n, big.get(ch, 0)) for ch, n in small.items())
        if 2.0 * shared / total < threshold:
            return 0.0
        if self.plain == other.plain:
            return 1.0
        best = SequenceMatcher(None, self.plain, other.plain, autojunk=False).ratio()
        if threshold <= 0 or best < threshold:  # no threshold: always report the true maximum
            best = max(best, SequenceMatcher(None, self.sorted, other.sorted, autojunk=False).ratio())
        return best


class _Article:
    """Pre-normalized article used during comparison."""
    __slots__ = ("item", "head", "head_numbers", "summ")

    def __init__(self, item: dict):
        self.item = item
        self.head = _Text(normalize(item.get("headline", "")))
        self.head_numbers = frozenset(_NUMBER_RE.findall(clean_text(item.get("headline", ""))))
        summ = normalize(item.get("summary", ""))
        self.summ = _Text(summ if len(summ) >= _MIN_SUMMARY_LEN else "")

    def similar_to(self, other: "_Article", threshold: float) -> bool:
        # Template headlines ("A $2.4 Billion Fund Dumps These 3 Stocks" vs "A $7.2 Billion ...")
        # are textually ~90% alike but are different stories: numbers carry the facts.
        if self.head_numbers and other.head_numbers and self.head_numbers != other.head_numbers:
            return False
        if self.head.similarity(other.head, threshold) >= threshold:
            return True
        # Summaries alone are not enough: some publishers reuse one boilerplate
        # summary (e.g. a fund's investor letter) for articles about different stocks.
        if self.summ.similarity(other.summ, threshold) >= threshold:
            return self.head.similarity(other.head, _SUMMARY_MATCH_MIN_HEADLINE) >= _SUMMARY_MATCH_MIN_HEADLINE
        return False


def _clean_item(item: dict) -> dict:
    out = dict(item)
    out["headline"] = clean_text(item.get("headline", ""))
    out["summary"] = clean_text(item.get("summary", ""))
    syms = item.get("symbols")
    if syms is None:
        syms = [item["symbol"]] if item.get("symbol") else []
    out["symbols"] = sorted(set(syms))
    out.setdefault("category", "company" if out["symbols"] else "market")
    out["timestamp"] = int(item.get("timestamp") or 0)
    return out


def merge_exact_duplicates(items: list) -> list:
    """Collapse items with the same URL or the same normalized headline into one."""
    merged, by_key = [], {}
    for raw in items:
        item = _clean_item(raw)
        keys = [k for k in (item.get("url"), "h:" + normalize(item["headline"])) if k and k != "h:"]
        existing = next((by_key[k] for k in keys if k in by_key), None)
        if existing is None:
            item["categories"] = [item["category"]]
            merged.append(item)
            existing = item
        else:
            existing["symbols"] = sorted(set(existing["symbols"]) | set(item["symbols"]))
            if item["category"] not in existing["categories"]:
                existing["categories"].append(item["category"])
            if len(item["summary"]) > len(existing["summary"]):
                existing["summary"] = item["summary"]
            if not existing.get("image") and item.get("image"):
                existing["image"] = item["image"]
            existing["timestamp"] = max(existing["timestamp"], item["timestamp"])
        for k in keys:
            by_key.setdefault(k, existing)
    return merged


def _pick_primary(members: list) -> dict:
    return max(members, key=lambda m: (bool(m["summary"]), m["timestamp"]))


def group_news(items: list, threshold: float = DEFAULT_THRESHOLD) -> list:
    """Group duplicate/similar news.

    Args:
        items: dicts with headline, source, summary, url, timestamp and either
               `symbols` (list) or `symbol` (str), optionally `category`.
        threshold: similarity in [0, 1] at or above which two items are grouped.

    Returns:
        List of groups, newest first:
        {"primary": item, "similar": [items newest first], "size": int, "image": str,
         "symbols": [...], "sources": [...], "categories": [...],
         "latest_ts": int, "first_ts": int}
    """
    articles = [_Article(it) for it in merge_exact_duplicates(items)]
    n = len(articles)
    parent = list(range(n))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(n):
        for j in range(i + 1, n):
            ri, rj = find(i), find(j)
            if ri != rj and articles[i].similar_to(articles[j], threshold):
                parent[rj] = ri

    clusters = {}
    for i, art in enumerate(articles):
        clusters.setdefault(find(i), []).append(art.item)

    groups = []
    for members in clusters.values():
        primary = _pick_primary(members)
        similar = sorted((m for m in members if m is not primary), key=lambda m: m["timestamp"], reverse=True)
        timestamps = [m["timestamp"] for m in members]
        groups.append({
            "primary": primary,
            "image": next((m["image"] for m in [primary, *similar] if m.get("image")), ""),
            "similar": similar,
            "size": len(members),
            "symbols": sorted({s for m in members for s in m["symbols"]}),
            "sources": sorted({m["source"] for m in members if m["source"]}),
            "categories": sorted({c for m in members for c in m["categories"]}),
            "latest_ts": max(timestamps),
            "first_ts": min(timestamps),
        })

    groups.sort(key=lambda g: g["latest_ts"], reverse=True)
    return groups


def rank_top(groups: list) -> list:
    """Order groups by coverage: most articles, then most tickers, then newest."""
    return sorted(groups, key=lambda g: (g["size"], len(g["symbols"]), g["latest_ts"]), reverse=True)
