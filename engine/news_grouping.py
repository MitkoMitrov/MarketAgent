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
    text = _APOSTROPHE_RE.sub("'", text)
    text = _SPACED_DASH_RE.sub(" – ", text)
    text = text.replace("�", " ").replace("\xa0", " ")
    return _SPACES_RE.sub(" ", text).strip()


def normalize(text: str) -> str:
    """Lowercase, drop punctuation, collapse whitespace."""
    text = clean_text(text).lower().replace("'", "")
    return _SPACES_RE.sub(" ", _NON_ALNUM_RE.sub(" ", text)).strip()


def _ratio(a: str, b: str, threshold: float) -> float:
    """SequenceMatcher ratio, short-circuiting with its cheap upper bounds."""
    if not a or not b:
        return 0.0
    sm = SequenceMatcher(None, a, b, autojunk=False)
    if sm.real_quick_ratio() < threshold or sm.quick_ratio() < threshold:
        return 0.0
    return sm.ratio()


def text_similarity(a: str, b: str, threshold: float = 0.0) -> float:
    """Similarity in [0, 1] of two texts (order-sensitive and word-order-insensitive).

    Results below `threshold` may be reported as 0.0 (fast path)."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    sa, sb = " ".join(sorted(na.split())), " ".join(sorted(nb.split()))
    return max(_ratio(na, nb, threshold), _ratio(sa, sb, threshold))


class _Article:
    """Pre-normalized article used during comparison."""
    __slots__ = ("item", "head", "head_sorted", "head_numbers", "summ", "summ_sorted")

    def __init__(self, item: dict):
        self.item = item
        self.head = normalize(item.get("headline", ""))
        self.head_sorted = " ".join(sorted(self.head.split()))
        self.head_numbers = frozenset(_NUMBER_RE.findall(clean_text(item.get("headline", ""))))
        summ = normalize(item.get("summary", ""))
        self.summ = summ if len(summ) >= _MIN_SUMMARY_LEN else ""
        self.summ_sorted = " ".join(sorted(self.summ.split())) if self.summ else ""

    def _head_sim(self, other: "_Article", threshold: float) -> float:
        if not (self.head and other.head):
            return 0.0
        return max(_ratio(self.head, other.head, threshold),
                   _ratio(self.head_sorted, other.head_sorted, threshold))

    def similar_to(self, other: "_Article", threshold: float) -> bool:
        # Template headlines ("A $2.4 Billion Fund Dumps These 3 Stocks" vs "A $7.2 Billion ...")
        # are textually ~90% alike but are different stories: numbers carry the facts.
        if self.head_numbers and other.head_numbers and self.head_numbers != other.head_numbers:
            return False
        if self._head_sim(other, threshold) >= threshold:
            return True
        # Summaries alone are not enough: some publishers reuse one boilerplate
        # summary (e.g. a fund's investor letter) for articles about different stocks.
        if self.summ and other.summ and (
            _ratio(self.summ, other.summ, threshold) >= threshold
            or _ratio(self.summ_sorted, other.summ_sorted, threshold) >= threshold
        ):
            return self._head_sim(other, _SUMMARY_MATCH_MIN_HEADLINE) >= _SUMMARY_MATCH_MIN_HEADLINE
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
        {"primary": item, "similar": [items newest first], "size": int,
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
