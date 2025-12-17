from dataclasses import dataclass
from typing import List


@dataclass
class StockInsight:
    symbol: str
    move_summary: str
    confidence: float
    tags: List[str]


@dataclass
class MarketReport:
    session: str
    headline: str
    summary: str
    key_insights: List[StockInsight]
    risks_to_watch: List[str]
    opportunities: List[str]
    tone: str
