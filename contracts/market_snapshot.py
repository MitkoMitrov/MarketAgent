from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class StockMove:
    symbol: str
    price: float
    change_percent: float
    volume: Optional[int]
    market_cap: Optional[float]
    reason_hint: Optional[str]


@dataclass
class MacroEvent:
    title: str
    source: str
    timestamp: datetime
    affected_sectors: List[str]
    factual_summary: str


@dataclass
class NewsItem:
    headline: str
    source: str
    timestamp: datetime
    symbols: List[str]
    summary: str


@dataclass
class MarketSnapshot:
    snapshot_time: datetime
    market_session: str
    major_index_moves: Dict[str, float]
    top_movers: List[StockMove]
    macro_events: List[MacroEvent]
    news: List[NewsItem]
