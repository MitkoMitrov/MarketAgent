"""
Build the static news site for GitHub Pages.

Fetches company + market news, quotes, key metrics and upcoming earnings from Finnhub
(no OpenAI calls), groups duplicate news, and writes <out>/news.json next to a copy of
web/ (index.html etc.). With --data-dir (a checkout of the `data` branch) the stored AI
reports are copied to <out>/reports/.

Usage (from project root):
    python -m engine.build_news_site --out site
    python -m engine.build_news_site --out site --snapshot data/snapshots/<file>.json   # offline preview
    python -m engine.build_news_site --out site --data-dir data-store                    # include AI reports
"""
import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from engine.finnhub_client import SYMBOLS
from engine.market_data import fetch_stocks
from engine.news_fetcher import fetch_company_news, fetch_market_news
from engine.news_grouping import DEFAULT_THRESHOLD, group_news
from engine.thumbnails import enrich_group_images

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PROJECT_ROOT / "web"

WINDOW_HOURS = 24
THUMB_CACHE = PROJECT_ROOT / ".cache" / "thumbnails.json"
META_CACHE = PROJECT_ROOT / ".cache" / "market_meta.json"


def collect_live_news() -> list:
    items = []
    for symbol in SYMBOLS:
        print(f"  → {symbol} company news...")
        items += fetch_company_news(symbol, hours=WINDOW_HOURS)
    print("  → market news...")
    items += fetch_market_news(hours=WINDOW_HOURS)
    return items


def collect_snapshot_news(path: Path) -> list:
    snap = json.loads(path.read_text(encoding="utf-8"))
    items = [dict(n, symbols=[n["symbol"]], category="company") for n in snap.get("news", [])]
    items += [dict(n, symbols=[], category="market") for n in snap.get("market_news", [])]
    return items


def collect_snapshot_stocks(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")).get("stocks", {})


def build_payload(items: list, threshold: float = DEFAULT_THRESHOLD, stocks: dict = None, earnings: list = None) -> dict:
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
        # Same figures as the Telegram "Company Info" and earnings messages.
        "stocks": [dict(info, symbol=sym) for sym, info in (stocks or {}).items()],
        "earnings": earnings or [],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="site", help="output directory (default: site)")
    parser.add_argument("--snapshot", type=Path, help="build from a saved snapshot instead of calling Finnhub")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--data-dir", type=Path, help="checkout of the data branch (AI reports)")
    parser.add_argument("--thumbnails", action=argparse.BooleanOptionalAction, default=None,
                        help="look up missing thumbnails on article pages (default: on for live builds)")
    args = parser.parse_args(argv)

    print("📥 Collecting news...")
    items = collect_snapshot_news(args.snapshot) if args.snapshot else collect_live_news()
    if not items:
        # Fail so the workflow keeps the last good deployment instead of publishing an empty page.
        print("❌ No news items collected; not building the site.")
        return 1

    if args.snapshot:
        stocks, earnings = collect_snapshot_stocks(args.snapshot), []
    else:
        print("📈 Collecting stock data...")
        stocks, earnings = fetch_stocks(SYMBOLS, cache_path=META_CACHE, with_earnings=True)

    payload = build_payload(items, threshold=args.threshold, stocks=stocks, earnings=earnings)

    use_thumbs = args.thumbnails if args.thumbnails is not None else not args.snapshot
    if use_thumbs:
        stats = enrich_group_images(payload["groups"], THUMB_CACHE)
        print(f"🖼️  Thumbnails: {stats['missing']} stories without image, "
              f"{stats['fetched']} pages checked, {stats['filled']} filled")
        for outcome, n in stats["outcomes"]:
            print(f"     {n:4d} × {outcome}")

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(WEB_DIR, out)
    (out / "news.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    reports_src = args.data_dir / "reports" if args.data_dir else None
    if reports_src and (reports_src / "index.json").exists():
        shutil.copytree(reports_src, out / "reports")
        print(f"📄 Copied {len(list(reports_src.glob('*.json'))) - 1} AI report(s) to {out}/reports/")

    print(f"✅ {payload['total_articles']} articles → {payload['total_groups']} stories, written to {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
