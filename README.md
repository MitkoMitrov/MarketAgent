# MarketAgent data branch

Generated data only, no code. Written by GitHub Actions; do not edit by hand.

- `reports/index.json`: list of stored AI reports, newest first
- `reports/<date>-<session>.json`: one AI market report (text + that day's stock moves)

Written by `engine/report_store.py` in the daily workflow (`marketagent-cron.yml`) and
read by the news site build (`news-pages.yml`). Code lives on `main`.
