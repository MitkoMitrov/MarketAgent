"""
Shared Finnhub configuration: watchlist symbols, a lazily created API client, a raw
GET helper for endpoints the Python client doesn't cover, and a rate limiter.

Importing this module has no side effects; the client is only built (and the
API key only required) the first time it is used.
"""
import os
import threading
import time
from collections import deque
from functools import lru_cache

import finnhub
import requests
from dotenv import load_dotenv

load_dotenv()

# Single source of truth for the watchlist (used by snapshots, earnings, news site).
SYMBOLS = ["QQQ", "TSLA", "AMD", "GOOG", "NVDA", "MSTR", "SMCI", "ANT"]

API_BASE = "https://finnhub.io/api/v1"
MAX_CALLS_PER_MIN = 50  # free tier allows 60/min; keep a margin

_calls = deque()
_lock = threading.Lock()


def _api_key() -> str:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("FINNHUB_API_KEY not found in environment variables")
    return api_key


@lru_cache(maxsize=1)
def get_client() -> finnhub.Client:
    return finnhub.Client(api_key=_api_key())


def throttle() -> None:
    """Block until another API call fits in the per-minute budget. Call before each request."""
    with _lock:
        while True:
            now = time.monotonic()
            while _calls and now - _calls[0] >= 60:
                _calls.popleft()
            if len(_calls) < MAX_CALLS_PER_MIN:
                _calls.append(now)
                return
            time.sleep(60 - (now - _calls[0]) + 0.05)


def api_get(path: str, **params):
    """GET {API_BASE}{path}; returns parsed JSON or raises (so failures are never cached)."""
    throttle()
    resp = requests.get(API_BASE + path, params=params, headers={"X-Finnhub-Token": _api_key()}, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {path}: {resp.text[:120]}")
    return resp.json()
