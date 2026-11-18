"""
Save the latest AI report as JSON into a checkout of the `data` branch.

Layout written under --data-dir:
    reports/index.json             {"reports": [{"id", "date", "session", "file"}, ...]}  newest first
    reports/<date>-<session>.json  {"id", "date", "session", "generated_at", "snapshot_time", "stocks", "text"}

The news site (engine.build_news_site --data-dir ...) copies this folder into the page.

Usage (from project root, after run_ai_report):
    python -m engine.report_store --data-dir data-store
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SNAPSHOTS_DIR = PROJECT_ROOT / "data" / "snapshots"
SEPARATOR = "=" * 10


def parse_report_file(path: Path) -> dict:
    """Split an ai_report-*.txt file into its header fields and body text."""
    lines = path.read_text(encoding="utf-8").splitlines()
    header, body_start = {}, 0
    for i, line in enumerate(lines):
        if SEPARATOR in line:
            body_start = i + 1
            break
        if ":" in line:
            key, _, value = line.partition(":")
            header[key.strip().lower()] = value.strip()
    return {"header": header, "text": "\n".join(lines[body_start:]).strip()}


def _stocks_from_snapshot(snapshot: dict) -> list:
    return [
        {
            "symbol": sym,
            "name": info.get("name", sym),
            "price": info.get("price", 0),
            "change": info.get("change", 0),
            "change_percent": info.get("change_percent", 0),
        }
        for sym, info in snapshot.get("stocks", {}).items()
    ]


def build_report_record(report_path: Path, session: str, snapshots_dir: Path = SNAPSHOTS_DIR) -> dict:
    parsed = parse_report_file(report_path)
    snapshot = {}
    source = parsed["header"].get("source")
    if source and (snapshots_dir / source).exists():
        snapshot = json.loads((snapshots_dir / source).read_text(encoding="utf-8"))

    snap_time = snapshot.get("snapshot_time")
    when = datetime.fromisoformat(snap_time) if snap_time else datetime.now(timezone.utc)
    date = when.astimezone(ZoneInfo("America/New_York")).date().isoformat()

    return {
        "id": f"{date}-{session}",
        "date": date,
        "session": session,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "snapshot_time": snap_time,
        "stocks": _stocks_from_snapshot(snapshot),
        "text": parsed["text"],
    }


def save_record(record: dict, data_dir: Path) -> Path:
    """Write the report JSON and upsert it into reports/index.json (newest first)."""
    out_dir = data_dir / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{record['id']}.json"
    (out_dir / file_name).write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")

    index_path = out_dir / "index.json"
    index = {"reports": []}
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    entries = [e for e in index.get("reports", []) if e.get("id") != record["id"]]
    entries.append({"id": record["id"], "date": record["date"], "session": record["session"], "file": f"reports/{file_name}"})
    entries.sort(key=lambda e: (e["date"], e["session"]), reverse=True)
    index_path.write_text(json.dumps({"reports": entries}, ensure_ascii=False, indent=1), encoding="utf-8")
    return out_dir / file_name


def latest_report_file(reports_dir: Path = REPORTS_DIR):
    files = sorted(reports_dir.glob("ai_report-*.txt"), reverse=True)
    return files[0] if files else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data-dir", type=Path, required=True, help="checkout of the data branch")
    parser.add_argument("--session", default=os.getenv("MARKET_SESSION", "after-market"))
    args = parser.parse_args(argv)

    report = latest_report_file()
    if report is None:
        # Non-working day or the AI step failed: nothing to store, not an error.
        print("ℹ️ No AI report produced in this run; nothing to save.")
        return 0

    record = build_report_record(report, args.session)
    path = save_record(record, args.data_dir)
    print(f"✅ Saved {report.name} → {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
