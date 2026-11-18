"""
Shared Finnhub configuration: watchlist symbols and a lazily created API client.

Importing this module has no side effects; the client is only built (and the
API key only required) the first time `get_client()` is called.
"""
import os
from functools import lru_cache

import finnhub
from dotenv import load_dotenv

load_dotenv()

# Single source of truth for the watchlist (used by snapshots, earnings, news site).
SYMBOLS = ["QQQ", "TSLA", "AMD", "GOOG", "NVDA", "MSTR", "SMCI"]


@lru_cache(maxsize=1)
def get_client() -> finnhub.Client:
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        raise ValueError("FINNHUB_API_KEY not found in environment variables")
    return finnhub.Client(api_key=api_key)
