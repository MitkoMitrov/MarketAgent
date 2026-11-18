"""
Fill in missing thumbnails for news groups from the article's preview image (og:image).

Finnhub often returns only a publisher logo (most Yahoo items), so for groups without an
image we open the article page once, read its <meta property="og:image">, and remember the
answer in a small JSON cache. The cache is persisted between GitHub Actions runs with
actions/cache, so each run only fetches articles it has not seen before.
"""
import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from html import unescape
from pathlib import Path
from urllib.parse import urlparse

import requests

from engine.news_fetcher import clean_image_url

USER_AGENT = "Mozilla/5.0 (compatible; NewsPreviewBot/1.0)"
MAX_HTML_BYTES = 300_000      # og:image lives in <head>; don't download whole pages
# Most links go through Finnhub's redirect (finnhub.io/api/news?id=...), which answers 429
# when hit with many parallel requests; keep concurrency low (~4).
TIMEOUT_S = 8
CACHE_TTL_S = 3 * 24 * 3600   # news window is 24h; keep entries a bit longer
GENERIC_IMAGE_MIN_USES = 3    # same image on 3+ different stories = publisher default picture

_META_RE = re.compile(r"<meta\b[^>]*>", re.I)
_PROP_RE = re.compile(r"""(?:property|name)\s*=\s*["'](og:image(?::secure_url)?|twitter:image(?::src)?)["']""", re.I)
_CONTENT_RE = re.compile(r"""content\s*=\s*["']([^"']+)["']""", re.I)


def extract_preview_image(html: str) -> str:
    """Return the first og:image / twitter:image URL in the HTML, or ""."""
    for tag in _META_RE.findall(html):
        if _PROP_RE.search(tag):
            m = _CONTENT_RE.search(tag)
            if m:
                return unescape(m.group(1).strip())
    return ""


# Answers worth remembering. Anything else (429 rate limit, 5xx, timeouts) is retried next run.
_DEFINITIVE_STATUSES = {200, 401, 403, 404, 410, 451}


def fetch_preview_image(url: str, session: requests.Session) -> tuple:
    """Return (image_url_or_empty, cacheable, outcome) where outcome is "<host> <status>"."""
    try:
        with session.get(url, timeout=TIMEOUT_S, stream=True, allow_redirects=True) as resp:
            outcome = f"{urlparse(resp.url).hostname} {resp.status_code}"
            if resp.status_code != 200 or "html" not in resp.headers.get("content-type", "html"):
                return "", resp.status_code in _DEFINITIVE_STATUSES, outcome
            raw = resp.raw.read(MAX_HTML_BYTES, decode_content=True)
        return clean_image_url(extract_preview_image(raw.decode("utf-8", "ignore"))), True, outcome
    except Exception as e:
        return "", False, f"{urlparse(url).hostname} {type(e).__name__}"


def _load_cache(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cutoff = time.time() - CACHE_TTL_S
        return {u: v for u, v in data.items() if v.get("t", 0) >= cutoff}
    except Exception:
        return {}


def _save_cache(path: Path, cache: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, separators=(",", ":")), encoding="utf-8")


def enrich_group_images(groups: list, cache_path: Path, max_fetch: int = 150, workers: int = 4) -> dict:
    """Set group["image"] for groups that have none. Returns stats for logging."""
    cache = _load_cache(cache_path)
    missing = [g for g in groups if not g.get("image")]

    # Candidate articles per group: primary first, then the similar ones.
    candidates = {id(g): [m["url"] for m in [g["primary"], *g["similar"]] if m.get("url")] for g in missing}
    to_fetch, seen = [], set()
    for urls in candidates.values():
        for url in urls[:2]:  # at most 2 tries per story
            if url not in cache and url not in seen:
                seen.add(url)
                to_fetch.append(url)
    to_fetch = to_fetch[:max_fetch]

    outcomes = Counter()
    if to_fetch:
        with requests.Session() as session:
            session.headers["User-Agent"] = USER_AGENT
            with ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(lambda u: fetch_preview_image(u, session), to_fetch))
        now = int(time.time())
        for url, (image, cacheable, outcome) in zip(to_fetch, results):
            outcomes[outcome + (" img" if image else "")] += 1
            if cacheable:  # "" is cached too, so pages without an image aren't refetched every run
                cache[url] = {"i": image, "t": now}
        _save_cache(cache_path, cache)

    found = {}
    for g in missing:
        found[id(g)] = next((cache[u]["i"] for u in candidates[id(g)] if cache.get(u, {}).get("i")), "")

    # A publisher's default picture shows up on many unrelated stories; treat it as "no image".
    uses = Counter(img for img in found.values() if img)
    filled = 0
    for g in missing:
        img = found[id(g)]
        if img and uses[img] < GENERIC_IMAGE_MIN_USES:
            g["image"] = img
            filled += 1

    return {"missing": len(missing), "fetched": len(to_fetch), "filled": filled,
            "outcomes": outcomes.most_common(8)}
