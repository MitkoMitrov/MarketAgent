"""
Build the static news site for GitHub Pages.

Fetches company + market news from Finnhub (no OpenAI calls), groups duplicates,
and writes <out>/news.json next to a copy of web/ (index.html etc.).

Usage (from project root):
    python -m engine.build_news_site --out site
    python -m engine.build_news_site --out site --snapshot data/snapshots/<file>.json   # offline preview
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from engine.finnhub_client import SYMBOLS
from engine.news_fetcher import fetch_company_news, fetch_market_news
from engine.news_grouping import DEFAULT_THRESHOLD, group_news

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"

WINDOW_HOURS = 24
COMPANY_NEWS_PER_SYMBOL = 20


def collect_live_news() -> list:
    items = []
    for symbol in SYMBOLS:
        print(f"  → {symbol} company news...")
        items += fetch_company_news(symbol, days=1, limit=COMPANY_NEWS_PER_SYMBOL)
    print("  → market news...")
    items += fetch_market_news(hours=WINDOW_HOURS)
    return items


def collect_snapshot_news(path: Path) -> list:
    snap = json.loads(path.read_text(encoding="utf-8"))
    items = [dict(n, symbols=[n["symbol"]], category="company") for n in snap.get("news", [])]
    items += [dict(n, symbols=[], category="market") for n in snap.get("market_news", [])]
    return items


def build_payload(items: list, threshold: float = DEFAULT_THRESHOLD) -> dict:
    groups = group_news(items, threshold=threshold)
    for i, g in enumerate(groups):
        g["id"] = f"g{i}"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_hours": WINDOW_HOURS,
        "threshold": threshold,
        "symbols": SYMBOLS,
        "total_articles": len(items),
        "total_groups": len(groups),
        "groups": groups,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="site", help="output directory (default: site)")
    parser.add_argument("--snapshot", type=Path, help="build from a saved snapshot instead of calling Finnhub")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    args = parser.parse_args(argv)

    print("📥 Collecting news...")
    items = collect_snapshot_news(args.snapshot) if args.snapshot else collect_live_news()
    if not items:
        # Fail so the workflow keeps the last good deployment instead of publishing an empty page.
        print("❌ No news items collected; not building the site.")
        return 1

    payload = build_payload(items, threshold=args.threshold)

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(WEB_DIR, out)
    (out / "news.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    print(f"✅ {payload['total_articles']} articles → {payload['total_groups']} stories, written to {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
